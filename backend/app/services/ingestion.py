"""Normalised ingestion pipeline shared by manual submissions and source connectors."""
from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailure
from app.models import Brand, CollectionRecord, DataSource, DigitalEntity, User
from app.models.enums import EntityType, Provenance, SourceKind
from app.repositories.access import get_brand_for_user
from app.schemas.entity import ATTR_MODELS, EntitySubmit
from app.services import audit
from app.services.official import is_official_asset
from app.utils.urls import parse_url

_RANK = {Provenance.SYNTHETIC: 1, Provenance.MANUAL: 2, Provenance.COLLECTED: 3}
_LIST_CAPS = {"post_timestamps": 1000, "image_phashes": 50, "links": 50, "linked_websites": 20}


@dataclass
class NormalizedEntity:
    entity_type: EntityType
    canonical_id: str
    display_name: str
    attributes: dict[str, Any]
    platform: str | None = None
    source_url: str | None = None


def _check_urls(label: str, values: list[str]) -> list[dict]:
    return [{"field": label, "message": f"'{v}' is not a valid http(s) URL"} for v in values if parse_url(v) is None]


def normalize_submission(entity_type: EntityType, display_name: str | None, platform: str | None, source_url: str | None, attributes: dict[str, Any]) -> NormalizedEntity:
    model = ATTR_MODELS[entity_type]
    try:
        attrs = model.model_validate(attributes)
    except ValidationError as exc:
        raise ValidationFailure(
            f"Invalid attributes for {entity_type.value}",
            details=[{"field": "attributes." + ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()],
        )
    a = attrs.model_dump(mode="json", exclude_none=True)
    problems = _check_urls("attributes.links", a.get("links", [])) + _check_urls("attributes.linked_websites", a.get("linked_websites", []))
    if source_url and parse_url(source_url) is None:
        problems.append({"field": "source_url", "message": "not a valid http(s) URL"})
    if a.get("store_url") and parse_url(a["store_url"]) is None:
        problems.append({"field": "attributes.store_url", "message": "not a valid http(s) URL"})
    if problems:
        raise ValidationFailure("Invalid URL value(s)", details=problems)

    name = (display_name or "").strip() or None
    if entity_type == EntityType.SOCIAL_PROFILE:
        if not platform:
            raise ValidationFailure("platform is required for social_profile", details=[{"field": "platform", "message": "required"}])
        handle = a["handle"].lower().lstrip("@")
        a["handle"] = a["handle"].lstrip("@")
        return NormalizedEntity(entity_type, f"{platform.lower().strip()}:{handle}", name or f"@{a['handle']}", a, platform.lower().strip(), source_url)
    if entity_type == EntityType.WEBSITE:
        p = parse_url(a["url"])
        if p is None:
            raise ValidationFailure("Invalid URL value(s)", details=[{"field": "attributes.url", "message": "not a valid http(s) URL"}])
        a["url"] = p.canonical
        return NormalizedEntity(entity_type, p.canonical, name or p.unicode_host, a, platform, source_url or p.canonical)
    if entity_type == EntityType.DOMAIN:
        p = parse_url(a["domain"])
        if p is None or p.is_ip:
            raise ValidationFailure("Invalid domain", details=[{"field": "attributes.domain", "message": "not a valid domain name"}])
        a["domain"] = p.host
        return NormalizedEntity(entity_type, p.host, name or p.unicode_host, a, platform, source_url)
    if entity_type == EntityType.IMAGE:
        cid = f"phash:{a['phash'].lower()}" if a.get("phash") else f"sha256:{a['sha256'].lower()}"
        return NormalizedEntity(entity_type, cid, name or cid, a, platform, source_url)
    # mobile app
    store = a.get("store", "other")
    a["package_id"] = a["package_id"].strip()
    return NormalizedEntity(entity_type, f"{store}:{a['package_id'].lower()}", name or a["app_name"], a, store, source_url or a.get("store_url"))


def merge_attributes(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(old)
    for k, v in new.items():
        if v is None:
            continue
        if isinstance(v, list) and isinstance(out.get(k), list):
            merged = list(dict.fromkeys(out[k] + v)) if all(isinstance(x, (str, int)) for x in out[k] + v) else out[k] + v
            if k == "post_timestamps":
                merged = sorted(set(merged))
            out[k] = merged[-_LIST_CAPS[k]:] if k in _LIST_CAPS else merged
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out


def ensure_source(db: Session, key: str, name: str, kind: SourceKind, description: str | None = None) -> DataSource:
    src = db.scalar(select(DataSource).where(DataSource.key == key))
    if src:
        return src
    src = DataSource(key=key, name=name, kind=kind, description=description)
    try:
        with db.begin_nested():
            db.add(src)
            db.flush()
    except IntegrityError:
        src = db.scalar(select(DataSource).where(DataSource.key == key))
    return src


def upsert_entity(
    db: Session, brand: Brand, norm: NormalizedEntity, provenance: Provenance, source: DataSource, actor: User | None, raw_payload: dict[str, Any],
) -> tuple[DigitalEntity, bool]:
    """Create the entity or merge into the existing record (same brand + type + canonical id). Does NOT commit."""
    now = datetime.now(UTC)
    key = (DigitalEntity.brand_id == brand.id, DigitalEntity.entity_type == norm.entity_type, DigitalEntity.canonical_id == norm.canonical_id)
    entity = db.scalar(select(DigitalEntity).where(*key).with_for_update())
    created = False
    if entity is None:
        candidate = DigitalEntity(
            brand_id=brand.id, entity_type=norm.entity_type, canonical_id=norm.canonical_id, display_name=norm.display_name[:300],
            platform=norm.platform, source_url=norm.source_url, provenance=provenance, attributes=norm.attributes,
            first_seen_at=now, last_seen_at=now, submission_count=1, created_by_id=actor.id if actor else None,
        )
        try:
            with db.begin_nested():
                db.add(candidate)
                db.flush()
            entity, created = candidate, True
        except IntegrityError:  # concurrent insert of the same entity: fall through to merge
            entity = db.scalar(select(DigitalEntity).where(*key).with_for_update())
    if not created:
        entity.attributes = merge_attributes(entity.attributes or {}, norm.attributes)
        if norm.display_name:
            entity.display_name = norm.display_name[:300]
        if norm.source_url:
            entity.source_url = norm.source_url
        if norm.platform:
            entity.platform = norm.platform
        if _RANK[provenance] > _RANK[entity.provenance]:
            entity.provenance = provenance
        entity.last_seen_at = now
        entity.submission_count += 1
    db.add(CollectionRecord(
        data_source_id=source.id, brand_id=brand.id, entity_id=entity.id, provenance=provenance, was_new_entity=created,
        raw_payload=raw_payload, collected_at=now, submitted_by_id=actor.id if actor else None,
    ))
    db.flush()
    return entity, created


def submit_entity(db: Session, actor: User, data: EntitySubmit) -> tuple[DigitalEntity, bool, str | None]:
    brand = get_brand_for_user(db, actor, data.brand_id)
    norm = normalize_submission(data.entity_type, data.display_name, data.platform, data.source_url, data.attributes)
    if data.provenance == Provenance.SYNTHETIC:
        source = ensure_source(db, "synthetic-demo", "Synthetic demonstration data", SourceKind.SYNTHETIC, "Clearly labelled sample data - not real observations")
    else:
        source = ensure_source(db, "manual", "Manual submission", SourceKind.MANUAL, "Entered by a human user; unverified")
    entity, created = upsert_entity(db, brand, norm, data.provenance, source, actor, {"submitted": data.model_dump(mode="json", exclude={"analyze"})})
    official = is_official_asset(entity, brand.references)
    audit.record(db, actor, "entity.create" if created else "entity.update", "entity", entity.id,
                 details={"entity_type": entity.entity_type.value, "canonical_id": entity.canonical_id, "provenance": data.provenance.value, "created": created},
                 organization_id=brand.organization_id)
    db.commit()
    return entity, created, official

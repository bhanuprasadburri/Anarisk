"""Brand reference normalisation and the 'is this actually an official asset?' guard."""
from __future__ import annotations

import hashlib
from typing import Iterable

from app.models import BrandReference, DigitalEntity
from app.models.enums import EntityType, ReferenceKind
from app.services.detection.common import attrs
from app.utils.text import normalize_text, squash_identity
from app.utils.urls import parse_url


def normalize_reference(kind: ReferenceKind, value: str) -> str:
    v = value.strip()
    if kind == ReferenceKind.DOMAIN:
        p = parse_url(v)
        return p.registrable_domain if p else v.lower()
    if kind == ReferenceKind.HANDLE:
        return v.lower().lstrip("@")
    if kind == ReferenceKind.APP_PACKAGE:
        return v.lower()
    if kind == ReferenceKind.IMAGE:
        return v.lower()
    if kind == ReferenceKind.BIO:
        return hashlib.sha1(normalize_text(v).encode()).hexdigest()
    return squash_identity(v) or normalize_text(v)


def is_official_asset(entity: DigitalEntity, refs: Iterable[BrandReference]) -> str | None:
    """Return a human-readable reason if the entity IS one of the brand's registered official assets."""
    a = attrs(entity)
    refs = list(refs)
    if entity.entity_type in (EntityType.WEBSITE, EntityType.DOMAIN):
        p = parse_url(entity.source_url or a.get("url") or entity.canonical_id)
        if p:
            for r in refs:
                if r.kind == ReferenceKind.DOMAIN and r.normalized_value == p.registrable_domain:
                    return f"domain {p.registrable_domain} is a registered official brand domain"
    if entity.entity_type == EntityType.SOCIAL_PROFILE and a.get("handle"):
        h = str(a["handle"]).lower().lstrip("@")
        for r in refs:
            if r.kind == ReferenceKind.HANDLE and r.normalized_value == h and (not r.platform or r.platform.lower() == (entity.platform or "").lower()):
                return f"handle @{h} is a registered official brand handle"
    if entity.entity_type == EntityType.MOBILE_APP and a.get("package_id"):
        pk = str(a["package_id"]).lower()
        for r in refs:
            if r.kind == ReferenceKind.APP_PACKAGE and r.normalized_value == pk:
                return f"package {pk} is a registered official brand app"
    return None

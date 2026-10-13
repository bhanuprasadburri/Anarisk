from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError
from app.models import EvidenceRecord, User
from app.models.enums import EvidenceKind, Provenance
from app.repositories.access import brand_scope, get_entity_for_user
from app.schemas.evidence import EvidenceCreate
from app.services import audit
from app.utils.images import inspect_image, perceptual_hash, sha256_hex


def create_evidence(db: Session, actor: User, data: EvidenceCreate) -> EvidenceRecord:
    entity = get_entity_for_user(db, actor, data.entity_id)
    ev = EvidenceRecord(
        entity_id=entity.id, brand_id=entity.brand_id, kind=data.kind, title=data.title, description=data.description,
        source_url=data.source_url, provenance=data.provenance, text_content=data.text_content, meta=data.metadata,
        collected_at=data.collected_at or datetime.now(UTC), created_by_id=actor.id,
    )
    db.add(ev)
    db.flush()
    audit.record(db, actor, "evidence.create", "evidence", ev.id, details={"entity_id": str(entity.id), "kind": ev.kind.value})
    db.commit()
    return ev


def upload_image_evidence(
    db: Session, actor: User, entity_id: uuid.UUID, data: bytes, *, title: str, description: str | None, kind: EvidenceKind,
    provenance: Provenance, original_filename: str | None,
) -> EvidenceRecord:
    entity = get_entity_for_user(db, actor, entity_id)
    info = inspect_image(data)  # validates real content, size, pixel budget
    sha = sha256_hex(data)
    if db.scalar(select(EvidenceRecord.id).where(EvidenceRecord.entity_id == entity.id, EvidenceRecord.sha256 == sha)):
        raise ConflictError("This file is already attached to the entity as evidence", code="duplicate_evidence")
    rel = Path("evidence") / str(entity.brand_id) / f"{sha}.{info['extension']}"  # name derived from content hash, never the client filename
    dest = Path(get_settings().upload_dir) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(data)
    safe_name = "".join(c for c in (original_filename or "") if c.isalnum() or c in "._- ")[:120] or None
    ev = EvidenceRecord(
        entity_id=entity.id, brand_id=entity.brand_id, kind=kind, title=title, description=description, provenance=provenance,
        content_type=info["content_type"], file_path=str(rel), sha256=sha, size_bytes=len(data), perceptual_hash=perceptual_hash(data),
        meta={"width": info["width"], "height": info["height"], "format": info["format"], "original_filename": safe_name},
        collected_at=datetime.now(UTC), created_by_id=actor.id,
    )
    db.add(ev)
    db.flush()
    audit.record(db, actor, "evidence.upload", "evidence", ev.id, details={"entity_id": str(entity.id), "sha256": sha, "size": len(data)})
    db.commit()
    return ev


def get_evidence(db: Session, actor: User, evidence_id: uuid.UUID) -> EvidenceRecord:
    ev = db.get(EvidenceRecord, evidence_id)
    if ev is None:
        raise NotFoundError("Evidence not found")
    get_entity_for_user(db, actor, ev.entity_id)
    return ev


def list_evidence(db: Session, actor: User, page: int, page_size: int, entity_id: uuid.UUID | None = None, kind: EvidenceKind | None = None):
    stmt = select(EvidenceRecord).where(brand_scope(actor, EvidenceRecord.brand_id))
    if entity_id:
        stmt = stmt.where(EvidenceRecord.entity_id == entity_id)
    if kind:
        stmt = stmt.where(EvidenceRecord.kind == kind)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(EvidenceRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return rows, total


def evidence_file_path(ev: EvidenceRecord) -> Path:
    if not ev.file_path:
        raise NotFoundError("This evidence record has no file")
    base = Path(get_settings().upload_dir).resolve()
    p = (base / ev.file_path).resolve()
    if base not in p.parents or not p.is_file():  # path-traversal / missing file guard
        raise NotFoundError("Evidence file not found")
    return p

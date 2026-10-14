from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import DigitalEntity, User
from app.models.enums import EntityType, Provenance, Severity
from app.repositories.access import brand_scope

SORTS = {"risk_score": DigitalEntity.current_risk_score, "last_seen_at": DigitalEntity.last_seen_at, "first_seen_at": DigitalEntity.first_seen_at,
         "display_name": DigitalEntity.display_name, "confidence": DigitalEntity.current_confidence, "created_at": DigitalEntity.created_at}


def list_entities(db: Session, actor: User, *, page: int, page_size: int, brand_id: uuid.UUID | None = None, entity_type: EntityType | None = None,
                  severities: list[Severity] | None = None, min_risk: float | None = None, max_risk: float | None = None,
                  provenance: Provenance | None = None, q: str | None = None, assessed: bool | None = None, sort: str = "last_seen_at", order: str = "desc"):
    stmt = select(DigitalEntity).where(brand_scope(actor, DigitalEntity.brand_id))
    if brand_id:
        stmt = stmt.where(DigitalEntity.brand_id == brand_id)
    if entity_type:
        stmt = stmt.where(DigitalEntity.entity_type == entity_type)
    if severities:
        stmt = stmt.where(DigitalEntity.current_severity.in_(severities))
    if min_risk is not None:
        stmt = stmt.where(DigitalEntity.current_risk_score >= min_risk)
    if max_risk is not None:
        stmt = stmt.where(DigitalEntity.current_risk_score <= max_risk)
    if provenance:
        stmt = stmt.where(DigitalEntity.provenance == provenance)
    if assessed is not None:
        stmt = stmt.where(DigitalEntity.last_assessed_at.is_not(None) if assessed else DigitalEntity.last_assessed_at.is_(None))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(DigitalEntity.display_name.ilike(like), DigitalEntity.canonical_id.ilike(like),
                              DigitalEntity.source_url.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    col = SORTS[sort]
    col = col.desc().nulls_last() if order == "desc" else col.asc().nulls_last()
    rows = db.scalars(stmt.order_by(col, DigitalEntity.id).offset((page - 1) * page_size).limit(page_size)).all()
    return rows, total


def related_entities(db: Session, actor: User, entity_id: uuid.UUID, limit: int = 12):
    """Neighbours in the risk graph, strongest relationships first."""
    from app.models import EntityRelationship
    from app.schemas.entity import RelatedEntityOut
    from app.schemas.graph import GraphNode

    rows = db.execute(
        select(EntityRelationship, DigitalEntity)
        .join(DigitalEntity, DigitalEntity.id == EntityRelationship.target_entity_id)
        .where(EntityRelationship.source_entity_id == entity_id, brand_scope(actor, DigitalEntity.brand_id))
        .order_by(EntityRelationship.confidence.desc(), EntityRelationship.id)
    ).all()
    rows += db.execute(
        select(EntityRelationship, DigitalEntity)
        .join(DigitalEntity, DigitalEntity.id == EntityRelationship.source_entity_id)
        .where(EntityRelationship.target_entity_id == entity_id, brand_scope(actor, DigitalEntity.brand_id))
        .order_by(EntityRelationship.confidence.desc(), EntityRelationship.id)
    ).all()
    rows.sort(key=lambda r: r[0].confidence, reverse=True)
    out = []
    for rel, e in rows[:limit]:
        out.append(RelatedEntityOut(
            entity=GraphNode(id=str(e.id), entity_type=e.entity_type, label=e.display_name, brand_id=str(e.brand_id),
                             risk_score=e.current_risk_score, confidence=e.current_confidence, severity=e.current_severity,
                             provenance=e.provenance.value),
            relationship_type=rel.relationship_type.value, confidence=rel.confidence))
    return out


def delete_entity(db: Session, actor: User, entity_id: uuid.UUID) -> None:
    """Administrators only. Cascades to evidence records/relationships in the database; stored files are removed too."""
    from pathlib import Path

    from app.core.config import get_settings
    from app.core.errors import ForbiddenError
    from app.models.enums import UserRole
    from app.services import audit

    if actor.role != UserRole.ADMIN:
        raise ForbiddenError("Only administrators may delete entities")
    e = db.scalar(select(DigitalEntity).where(brand_scope(actor, DigitalEntity.brand_id), DigitalEntity.id == entity_id))
    if e is None:
        raise NotFoundError("Entity not found")
    details = {"entity_type": e.entity_type.value, "canonical_id": e.canonical_id, "display_name": e.display_name,
               "provenance": e.provenance.value,
               "cascades": ["evidence_records", "entity_relationships", "risk_assessments (kept in place via SET NULL/CASCADE as configured)"]}
    # remove stored evidence files (records cascade in the database)
    from app.models import EvidenceRecord

    upload_base = Path(get_settings().upload_dir).resolve()
    removed = 0
    for ev in db.scalars(select(EvidenceRecord).where(EvidenceRecord.entity_id == e.id)):
        if ev.file_path:
            p = (upload_base / ev.file_path).resolve()
            if upload_base in p.parents and p.is_file():
                try:
                    p.unlink()
                    removed += 1
                except OSError:
                    pass
    details["files_removed"] = removed
    audit.record(db, actor, "entity.delete", "entity", e.id, details=details)
    db.delete(e)
    db.commit()

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import DigitalEntity, User
from app.models.enums import EntityType, Provenance, Severity
from app.repositories.access import brand_scope

SORTS = {"risk_score": DigitalEntity.current_risk_score, "last_seen_at": DigitalEntity.last_seen_at, "first_seen_at": DigitalEntity.first_seen_at,
         "display_name": DigitalEntity.display_name, "confidence": DigitalEntity.current_confidence}


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
        stmt = stmt.where(or_(DigitalEntity.display_name.ilike(like), DigitalEntity.canonical_id.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    col = SORTS[sort]
    col = col.desc().nulls_last() if order == "desc" else col.asc().nulls_last()
    rows = db.scalars(stmt.order_by(col, DigitalEntity.id).offset((page - 1) * page_size).limit(page_size)).all()
    return rows, total

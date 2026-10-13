import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, require_permission
from app.db.session import get_db
from app.models import AuditLog, User
from app.models.enums import UserRole
from app.schemas.common import ORM, Page

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditOut(ORM):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_email: str | None
    organization_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    ip_address: str | None
    details: dict
    created_at: datetime


@router.get("", response_model=Page[AuditOut], summary="Audit history (administrators: all; others: own organization only)")
def list_(p: Pagination = Depends(), action: str | None = Query(None, max_length=100), resource_type: str | None = None, resource_id: str | None = None,
          actor_id: uuid.UUID | None = None, since: datetime | None = None, until: datetime | None = None,
          user: User = Depends(require_permission("audit:read")), db: Session = Depends(get_db)):
    stmt = select(AuditLog)
    if user.role != UserRole.ADMIN:
        stmt = stmt.where(AuditLog.organization_id == user.organization_id) if user.organization_id else stmt.where(AuditLog.id.is_(None))
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"{action}%"))
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditLog.resource_id == resource_id)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if since:
        stmt = stmt.where(AuditLog.created_at >= since)
    if until:
        stmt = stmt.where(AuditLog.created_at <= until)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(AuditLog.created_at.desc()).offset((p.page - 1) * p.page_size).limit(p.page_size)).all()
    return Page.build([AuditOut.model_validate(r) for r in rows], total, p.page, p.page_size)

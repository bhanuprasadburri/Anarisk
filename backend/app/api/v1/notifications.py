from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user
from app.db.session import get_db
from app.models import Notification, User
from app.schemas.notification import MarkReadRequest, MarkReadResponse, NotificationPage, NotificationOut
from app.services import notifications as svc

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationPage, summary="Your notifications (newest first) plus a top-level unread_count")
def list_(p: Pagination = Depends(), unread_only: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Notification.created_at.desc(), Notification.id)
        .offset((p.page - 1) * p.page_size).limit(p.page_size)
    ).all()
    pages = max(1, -(-total // p.page_size)) if p.page_size else 1
    return NotificationPage(
        items=[NotificationOut.model_validate(r) for r in rows], total=total,
        unread_count=svc.unread_count(db, user.id), page=p.page, page_size=p.page_size, pages=pages,
    )


@router.post("/read", response_model=MarkReadResponse, summary="Mark notifications read (omit ids to mark ALL read)")
def mark_read(body: MarkReadRequest | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = body.ids if body else None
    updated, unread = svc.mark_read(db, user.id, ids)
    return MarkReadResponse(updated=updated, unread_count=unread)

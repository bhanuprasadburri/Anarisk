"""Organization / brand scoping. Cross-organization resources are reported as 404 (not 403) so that
identifiers cannot be enumerated across tenants."""
from __future__ import annotations

import uuid

from sqlalchemy import ColumnElement, false, select, true
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Brand, DigitalEntity, User
from app.models.enums import UserRole


def is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def brand_scope(user: User, brand_id_column) -> ColumnElement[bool]:
    """SQL predicate restricting `brand_id_column` to brands the user may access."""
    if is_admin(user):
        return true()
    if user.organization_id is None:
        return false()
    return brand_id_column.in_(select(Brand.id).where(Brand.organization_id == user.organization_id))


def can_access_brand(db: Session, user: User, brand: Brand) -> bool:
    return is_admin(user) or (user.organization_id is not None and brand.organization_id == user.organization_id)


def get_brand_for_user(db: Session, user: User, brand_id: uuid.UUID, *, for_update: bool = False) -> Brand:
    stmt = select(Brand).where(Brand.id == brand_id)
    if for_update:
        stmt = stmt.with_for_update()
    brand = db.scalar(stmt)
    if brand is None or not can_access_brand(db, user, brand):
        raise NotFoundError("Brand not found")
    return brand


def get_entity_for_user(db: Session, user: User, entity_id: uuid.UUID) -> DigitalEntity:
    e = db.get(DigitalEntity, entity_id)
    if e is None:
        raise NotFoundError("Entity not found")
    get_brand_for_user(db, user, e.brand_id)  # raises 404 if out of scope
    return e

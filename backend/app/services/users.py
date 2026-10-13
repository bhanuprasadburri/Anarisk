from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationFailure
from app.core.security import (
    burn_password_check, create_access_token, hash_password, validate_password_strength, verify_password,
)
from app.models import Organization, User
from app.models.enums import UserRole
from app.schemas.auth import OrganizationCreate, UserCreate, UserUpdate
from app.services import audit

INVALID_LOGIN = "Invalid email or password"


def authenticate(db: Session, email: str, password: str) -> tuple[str, int]:
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    if user is None:
        burn_password_check(password)
        raise UnauthorizedError(INVALID_LOGIN, code="invalid_credentials")
    if not verify_password(password, user.hashed_password):
        audit.record(db, user, "auth.login_failed", "user", user.id)
        db.commit()
        raise UnauthorizedError(INVALID_LOGIN, code="invalid_credentials")
    if not user.is_active:
        # Same message as a bad password: do not reveal that the account exists but is disabled.
        raise UnauthorizedError(INVALID_LOGIN, code="invalid_credentials")
    user.last_login_at = datetime.now(UTC)
    audit.record(db, user, "auth.login", "user", user.id)
    db.commit()
    return create_access_token(user.id)


def register_public(db: Session, email: str, full_name: str, password: str) -> User:
    """Self-registration. Creates a brand_owner with NO organization: no data access until an admin assigns one.
    A caller can never choose their own role or organization here."""
    if not get_settings().allow_public_registration:
        raise ForbiddenError("Public registration is disabled", code="registration_disabled")
    validate_password_strength(password)
    user = User(email=email.strip().lower(), full_name=full_name.strip(), hashed_password=hash_password(password), role=UserRole.BRAND_OWNER)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("An account with this email already exists", code="email_taken")
    audit.record(db, user, "auth.register", "user", user.id)
    db.commit()
    return user


def create_user(db: Session, actor: User, data: UserCreate) -> User:
    validate_password_strength(data.password)
    if data.role != UserRole.ADMIN and data.organization_id is None:
        pass  # allowed: such a user has no data access until assigned
    if data.organization_id and db.get(Organization, data.organization_id) is None:
        raise ValidationFailure("organization_id does not exist")
    user = User(
        email=data.email.strip().lower(), full_name=data.full_name.strip(), hashed_password=hash_password(data.password),
        role=data.role, organization_id=data.organization_id,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("An account with this email already exists", code="email_taken")
    audit.record(db, actor, "user.create", "user", user.id, details={"role": data.role.value, "organization_id": str(data.organization_id) if data.organization_id else None})
    db.commit()
    return user


def update_user(db: Session, actor: User, user_id: uuid.UUID, data: UserUpdate) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    changes: dict = {}
    if data.full_name is not None:
        user.full_name = data.full_name.strip()
        changes["full_name"] = True
    if data.role is not None and data.role != user.role:
        if user.id == actor.id:
            raise ForbiddenError("You cannot change your own role")
        changes["role"] = [user.role.value, data.role.value]
        user.role = data.role
    if data.is_active is not None and data.is_active != user.is_active:
        if user.id == actor.id and not data.is_active:
            raise ForbiddenError("You cannot deactivate your own account")
        changes["is_active"] = data.is_active
        user.is_active = data.is_active
    if data.clear_organization:
        user.organization_id = None
        changes["organization_id"] = None
    elif data.organization_id is not None:
        if db.get(Organization, data.organization_id) is None:
            raise ValidationFailure("organization_id does not exist")
        user.organization_id = data.organization_id
        changes["organization_id"] = str(data.organization_id)
    if data.password:
        validate_password_strength(data.password)
        user.hashed_password = hash_password(data.password)
        changes["password_changed"] = True
    audit.record(db, actor, "user.update", "user", user.id, details=changes, organization_id=user.organization_id)
    db.commit()
    return user


def create_organization(db: Session, actor: User, data: OrganizationCreate) -> Organization:
    org = Organization(name=data.name, slug=data.slug, description=data.description)
    db.add(org)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Organization slug already exists", code="slug_taken")
    audit.record(db, actor, "organization.create", "organization", org.id, organization_id=org.id)
    db.commit()
    return org

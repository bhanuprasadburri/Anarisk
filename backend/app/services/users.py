from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, DomainError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationFailure
from app.core.security import (
    burn_password_check, create_access_token, hash_password, validate_password_strength, verify_password,
)
from app.models import Organization, PasswordResetToken, User
from app.models.enums import UserRole
from app.schemas.auth import OrganizationCreate, UpdateMeRequest, UserCreate, UserUpdate
from app.services import audit

log = logging.getLogger(__name__)
INVALID_LOGIN = "Invalid email or password"
RESET_TOKEN_TTL_MINUTES = 30
MAX_PREFERENCES_BYTES = 8192


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


# ---------- password recovery / self-service profile ----------
def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def forgot_password(db: Session, email: str) -> dict:
    """Always returns {"status": "sent"} - unknown addresses behave exactly like known ones (no enumeration).
    In development the token is also returned as `dev_reset_token` so the UI can finish the flow without SMTP."""
    s = get_settings()
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    if user is None or not user.is_active:
        log.info("Password reset requested for an unknown or inactive address - ignored (no user enumeration)")
        return {"status": "sent"}
    token = secrets.token_urlsafe(32)  # 32 random bytes, stored ONLY as a SHA-256 hash
    db.add(PasswordResetToken(
        user_id=user.id, token_hash=_token_hash(token),
        expires_at=datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    ))
    audit.record(db, user, "auth.password_reset_request", "user", user.id)
    db.commit()
    link = f"/reset-password?token={token}"
    if s.environment == "production":
        # No secrets in production logs: the message states that a link was created without printing it.
        log.info("Password reset requested for %s: a 30-minute reset link was created (token not logged in production)",
                 user.email)
        return {"status": "sent"}
    log.info("PASSWORD RESET for %s (expires in %s minutes) -> %s",
             user.email, RESET_TOKEN_TTL_MINUTES, link)
    return {"status": "sent", "dev_reset_token": token, "dev_only": True}


def reset_password(db: Session, token: str, new_password: str) -> User:
    invalid = DomainError("This reset link is invalid or has expired; request a new one",
                          code="invalid_or_expired_token", status_code=400)
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == _token_hash(token)))
    now = datetime.now(UTC)
    if row is None or row.used_at is not None or row.expires_at <= now:
        raise invalid
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise invalid
    validate_password_strength(new_password)
    user.hashed_password = hash_password(new_password)
    row.used_at = now
    db.execute(update(PasswordResetToken).where(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None), PasswordResetToken.id != row.id
    ).values(used_at=now))  # one click invalidates every other outstanding link
    audit.record(db, user, "auth.password_reset", "user", user.id)
    db.commit()
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> User:
    if not verify_password(current_password, user.hashed_password):
        raise DomainError("Current password is incorrect", code="invalid_current_password", status_code=400)
    validate_password_strength(new_password)
    user.hashed_password = hash_password(new_password)
    db.execute(update(PasswordResetToken).where(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
    ).values(used_at=datetime.now(UTC)))  # a successful change invalidates pending reset links
    audit.record(db, user, "auth.password_change", "user", user.id)
    db.commit()
    return user


def update_own_profile(db: Session, user: User, data: UpdateMeRequest) -> User:
    changes: dict = {}
    if data.full_name is not None and data.full_name.strip() != user.full_name:
        user.full_name = data.full_name.strip()
        changes["full_name"] = True
    if data.email is not None:
        email = data.email.strip().lower()
        if email != user.email:
            taken = db.scalar(select(User.id).where(func.lower(User.email) == email, User.id != user.id))
            if taken:
                raise ConflictError("An account with this email already exists", code="email_taken")
            user.email = email
            changes["email"] = True
    if data.preferences is not None:
        try:
            if len(json.dumps(data.preferences)) > MAX_PREFERENCES_BYTES:
                raise ValueError("too large")
        except (TypeError, ValueError):
            raise ValidationFailure(f"preferences must be JSON-serialisable and smaller than {MAX_PREFERENCES_BYTES} bytes")
        user.preferences = data.preferences
        changes["preferences"] = sorted(str(k) for k in data.preferences)
    if not changes:
        return user
    audit.record(db, user, "user.update_self", "user", user.id, details=changes)
    db.commit()
    return user

"""Password hashing (bcrypt over a SHA-256 prehash, avoiding bcrypt's 72-byte limit) and JWT helpers."""
from __future__ import annotations

import base64
import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.errors import UnauthorizedError, ValidationFailure


def _prehash(password: str) -> bytes:
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), hashed.encode("ascii"))
    except ValueError:
        return False


# Used to equalise timing when the account does not exist.
_DUMMY_HASH = hash_password("dummy-password-for-timing-equalisation")


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def validate_password_strength(password: str) -> None:
    problems = []
    if len(password) < 10:
        problems.append("at least 10 characters")
    if not re.search(r"[A-Za-z]", password):
        problems.append("at least one letter")
    if not re.search(r"\d", password):
        problems.append("at least one digit")
    if len(password) > 256:
        problems.append("at most 256 characters")
    if problems:
        raise ValidationFailure("Password does not meet requirements: " + ", ".join(problems))


def create_access_token(user_id: uuid.UUID, *, expires_minutes: int | None = None) -> tuple[str, int]:
    s = get_settings()
    minutes = s.access_token_expire_minutes if expires_minutes is None else expires_minutes
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "jti": uuid.uuid4().hex,
        "typ": "access",
    }
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm), minutes * 60


def decode_access_token(token: str) -> dict:
    s = get_settings()
    try:
        payload = jwt.decode(
            token, s.secret_key, algorithms=[s.jwt_algorithm], options={"require": ["exp", "sub", "iat"]}
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired", code="token_expired")
    except jwt.PyJWTError:
        raise UnauthorizedError("Could not validate credentials", code="invalid_token")
    if payload.get("typ") != "access":
        raise UnauthorizedError("Could not validate credentials", code="invalid_token")
    return payload

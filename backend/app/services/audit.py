from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.context import request_ip
from app.models import AuditLog, User

_SENSITIVE = ("password", "token", "secret", "authorization", "hashed")


def _scrub(details: dict[str, Any] | None) -> dict[str, Any]:
    out = {}
    for k, v in (details or {}).items():
        sensitive = any(x in k.lower() for x in _SENSITIVE) and not isinstance(v, bool)  # booleans (e.g. password_changed) carry no secret
        out[k] = "[redacted]" if sensitive else v
    return out


def record(
    db: Session, actor: User | None, action: str, resource_type: str, resource_id: Any = None, *,
    details: dict[str, Any] | None = None, organization_id: uuid.UUID | None = None,
) -> AuditLog:
    """Adds an audit row to the CURRENT transaction (caller commits) so it is atomic with the change."""
    row = AuditLog(
        actor_id=actor.id if actor else None, actor_email=actor.email if actor else None,
        organization_id=organization_id if organization_id else (actor.organization_id if actor else None),
        action=action, resource_type=resource_type, resource_id=str(resource_id) if resource_id else None,
        ip_address=request_ip.get(), details=_scrub(details),
    )
    db.add(row)
    return row

"""Role -> permission matrix. Permissions are checked by `require_permission` dependencies.

Scope rules (enforced in `app/api/deps.py` and repositories, not here):
  * administrator: global access to every organization and brand.
  * all other roles: only brands whose organization == user.organization_id. A user with no organization
    can authenticate but can see no brand data.
  * partner: additionally limited to cases that have been escalated (partner handoffs).
"""
from __future__ import annotations

from app.models.enums import UserRole

P = {
    "user:manage", "org:manage", "brand:read", "brand:write", "entity:read", "entity:submit", "entity:analyze",
    "evidence:read", "evidence:write", "graph:read", "graph:write", "case:read", "case:create", "case:triage",
    "case:assign", "case:escalate", "case:resolve", "case:reopen", "case:note", "dashboard:read", "audit:read",
    "connector:run", "url:inspect",
}

ROLE_PERMISSIONS: dict[UserRole, frozenset[str]] = {
    UserRole.ADMIN: frozenset(P),
    UserRole.INVESTIGATOR: frozenset({
        "brand:read", "entity:read", "entity:submit", "entity:analyze", "evidence:read", "evidence:write",
        "graph:read", "graph:write", "case:read", "case:create", "case:triage", "case:assign", "case:escalate",
        "case:resolve", "case:note", "dashboard:read", "audit:read", "connector:run", "url:inspect",
    }),
    UserRole.BRAND_OWNER: frozenset({
        "brand:read", "brand:write", "entity:read", "entity:submit", "evidence:read", "evidence:write",
        "graph:read", "case:read", "case:note", "dashboard:read",
    }),
    UserRole.PARTNER: frozenset({"brand:read", "entity:read", "evidence:read", "case:read", "case:note"}),
}


def has_permission(role: UserRole, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import User
from app.repositories.access import get_brand_for_user
from app.services import audit
from app.services.connectors import get_connector
from app.services.ingestion import ensure_source, upsert_entity


def run_connector(db: Session, actor: User, key: str, brand_id: uuid.UUID, query: dict[str, Any]):
    conn = get_connector(key)
    if conn is None:
        raise NotFoundError("Unknown connector")
    if not conn.is_configured():
        raise ConflictError(f"Connector '{key}' is not configured: {conn.configuration_help() or 'missing credentials'}", code="connector_not_configured")
    brand = get_brand_for_user(db, actor, brand_id)
    source = ensure_source(db, conn.key, conn.name, conn.kind, conn.description)
    items = conn.collect(brand, query)
    out = []
    for norm in items:
        entity, created = upsert_entity(db, brand, norm, conn.provenance, source, actor, {"connector": conn.key, "query": query, "canonical_id": norm.canonical_id})
        out.append((entity, created))
    audit.record(db, actor, "collection.run", "connector", conn.key, details={"brand_id": str(brand.id), "items": len(out), "provenance": conn.provenance.value}, organization_id=brand.organization_id)
    db.commit()
    return out

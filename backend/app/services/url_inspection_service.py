from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import ValidationFailure
from app.models import EvidenceRecord, User
from app.models.enums import EvidenceKind, Provenance
from app.repositories.access import get_entity_for_user
from app.services import audit
from app.services.url_inspector import SafeFetcher
from app.utils.urls import parse_url


def inspect_entity_url(db: Session, actor: User, entity_id: uuid.UUID, url: str, fetcher: SafeFetcher | None = None) -> EvidenceRecord:
    entity = get_entity_for_user(db, actor, entity_id)
    if parse_url(url) is None:
        raise ValidationFailure("url is not a valid http(s) URL")
    result = (fetcher or SafeFetcher()).fetch(url)  # raises SsrfBlocked / UrlFetchDisabled / DomainError
    ev = EvidenceRecord(
        entity_id=entity.id, brand_id=entity.brand_id, kind=EvidenceKind.URL_INSPECTION, title=f"URL inspection: {result.final_url}"[:300],
        description="Metadata captured by the SSRF-guarded inspector. Page content is not stored or executed.",
        source_url=result.final_url, provenance=Provenance.COLLECTED, content_type=result.content_type, sha256=result.sha256,
        size_bytes=result.size_bytes, collected_at=datetime.now(UTC), created_by_id=actor.id,
        meta={"status": result.status, "title": result.title, "redirects": result.redirects, "truncated": result.truncated, "server": result.server_header, "elapsed_ms": result.elapsed_ms},
    )
    db.add(ev)
    db.flush()
    audit.record(db, actor, "url.inspect", "evidence", ev.id, details={"entity_id": str(entity.id), "url": result.final_url, "status": result.status})
    db.commit()
    return ev

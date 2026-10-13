from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.enums import EvidenceKind, Provenance
from app.schemas.common import ORM


class EvidenceCreate(BaseModel):
    entity_id: uuid.UUID
    kind: Literal[EvidenceKind.TEXT, EvidenceKind.URL, EvidenceKind.WHOIS, EvidenceKind.OTHER]
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(None, max_length=5000)
    source_url: str | None = Field(None, max_length=2048)
    text_content: str | None = Field(None, max_length=20000)
    provenance: Literal[Provenance.MANUAL, Provenance.SYNTHETIC] = Provenance.MANUAL
    metadata: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime | None = None


class EvidenceOut(ORM):
    id: uuid.UUID
    entity_id: uuid.UUID
    brand_id: uuid.UUID
    kind: EvidenceKind
    title: str
    description: str | None
    source_url: str | None
    provenance: Provenance
    content_type: str | None
    sha256: str | None
    size_bytes: int | None
    perceptual_hash: str | None
    has_file: bool = False
    text_content: str | None
    metadata: dict[str, Any] = Field(validation_alias="meta", default_factory=dict)
    collected_at: datetime
    created_at: datetime

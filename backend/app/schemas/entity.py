from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import EntityType, Provenance, Severity
from app.schemas.common import ORM
from app.utils.images import is_valid_phash


class _Attrs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Hosting(_Attrs):
    ip: str | None = Field(None, max_length=64)
    nameservers: list[str] = Field(default_factory=list, max_length=10)
    registrar: str | None = Field(None, max_length=200)


class CommonAttrs(_Attrs):
    image_phashes: list[str] = Field(default_factory=list, max_length=50)
    links: list[str] = Field(default_factory=list, max_length=50)
    hosting: Hosting | None = None

    @field_validator("image_phashes")
    @classmethod
    def _hashes(cls, v):
        for h in v:
            if not is_valid_phash(h):
                raise ValueError(f"invalid perceptual hash '{h}' (expected 16 hex chars)")
        return [h.lower() for h in v]

    @field_validator("links")
    @classmethod
    def _links(cls, v):
        if any(len(u) > 2048 for u in v):
            raise ValueError("link too long")
        return v


class SocialProfileAttrs(CommonAttrs):
    handle: str = Field(min_length=1, max_length=100)
    bio: str | None = Field(None, max_length=5000)
    followers_count: int | None = Field(None, ge=0)
    following_count: int | None = Field(None, ge=0)
    account_created_at: datetime | None = None
    post_timestamps: list[datetime] = Field(default_factory=list, max_length=1000)
    profile_image_phash: str | None = None

    @field_validator("profile_image_phash")
    @classmethod
    def _p(cls, v):
        if v is not None and not is_valid_phash(v):
            raise ValueError("invalid perceptual hash")
        return v.lower() if v else v


class WebsiteAttrs(CommonAttrs):
    url: str = Field(min_length=3, max_length=2048)
    page_title: str | None = Field(None, max_length=500)
    registered_at: datetime | None = None


class DomainAttrs(CommonAttrs):
    domain: str = Field(min_length=3, max_length=253)
    registered_at: datetime | None = None


class ImageAttrs(_Attrs):
    phash: str | None = None
    sha256: str | None = Field(None, pattern=r"^[0-9a-fA-F]{64}$")
    source_note: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def _one(self):
        if not self.phash and not self.sha256:
            raise ValueError("image entities need a phash or sha256")
        if self.phash and not is_valid_phash(self.phash):
            raise ValueError("invalid perceptual hash")
        return self


class MobileAppAttrs(CommonAttrs):
    app_name: str = Field(min_length=1, max_length=300)
    package_id: str = Field(min_length=3, max_length=300)
    store: Literal["google_play", "app_store", "other"] = "other"
    publisher_name: str | None = Field(None, max_length=300)
    store_url: str | None = Field(None, max_length=2048)
    description: str | None = Field(None, max_length=10000)
    permissions: list[str] | None = Field(None, max_length=200)
    permissions_source: Literal["store_listing", "manual"] | None = None
    linked_websites: list[str] = Field(default_factory=list, max_length=20)
    published_at: datetime | None = None


ATTR_MODELS: dict[EntityType, type[_Attrs]] = {
    EntityType.SOCIAL_PROFILE: SocialProfileAttrs, EntityType.WEBSITE: WebsiteAttrs, EntityType.DOMAIN: DomainAttrs,
    EntityType.IMAGE: ImageAttrs, EntityType.MOBILE_APP: MobileAppAttrs,
}


class EntitySubmit(BaseModel):
    brand_id: uuid.UUID
    entity_type: EntityType
    display_name: str | None = Field(None, max_length=300)
    platform: str | None = Field(None, max_length=64, description="Social platform (required for social_profile)")
    source_url: str | None = Field(None, max_length=2048)
    provenance: Literal[Provenance.MANUAL, Provenance.SYNTHETIC] = Provenance.MANUAL
    attributes: dict[str, Any] = Field(default_factory=dict)
    analyze: bool = Field(False, description="Run detection immediately after saving")


class EntityOut(ORM):
    id: uuid.UUID
    brand_id: uuid.UUID
    entity_type: EntityType
    canonical_id: str
    display_name: str
    platform: str | None
    source_url: str | None
    provenance: Provenance
    attributes: dict[str, Any]
    first_seen_at: datetime
    last_seen_at: datetime
    submission_count: int
    current_risk_score: float | None
    current_confidence: float | None
    current_severity: Severity
    last_assessed_at: datetime | None
    created_at: datetime


class EntitySubmitResult(BaseModel):
    entity: EntityOut
    created: bool
    matches_official_reference: str | None = None
    assessment: "AssessmentOut | None" = None


from app.schemas.detection import AssessmentOut  # noqa: E402

EntitySubmitResult.model_rebuild()


class EntityDetail(EntityOut):
    latest_assessment: AssessmentOut | None = None
    evidence_count: int = 0
    matches_official_reference: str | None = None


class UrlInspectRequest(BaseModel):
    url: str = Field(min_length=4, max_length=2048)

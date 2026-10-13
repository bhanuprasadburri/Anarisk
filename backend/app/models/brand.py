from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_col, uuid_pk
from app.models.enums import Provenance, ReferenceKind, SourceKind
from app.models.user import Organization


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"
    __table_args__ = (UniqueConstraint("organization_id", "slug", name="uq_brands_org_slug"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="brands")
    references: Mapped[list[BrandReference]] = relationship(
        back_populates="brand", cascade="all, delete-orphan", passive_deletes=True
    )


class BrandReference(TimestampMixin, Base):
    """An official brand asset used as ground truth for similarity (name, handle, domain, logo...)."""

    __tablename__ = "brand_references"
    __table_args__ = (
        UniqueConstraint("brand_id", "kind", "normalized_value", name="uq_brand_refs_brand_kind_value"),
        Index("ix_brand_refs_brand_kind", "brand_id", "kind"),
    )
    id: Mapped[uuid.UUID] = uuid_pk()
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[ReferenceKind] = mapped_column(enum_col(ReferenceKind, "reference_kind"), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # display value (text) or perceptual hash (hex)
    normalized_value: Mapped[str] = mapped_column(String(512), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(64))  # e.g. social platform or app store
    perceptual_hash: Mapped[str | None] = mapped_column(String(32))  # image refs
    sha256: Mapped[str | None] = mapped_column(String(64))
    file_path: Mapped[str | None] = mapped_column(String(512))
    note: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[Provenance] = mapped_column(
        enum_col(Provenance, "provenance"), default=Provenance.MANUAL, nullable=False
    )

    brand: Mapped[Brand] = relationship(back_populates="references")


class DataSource(TimestampMixin, Base):
    __tablename__ = "data_sources"
    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[SourceKind] = mapped_column(enum_col(SourceKind, "source_kind"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

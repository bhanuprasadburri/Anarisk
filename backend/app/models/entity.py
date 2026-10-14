from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_col, tz_col, uuid_pk, utcnow
from app.models.brand import Brand, DataSource
from app.models.enums import (
    EntityType, EvidenceKind, Provenance, RelationshipType, Severity, SignalStatus, SignalType,
)


class DigitalEntity(TimestampMixin, Base):
    __tablename__ = "digital_entities"
    __table_args__ = (
        UniqueConstraint("brand_id", "entity_type", "canonical_id", name="uq_entities_brand_type_canonical"),
        Index("ix_entities_brand_type", "brand_id", "entity_type"),
        Index("ix_entities_risk", "current_risk_score"),
        CheckConstraint("current_risk_score IS NULL OR (current_risk_score >= 0 AND current_risk_score <= 1)", name="risk_range"),
    )
    id: Mapped[uuid.UUID] = uuid_pk()
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(enum_col(EntityType, "entity_type"), nullable=False)
    canonical_id: Mapped[str] = mapped_column(String(600), nullable=False)
    display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[Provenance] = mapped_column(enum_col(Provenance, "provenance"), nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    first_seen_at: Mapped[datetime] = tz_col(default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = tz_col(default=utcnow, nullable=False)
    submission_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # Denormalised pointer to the latest assessment (full history is in risk_assessments).
    current_risk_score: Mapped[float | None] = mapped_column(Float)
    current_confidence: Mapped[float | None] = mapped_column(Float)
    current_severity: Mapped[Severity] = mapped_column(
        enum_col(Severity, "severity"), default=Severity.UNKNOWN, nullable=False
    )
    last_assessed_at: Mapped[datetime | None] = tz_col()

    brand: Mapped[Brand] = relationship()
    evidence: Mapped[list[EvidenceRecord]] = relationship(back_populates="entity", cascade="all, delete-orphan")


class CollectionRecord(Base):
    """One row per ingestion event (manual submission or connector run) - preserves raw payloads."""

    __tablename__ = "collection_records"
    id: Mapped[uuid.UUID] = uuid_pk()
    data_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("digital_entities.id", ondelete="CASCADE"), index=True)
    provenance: Mapped[Provenance] = mapped_column(enum_col(Provenance, "provenance"), nullable=False)
    was_new_entity: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    collected_at: Mapped[datetime] = tz_col(default=utcnow, nullable=False)
    submitted_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class EvidenceRecord(TimestampMixin, Base):
    __tablename__ = "evidence_records"
    __table_args__ = (Index("ix_evidence_entity", "entity_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    entity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("digital_entities.id", ondelete="CASCADE"))
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False)
    kind: Mapped[EvidenceKind] = mapped_column(enum_col(EvidenceKind, "evidence_kind"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[Provenance] = mapped_column(enum_col(Provenance, "provenance"), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100))
    file_path: Mapped[str | None] = mapped_column(String(512))
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    perceptual_hash: Mapped[str | None] = mapped_column(String(32))
    text_content: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict, nullable=False)
    collected_at: Mapped[datetime] = tz_col(default=utcnow, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    entity: Mapped[DigitalEntity | None] = relationship(back_populates="evidence")


class RiskAssessment(Base):
    """Immutable historical record of one scoring run. Never updated, only appended."""

    __tablename__ = "risk_assessments"
    __table_args__ = (
        Index("ix_assessments_entity_time", "entity_id", "assessed_at"),
        CheckConstraint("risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 1)", name="risk_range"),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="confidence_range"),
    )
    id: Mapped[uuid.UUID] = uuid_pk()
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("digital_entities.id", ondelete="CASCADE"), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    configured_weights: Mapped[dict[str, Any]] = mapped_column(nullable=False)
    effective_weights: Mapped[dict[str, Any]] = mapped_column(nullable=False)  # renormalised over available signals
    component_scores: Mapped[dict[str, Any]] = mapped_column(nullable=False)  # null for unavailable signals
    risk_score: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_breakdown: Mapped[dict[str, Any]] = mapped_column(nullable=False)
    severity: Mapped[Severity] = mapped_column(enum_col(Severity, "severity"), nullable=False)
    thresholds: Mapped[dict[str, Any]] = mapped_column(nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    assessed_at: Mapped[datetime] = tz_col(default=utcnow, nullable=False)
    triggered_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    signals: Mapped[list[DetectionSignal]] = relationship(back_populates="assessment", order_by="DetectionSignal.signal_type")


class DetectionSignal(Base):
    __tablename__ = "detection_signals"
    __table_args__ = (
        Index("ix_signals_entity", "entity_id"),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 1)", name="score_range"),
        UniqueConstraint("assessment_id", "signal_type", name="uq_signals_assessment_type"),
    )
    id: Mapped[uuid.UUID] = uuid_pk()
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("digital_entities.id", ondelete="CASCADE"), nullable=False)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("risk_assessments.id", ondelete="CASCADE"), nullable=False)
    signal_type: Mapped[SignalType] = mapped_column(enum_col(SignalType, "signal_type"), nullable=False)
    status: Mapped[SignalStatus] = mapped_column(enum_col(SignalStatus, "signal_status"), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict, nullable=False)
    created_at: Mapped[datetime] = tz_col(default=utcnow, nullable=False)

    assessment: Mapped[RiskAssessment] = relationship(back_populates="signals")


class EntityRelationship(Base):
    """Undirected edge of the risk graph. Stored with source_entity_id < target_entity_id (canonical order)."""

    __tablename__ = "entity_relationships"
    __table_args__ = (
        UniqueConstraint("source_entity_id", "target_entity_id", "relationship_type", name="uq_rel_pair_type"),
        CheckConstraint("source_entity_id <> target_entity_id", name="no_self_loop"),
        CheckConstraint("source_entity_id < target_entity_id", name="canonical_order"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        Index("ix_rel_source", "source_entity_id"),
        Index("ix_rel_target", "target_entity_id"),
    )
    id: Mapped[uuid.UUID] = uuid_pk()
    source_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("digital_entities.id", ondelete="CASCADE"), nullable=False)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("digital_entities.id", ondelete="CASCADE"), nullable=False)
    relationship_type: Mapped[RelationshipType] = mapped_column(enum_col(RelationshipType, "relationship_type"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence_records.id", ondelete="SET NULL"))
    evidence_note: Mapped[str] = mapped_column(Text, nullable=False)  # human-readable reference to what links them
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict, nullable=False)
    auto_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = tz_col(default=utcnow, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

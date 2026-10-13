from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import Severity, SignalStatus, SignalType
from app.schemas.common import ORM


class SignalOut(ORM):
    id: uuid.UUID
    entity_id: uuid.UUID
    assessment_id: uuid.UUID
    signal_type: SignalType
    status: SignalStatus
    score: float | None
    explanation: str
    evidence_refs: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(validation_alias="meta")
    created_at: datetime


class AssessmentOut(ORM):
    id: uuid.UUID
    entity_id: uuid.UUID
    model_version: str
    configured_weights: dict[str, float]
    effective_weights: dict[str, float]
    component_scores: dict[str, float | None]
    risk_score: float | None
    confidence_score: float
    confidence_breakdown: dict[str, Any]
    severity: Severity
    thresholds: dict[str, float]
    is_synthetic: bool
    notes: str | None
    assessed_at: datetime
    signals: list[SignalOut] = []


class BulkAnalyzeRequest(BaseModel):
    entity_ids: list[uuid.UUID] | None = Field(None, max_length=200)
    brand_id: uuid.UUID | None = None


class BulkAnalyzeResult(BaseModel):
    analyzed: int
    skipped: list[dict[str, Any]]
    assessments: list[AssessmentOut]


class ModelInfo(BaseModel):
    model_version: str
    weights: dict[str, float]
    severity_thresholds: dict[str, float]
    confidence: dict[str, Any]
    status: str = "heuristic - unvalidated; requires human review"

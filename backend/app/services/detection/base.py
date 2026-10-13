"""Detection contracts. Every detector is independent and returns a SignalResult - never raises for missing data."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.core.config import Settings
from app.models import Brand, BrandReference, DigitalEntity, EvidenceRecord
from app.models.enums import SignalStatus, SignalType


@dataclass
class SignalResult:
    signal_type: SignalType
    status: SignalStatus
    score: float | None  # 0..1, None when status != OK
    explanation: str
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def unavailable(cls, signal_type: SignalType, why: str, **meta) -> "SignalResult":
        return cls(signal_type, SignalStatus.UNAVAILABLE, None, f"Signal unavailable: {why}", [], {"reason": why, **meta})

    @classmethod
    def failed(cls, signal_type: SignalType, err: str) -> "SignalResult":
        return cls(signal_type, SignalStatus.FAILED, None, f"Detector failed: {err}", [], {"error": err})


@dataclass
class DetectionContext:
    entity: DigitalEntity
    brand: Brand
    references: list[BrandReference]
    evidence: list[EvidenceRecord]
    peers: list[DigitalEntity]  # other entities of the same brand (for coordination analysis)
    collection_count: int
    settings: Settings
    now: datetime


class Detector(Protocol):
    signal_type: SignalType

    def run(self, ctx: DetectionContext) -> SignalResult: ...

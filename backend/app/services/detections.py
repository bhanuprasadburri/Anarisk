"""Flattened 'Detections' feed: the LATEST assessment per entity, with the top-weight signal
turned into a plain-English detection type. Human review is always required - the model is
an unvalidated heuristic and the API says so.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models import DetectionSignal, DigitalEntity, RiskAssessment, User
from app.models.enums import EntityType, Provenance, Severity, SignalStatus, SignalType
from app.repositories.access import brand_scope, get_entity_for_user
from app.services import analysis

# Plain-English labels for the four detection families (display order == configured weight order).
SIGNAL_LABELS: dict[SignalType, str] = {
    SignalType.BRAND_LOGO: "Brand & Logo Similarity",
    SignalType.IMPERSONATION: "Identity & Impersonation",
    SignalType.URL_RISK: "URL & Link Risk",
    SignalType.BEHAVIOR: "Behavioural & Coordination Signals",
}


def _weights() -> dict[str, float]:
    return get_settings().weights


def top_signal(assessment: RiskAssessment) -> DetectionSignal | None:
    """Highest-weight signal that actually produced a score; ties broken by score."""
    w = _weights()
    scored = [s for s in assessment.signals if s.status == SignalStatus.OK and s.score is not None]
    if not scored:
        return None
    return max(scored, key=lambda s: (w.get(s.signal_type.value, 0.0), s.score))


def detection_type(assessment: RiskAssessment) -> str:
    top = top_signal(assessment)
    return SIGNAL_LABELS.get(top.signal_type, "Heuristic detection") if top else "Heuristic detection"


def derived_status(assessment: RiskAssessment) -> str:
    """analyzed = every signal ran; partial = some ran; unavailable = none ran."""
    ok = sum(1 for s in assessment.signals if s.status == SignalStatus.OK)
    if not assessment.signals:
        return "unavailable"
    if ok == len(assessment.signals):
        return "analyzed"
    return "partial" if ok else "unavailable"


def _entity_ref(e: DigitalEntity) -> dict:
    return {"id": e.id, "display_name": e.display_name, "entity_type": e.entity_type.value,
            "canonical_id": e.canonical_id, "platform": e.platform, "provenance": e.provenance.value}


def item_dict(a: RiskAssessment, e: DigitalEntity) -> dict:
    top = top_signal(a)
    expl = top.explanation if top else (
        a.notes or "No signal produced a score for this entity; treat as unassessed, not safe.")
    return {
        "id": a.id, "entity": _entity_ref(e), "detection_type": detection_type(a),
        "signal_type": top.signal_type if top else None, "risk_score": a.risk_score,
        "confidence": a.confidence_score, "severity": a.severity, "status": derived_status(a),
        "explanation": expl,
        "signals_summary": [{"signal_type": s.signal_type, "status": s.status, "score": s.score} for s in a.signals],
        "assessed_at": a.assessed_at, "is_synthetic": a.is_synthetic,
    }


def _latest_subquery():
    rn = func.row_number().over(partition_by=RiskAssessment.entity_id,
                                order_by=(RiskAssessment.assessed_at.desc(), RiskAssessment.id.desc())).label("rn")
    return select(RiskAssessment.id.label("assessment_id"), RiskAssessment.entity_id, rn).subquery()


SORTS = {
    "assessed_at": RiskAssessment.assessed_at,
    "risk_score": RiskAssessment.risk_score,
    "confidence": RiskAssessment.confidence_score,
    "severity": case(
        (RiskAssessment.severity == Severity.CRITICAL, 4), (RiskAssessment.severity == Severity.HIGH, 3),
        (RiskAssessment.severity == Severity.MEDIUM, 2), (RiskAssessment.severity == Severity.LOW, 1), else_=0),
}


def list_detections(db: Session, actor: User, *, page: int, page_size: int, q: str | None = None,
                    severity: Severity | None = None, entity_type: EntityType | None = None,
                    brand_id: uuid.UUID | None = None, status: str | None = None,
                    provenance: Provenance | None = None, from_: datetime | None = None, to: datetime | None = None,
                    sort: str = "assessed_at", order: str = "desc"):
    latest = _latest_subquery()
    # signal availability per assessment -> the derived "analyzed | partial | unavailable" status
    sig = select(DetectionSignal.assessment_id,
                 func.count().label("n"),
                 func.count().filter(DetectionSignal.status == SignalStatus.OK).label("n_ok")
                 ).group_by(DetectionSignal.assessment_id).subquery()
    stmt = (select(RiskAssessment, DigitalEntity, func.coalesce(sig.c.n, 0), func.coalesce(sig.c.n_ok, 0))
            .outerjoin(sig, sig.c.assessment_id == RiskAssessment.id)
            .join(latest, (latest.c.assessment_id == RiskAssessment.id) & (latest.c.rn == 1))
            .join(DigitalEntity, DigitalEntity.id == RiskAssessment.entity_id)
            .where(brand_scope(actor, DigitalEntity.brand_id)))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(DigitalEntity.display_name.ilike(like) | DigitalEntity.canonical_id.ilike(like))
    if severity:
        stmt = stmt.where(RiskAssessment.severity == severity)
    if entity_type:
        stmt = stmt.where(DigitalEntity.entity_type == entity_type)
    if brand_id:
        stmt = stmt.where(DigitalEntity.brand_id == brand_id)
    if provenance:
        stmt = stmt.where(DigitalEntity.provenance == provenance)
    if from_:
        stmt = stmt.where(RiskAssessment.assessed_at >= from_)
    if to:
        stmt = stmt.where(RiskAssessment.assessed_at < to)
    if status == "analyzed":
        stmt = stmt.where(func.coalesce(sig.c.n_ok, 0) > 0, sig.c.n_ok == sig.c.n)
    elif status == "partial":
        stmt = stmt.where(func.coalesce(sig.c.n_ok, 0) > 0, sig.c.n_ok < sig.c.n)
    elif status == "unavailable":
        stmt = stmt.where(func.coalesce(sig.c.n_ok, 0) == 0)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    col = SORTS.get(sort, RiskAssessment.assessed_at)
    col = col.desc().nulls_last() if order == "desc" else col.asc().nulls_last()
    rows = db.execute(stmt.options(selectinload(RiskAssessment.signals))
                      .order_by(col, RiskAssessment.id).offset((page - 1) * page_size).limit(page_size)).all()
    return [item_dict(a, e) for a, e, _n, _nok in rows], total


def get_detection(db: Session, actor: User, assessment_id: uuid.UUID) -> RiskAssessment:
    return analysis.get_assessment(db, actor, assessment_id)


def reanalyze(db: Session, actor: User, assessment_id: uuid.UUID) -> tuple[RiskAssessment, str]:
    """Run the rule-based pipeline again for this assessment's entity; a NEW assessment is appended."""
    old = analysis.get_assessment(db, actor, assessment_id)
    entity = get_entity_for_user(db, actor, old.entity_id)
    new = analysis.analyze_entity(db, actor, entity)
    return new, "Rule-based heuristic re-analysis completed. Scores are unvalidated and require human review."

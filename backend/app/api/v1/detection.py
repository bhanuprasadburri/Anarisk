import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Pagination, require_permission
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models import User
from app.models.enums import SignalStatus, SignalType
from app.schemas.common import Page
from app.schemas.detection import AssessmentOut, BulkAnalyzeRequest, BulkAnalyzeResult, ModelInfo, SignalOut
from app.services import analysis

router = APIRouter(prefix="/detection", tags=["Detection & Risk Scoring"])


@router.get("/model", response_model=ModelInfo, summary="Active scoring model: version, weights, thresholds, confidence formula")
def model(_: User = Depends(require_permission("entity:read"))):
    s = get_settings()
    return ModelInfo(model_version=s.scoring_model_version, weights=s.weights,
                     severity_thresholds={"medium": s.severity_medium, "high": s.severity_high, "critical": s.severity_critical},
                     confidence={"weights": {"evidence_quality": s.confidence_w_evidence, "availability": s.confidence_w_availability, "corroboration": s.confidence_w_corroboration},
                                 "provenance_factors": {"collected": s.provenance_factor_collected, "manual": s.provenance_factor_manual, "synthetic": s.provenance_factor_synthetic},
                                 "synthetic_cap": s.synthetic_confidence_cap, "labels": {"medium": s.confidence_medium, "high": s.confidence_high}})


@router.post("/analyze", response_model=BulkAnalyzeResult, dependencies=[Depends(rate_limit("analyze", "analyze_rate_limit_per_minute"))],
             summary="Analyze several entities (by ids) or every entity of a brand (max 200)")
def analyze(body: BulkAnalyzeRequest, user: User = Depends(require_permission("entity:analyze")), db: Session = Depends(get_db)):
    assessments, skipped = analysis.analyze_many(db, user, body.entity_ids, body.brand_id)
    return BulkAnalyzeResult(analyzed=len(assessments), skipped=skipped, assessments=[AssessmentOut.model_validate(a) for a in assessments])


@router.get("/signals", response_model=Page[SignalOut], summary="Signal results (latest assessment per entity unless latest_only=false)")
def signals(p: Pagination = Depends(), entity_id: uuid.UUID | None = None, signal_type: SignalType | None = None, status: SignalStatus | None = None,
            latest_only: bool = True, user: User = Depends(require_permission("entity:read")), db: Session = Depends(get_db)):
    rows, total = analysis.list_signals(db, user, p.page, p.page_size, entity_id, signal_type, status, latest_only)
    return Page.build([SignalOut.model_validate(r) for r in rows], total, p.page, p.page_size)


@router.get("/assessments/{assessment_id}", response_model=AssessmentOut)
def assessment(assessment_id: uuid.UUID, user: User = Depends(require_permission("entity:read")), db: Session = Depends(get_db)):
    return analysis.get_assessment(db, user, assessment_id)

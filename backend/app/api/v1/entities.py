import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, require_permission
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models import EvidenceRecord, User
from app.models.enums import EntityType, Provenance, Severity
from app.repositories import entities as repo
from app.repositories.access import get_entity_for_user
from app.schemas.case import CaseSummary
from app.schemas.common import Page
from app.schemas.detection import AssessmentOut
from app.schemas.entity import CaseRef, EntityDetail, EntityOut, EntitySubmit, EntitySubmitResult, UrlInspectRequest
from app.schemas.evidence import EvidenceOut
from app.services import analysis, cases as cases_svc, ingestion
from app.services.official import is_official_asset
from app.services.url_inspection_service import inspect_entity_url

router = APIRouter(prefix="/entities", tags=["Digital Entities"])


@router.post("", response_model=EntitySubmitResult, status_code=201,
             summary="Submit a profile, website, domain, image or mobile app (manual/synthetic). Duplicates are merged into the existing record.")
def submit(body: EntitySubmit, user: User = Depends(require_permission("entity:submit")), db: Session = Depends(get_db)):
    entity, created, official = ingestion.submit_entity(db, user, body)
    assessment = None
    if body.analyze and not official:
        assessment = analysis.analyze_entity(db, user, entity)
    return EntitySubmitResult(entity=EntityOut.model_validate(entity), created=created, matches_official_reference=official,
                              assessment=AssessmentOut.model_validate(assessment) if assessment else None)


@router.get("", response_model=Page[EntityOut])
def list_entities(p: Pagination = Depends(), brand_id: uuid.UUID | None = None, entity_type: EntityType | None = None,
                  severity: list[Severity] | None = Query(None), min_risk: float | None = Query(None, ge=0, le=1), max_risk: float | None = Query(None, ge=0, le=1),
                  provenance: Provenance | None = None, assessed: bool | None = None, q: str | None = Query(None, max_length=100),
                  sort: str = Query("last_seen_at", pattern="^(risk_score|last_seen_at|first_seen_at|display_name|confidence|created_at)$"),
                  order: str = Query("desc", pattern="^(asc|desc)$"), user: User = Depends(require_permission("entity:read")), db: Session = Depends(get_db)):
    rows, total = repo.list_entities(db, user, page=p.page, page_size=p.page_size, brand_id=brand_id, entity_type=entity_type, severities=severity,
                                     min_risk=min_risk, max_risk=max_risk, provenance=provenance, q=q, assessed=assessed, sort=sort, order=order)
    return Page.build([EntityOut.model_validate(r) for r in rows], total, p.page, p.page_size)


ASSET_METADATA_KEYS = (
    "platform", "handle", "bio", "followers_count", "following_count", "account_created_at", "url", "page_title",
    "domain", "app_name", "package_id", "store", "publisher_name", "store_url", "description", "permissions",
    "permissions_source", "published_at", "phash", "sha256", "hosting", "links", "linked_websites",
)


@router.get("/{entity_id}", response_model=EntityDetail, summary="Entity with latest assessment, related entities, cases, evidence and asset metadata")
def get_entity(entity_id: uuid.UUID, user: User = Depends(require_permission("entity:read")), db: Session = Depends(get_db)):
    e = get_entity_for_user(db, user, entity_id)
    # validate the COLUMN attributes only: the ORM `evidence`/`brand` relationships must not be
    # coerced into the detail schema (they are hydrated explicitly below).
    out = EntityDetail.model_validate({c.key: getattr(e, c.key) for c in inspect(e).mapper.column_attrs})
    la = analysis.latest_assessment(db, e.id)
    out.latest_assessment = AssessmentOut.model_validate(la) if la else None
    out.evidence_count = db.scalar(select(func.count()).select_from(EvidenceRecord).where(EvidenceRecord.entity_id == e.id)) or 0
    out.matches_official_reference = is_official_asset(e, e.brand.references)
    out.related_entities = repo.related_entities(db, user, e.id, limit=12)
    out.cases = [CaseRef(id=c.id, case_number=c.case_number, title=c.title, status=c.status.value, severity=c.severity)
                 for c in cases_svc.cases_for_entity(db, user, e.id)]
    out.evidence = [cases_svc._ev(db, r) for r in db.scalars(
        select(EvidenceRecord).where(EvidenceRecord.entity_id == e.id).order_by(EvidenceRecord.created_at))]
    out.asset_metadata = {k: e.attributes[k] for k in ASSET_METADATA_KEYS if k in (e.attributes or {})}
    return out


@router.delete("/{entity_id}", status_code=204,
               summary="Delete an entity and its evidence (administrators only). Linked cases keep their history")
def delete_entity(entity_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo.delete_entity(db, user, entity_id)


@router.post("/{entity_id}/analyze", response_model=AssessmentOut, status_code=201, dependencies=[Depends(rate_limit("analyze", "analyze_rate_limit_per_minute"))],
             summary="Run the four detection families and persist a new historical risk assessment")
def analyze(entity_id: uuid.UUID, user: User = Depends(require_permission("entity:analyze")), db: Session = Depends(get_db)):
    return analysis.analyze_entity(db, user, get_entity_for_user(db, user, entity_id))


@router.get("/{entity_id}/assessments", response_model=Page[AssessmentOut], summary="Assessment history (newest first)")
def assessments(entity_id: uuid.UUID, p: Pagination = Depends(), user: User = Depends(require_permission("entity:read")), db: Session = Depends(get_db)):
    rows, total = analysis.list_assessments(db, user, entity_id, p.page, p.page_size)
    return Page.build([AssessmentOut.model_validate(r) for r in rows], total, p.page, p.page_size)


@router.get("/{entity_id}/evidence", response_model=list[EvidenceOut])
def entity_evidence(entity_id: uuid.UUID, user: User = Depends(require_permission("evidence:read")), db: Session = Depends(get_db)):
    e = get_entity_for_user(db, user, entity_id)
    rows = db.scalars(select(EvidenceRecord).where(EvidenceRecord.entity_id == e.id).order_by(EvidenceRecord.created_at)).all()
    return [cases_svc._ev(db, r) for r in rows]


@router.get("/{entity_id}/cases", response_model=list[CaseSummary], summary="Cases this entity is part of")
def entity_cases(entity_id: uuid.UUID, user: User = Depends(require_permission("case:read")), db: Session = Depends(get_db)):
    return cases_svc.cases_for_entity(db, user, entity_id)


@router.post("/{entity_id}/inspect-url", response_model=EvidenceOut, status_code=201,
             summary="SSRF-guarded live URL inspection (disabled unless URL_FETCH_ENABLED=true); stores metadata as evidence")
def inspect_url(entity_id: uuid.UUID, body: UrlInspectRequest, user: User = Depends(require_permission("url:inspect")), db: Session = Depends(get_db)):
    return cases_svc._ev(db, inspect_entity_url(db, user, entity_id, body.url))

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models import User
from app.models.enums import EntityType, Severity
from app.schemas.case import CaseDetail
from app.schemas.graph import (
    ClusterCaseRequest, ClusterSummary, DiscoveryResult, GraphResponse, RelatedEntity, RelationshipCreate, RelationshipOut,
)
from app.services import cases as cases_svc, graph as svc

router = APIRouter(prefix="/graph", tags=["Risk Graph"])


def _filters(brand_id, entity_type, min_risk, severity, min_confidence):
    return dict(brand_id=brand_id, entity_types=entity_type, min_risk=min_risk, severities=severity, min_confidence=min_confidence)


@router.get("", response_model=GraphResponse, summary="Nodes and edges, filterable by brand, entity type, risk and edge confidence")
def graph(brand_id: uuid.UUID | None = None, entity_type: list[EntityType] | None = Query(None), min_risk: float | None = Query(None, ge=0, le=1),
          severity: list[Severity] | None = Query(None), min_confidence: float | None = Query(None, ge=0, le=1),
          user: User = Depends(require_permission("graph:read")), db: Session = Depends(get_db)):
    return svc.to_response(svc.build_graph(db, user, **_filters(brand_id, entity_type, min_risk, severity, min_confidence)))


@router.post("/rebuild", response_model=dict, summary="Rebuild the graph from persisted relationships and return its size")
def rebuild(brand_id: uuid.UUID | None = None, user: User = Depends(require_permission("graph:read")), db: Session = Depends(get_db)):
    r = svc.to_response(svc.build_graph(db, user, brand_id=brand_id))
    return {"node_count": r.node_count, "edge_count": r.edge_count, "cluster_count": r.cluster_count, "source": "persisted entity_relationships"}


@router.get("/clusters", response_model=list[ClusterSummary], summary="Connected clusters with evidence-based investigation proposals")
def clusters(brand_id: uuid.UUID | None = None, entity_type: list[EntityType] | None = Query(None), min_risk: float | None = Query(None, ge=0, le=1),
             severity: list[Severity] | None = Query(None), min_confidence: float | None = Query(None, ge=0, le=1), proposed_only: bool = False,
             user: User = Depends(require_permission("graph:read")), db: Session = Depends(get_db)):
    out = svc.list_clusters(db, user, **_filters(brand_id, entity_type, min_risk, severity, min_confidence))
    return [c for c in out if c.propose_for_investigation] if proposed_only else out


@router.post("/clusters/case", response_model=CaseDetail, status_code=201, summary="Open a case from a cluster (human action; never automatic)")
def case_from_cluster(body: ClusterCaseRequest, idempotency_key: str | None = None, user: User = Depends(require_permission("case:create")), db: Session = Depends(get_db)):
    case, _ = cases_svc.create_case_from_cluster(db, user, body.entity_ids, body.title, idempotency_key)
    return cases_svc.case_detail_dict(db, user, case)


@router.get("/entities/{entity_id}/neighbors", response_model=GraphResponse)
def neighbors(entity_id: uuid.UUID, depth: int = Query(1, ge=1, le=3), user: User = Depends(require_permission("graph:read")), db: Session = Depends(get_db)):
    return svc.neighbors(db, user, entity_id, depth)


@router.get("/entities/{entity_id}/related", response_model=list[RelatedEntity], summary="Related entities ranked by strongest-path confidence")
def related(entity_id: uuid.UUID, max_depth: int = Query(3, ge=1, le=5), min_path_confidence: float | None = Query(None, ge=0, le=1),
            user: User = Depends(require_permission("graph:read")), db: Session = Depends(get_db)):
    return svc.related_entities(db, user, entity_id, max_depth, min_path_confidence)


@router.post("/relationships", response_model=RelationshipOut, status_code=201, summary="Record an investigator-asserted relationship (type, confidence, evidence reference)")
def create_rel(body: RelationshipCreate, user: User = Depends(require_permission("graph:write")), db: Session = Depends(get_db)):
    rel, _ = svc.create_relationship(db, user, body)
    return rel


@router.post("/discover", response_model=DiscoveryResult, summary="Derive relationships from observable data for a brand (shared images/domains/identity/infrastructure/posting)")
def discover(brand_id: uuid.UUID, user: User = Depends(require_permission("graph:write")), db: Session = Depends(get_db)):
    return svc.discover_relationships(db, user, brand_id)

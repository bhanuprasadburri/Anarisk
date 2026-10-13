from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import EntityType, RelationshipType, Severity
from app.schemas.common import ORM


class RelationshipCreate(BaseModel):
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: RelationshipType
    confidence: float = Field(ge=0, le=1)
    evidence_id: uuid.UUID | None = None
    evidence_note: str = Field(min_length=3, max_length=2000)


class RelationshipOut(ORM):
    id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: RelationshipType
    confidence: float
    evidence_id: uuid.UUID | None
    evidence_note: str
    metadata: dict[str, Any] = Field(validation_alias="meta")
    auto_generated: bool
    created_at: datetime


class GraphNode(BaseModel):
    id: str
    entity_type: EntityType
    label: str
    brand_id: str
    risk_score: float | None
    confidence: float | None
    severity: Severity
    provenance: str
    cluster_id: str | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: RelationshipType
    confidence: float
    evidence_id: str | None
    evidence_note: str
    created_at: datetime
    auto_generated: bool


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    node_count: int
    edge_count: int
    cluster_count: int


class ClusterSummary(BaseModel):
    cluster_id: str
    size: int
    entity_ids: list[str]
    entity_type_counts: dict[str, int]
    relationship_type_counts: dict[str, int]
    brand_ids: list[str]
    max_risk_score: float | None
    mean_risk_score: float | None
    mean_edge_confidence: float
    max_severity: Severity
    propose_for_investigation: bool
    proposal_reasons: list[str]
    existing_case_ids: list[str]
    headline: str


class RelatedEntity(BaseModel):
    entity: GraphNode
    distance: int
    path_confidence: float
    via: list[str]


class ClusterCaseRequest(BaseModel):
    entity_ids: list[uuid.UUID] = Field(min_length=1, max_length=100, description="One or more entities of the SAME cluster; the whole connected cluster is used")
    title: str | None = Field(None, max_length=300)


class DiscoveryResult(BaseModel):
    pairs_compared: int
    relationships_created: int
    relationships_existing: int

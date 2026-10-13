import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models import User
from app.schemas.entity import EntityOut
from app.services import collection as svc
from app.services.connectors import all_connectors

router = APIRouter(prefix="/collection", tags=["Digital Surface Collection"])


class ConnectorInfo(BaseModel):
    key: str
    name: str
    kind: str
    provenance_of_output: str
    live: bool
    configured: bool
    description: str
    configuration_help: str | None


class RunRequest(BaseModel):
    brand_id: uuid.UUID
    query: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    connector: str
    items: int
    created: int
    entities: list[EntityOut]


@router.get("/connectors", response_model=list[ConnectorInfo], summary="Available source connectors. live=false means NO real external monitoring is happening.")
def connectors(_: User = Depends(require_permission("entity:read"))):
    return [ConnectorInfo(key=c.key, name=c.name, kind=c.kind.value, provenance_of_output=c.provenance.value, live=c.live, configured=c.is_configured(),
                          description=c.description, configuration_help=c.configuration_help()) for c in all_connectors()]


@router.post("/connectors/{key}/run", response_model=RunResult, summary="Run a connector for a brand (409 if not configured)")
def run(key: str, body: RunRequest, user: User = Depends(require_permission("connector:run")), db: Session = Depends(get_db)):
    res = svc.run_connector(db, user, key, body.brand_id, body.query)
    return RunResult(connector=key, items=len(res), created=sum(1 for _, c in res if c), entities=[EntityOut.model_validate(e) for e, _ in res])

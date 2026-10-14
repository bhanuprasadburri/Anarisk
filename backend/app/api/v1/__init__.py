from fastapi import APIRouter

from app.api.v1 import (
    audit, auth, brands, cases, collection, dashboard, detection, entities, evidence, graph, integrations,
    monitoring, notifications, reports, users,
)

api_router = APIRouter()
for module in (
    auth, users, brands, collection, entities, evidence, detection, graph, cases, dashboard, audit,
    notifications, integrations, monitoring, reports,
):
    api_router.include_router(module.router)
    if hasattr(module, "detections_router"):  # /detections feed (module detection)
        api_router.include_router(module.detections_router)

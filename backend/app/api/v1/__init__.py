from fastapi import APIRouter

from app.api.v1 import audit, auth, brands, cases, collection, dashboard, detection, entities, evidence, graph, users

api_router = APIRouter()
for module in (auth, users, brands, collection, entities, evidence, detection, graph, cases, dashboard, audit):
    api_router.include_router(module.router)

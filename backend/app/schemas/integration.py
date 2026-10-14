from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORM

IntegrationCategory = Literal["social", "app_store", "web", "infrastructure"]
FieldType = Literal["text", "url", "secret", "select"]


class ConfigField(BaseModel):
    key: str
    label: str
    type: FieldType
    required: bool = False
    placeholder: str | None = None
    options: list[str] | None = None


class ProviderSpec(BaseModel):
    """Static catalog entry (no stored state)."""

    key: str
    name: str
    category: IntegrationCategory
    description: str
    requires_credentials: bool
    config_fields: list[ConfigField]
    docs_url: str | None = None


class UserBrief(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str


class IntegrationItem(ProviderSpec):
    """Catalog entry merged with the caller's stored configuration. Never contains secret values."""

    status: Literal["not_configured", "configured", "error"] = "not_configured"
    last_sync_at: datetime | None = None
    last_error: str | None = None
    config_preview: dict[str, Any] = Field(default_factory=dict)
    connected_by: UserBrief | None = None


class IntegrationList(BaseModel):
    items: list[IntegrationItem]
    total: int


class ConnectRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class TestResult(BaseModel):
    ok: bool
    message: str
    checked_at: datetime


class SyncRequest(BaseModel):
    brand_id: uuid.UUID | None = None
    query: dict[str, Any] = Field(default_factory=dict)


class SyncResult(BaseModel):
    synced: int
    created_entities: int
    message: str


__all__ = [
    "ConfigField", "ProviderSpec", "IntegrationItem", "IntegrationList", "ConnectRequest", "TestResult",
    "SyncRequest", "SyncResult", "UserBrief", "IntegrationCategory", "FieldType",
]

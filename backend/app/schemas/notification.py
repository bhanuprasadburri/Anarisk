from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORM


class NotificationOut(ORM):
    id: uuid.UUID
    type: str
    title: str
    body: str | None = None
    link_url: str | None = None
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    is_read: bool
    created_at: datetime


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    total: int
    unread_count: int
    page: int
    page_size: int
    pages: int


class MarkReadRequest(BaseModel):
    ids: list[uuid.UUID] | None = Field(None, max_length=500, description="Omit to mark ALL of the caller's notifications read")


class MarkReadResponse(BaseModel):
    updated: int
    unread_count: int

from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: list, total: int, page: int, page_size: int):
        return cls(items=items, total=total, page=page, page_size=page_size, pages=max(1, math.ceil(total / page_size)) if page_size else 1)


class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class Message(BaseModel):
    message: str

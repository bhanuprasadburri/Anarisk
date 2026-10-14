from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Enum, MetaData, TypeDecorator, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map = {dict[str, Any]: JSONB, list[Any]: JSONB, uuid.UUID: Uuid}


def utcnow() -> datetime:
    return datetime.now(UTC)


def enum_col(py_enum: type[enum.Enum], name: str) -> Enum:
    """VARCHAR + CHECK constraint (portable, easy to migrate) storing the enum *values*."""
    return Enum(
        py_enum,
        name=name,
        native_enum=False,
        length=32,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class UTCDateTime(TypeDecorator):
    """TIMESTAMP WITH TIME ZONE that always reads back as UTC.

    psycopg returns timestamptz values in the session's local offset; without this the
    same instant serializes differently depending on whether the row was just written
    (in-memory, UTC) or read back from the database (local offset). Normalizing to UTC
    keeps the API's ISO-8601 output stable ('...Z' everywhere). DDL is unchanged.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            return value.astimezone(UTC)
        return value


def tz_col(**kw):
    return mapped_column(UTCDateTime, **kw)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False
    )

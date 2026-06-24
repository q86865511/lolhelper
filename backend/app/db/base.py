"""SQLAlchemy declarative base."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming convention so Alembic generates stable constraint names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """All ORM models inherit from this."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: dict[type[Any], Any] = {
        datetime: DateTime(timezone=True),
    }


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    """created_at / updated_at convenience mixin."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

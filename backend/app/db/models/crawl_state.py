"""BFS crawler bookkeeping.

Each puuid tracked here has a priority + last_crawled_at. Workers pick the highest
priority + stalest entries via SELECT ... FOR UPDATE SKIP LOCKED.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CrawlState(Base):
    __tablename__ = "crawl_state"

    puuid: Mapped[str] = mapped_column(String(78), primary_key=True)
    region_cluster: Mapped[str] = mapped_column(String(8), nullable=False)
    platform: Mapped[str] = mapped_column(String(8), nullable=False)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    match_cursor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    discovered_by: Mapped[str | None] = mapped_column(String(78), nullable=True)
    depth: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    backoff_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_crawl_state_cluster_priority_stale",
            "region_cluster",
            "priority",
            "last_crawled_at",
            postgresql_where="done = false",
        ),
    )

"""Pre-aggregated stats tables (augment_stats, item_stats).

Recomputed by worker on schedule. Indexed for the common access patterns:
  - list all augments at a patch sorted by Wilson lower bound
  - look up a single augment × champion × patch
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AugmentStat(Base):
    __tablename__ = "augment_stats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    queue_id: Mapped[int] = mapped_column(Integer, nullable=False)
    augment_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # NULL = aggregated across all champions
    champion_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    patch: Mapped[str] = mapped_column(String(8), nullable=False)
    games: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    top1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_placement: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    pick_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    wilson_low: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    tier: Mapped[str | None] = mapped_column(String(1), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "queue_id", "augment_id", "champion_id", "patch",
            name="uq_augment_stats_queue_aug_champ_patch",
        ),
        Index("ix_augment_stats_queue_patch_aug", "queue_id", "patch", "augment_id"),
        Index(
            "ix_augment_stats_queue_patch_champ_wilson",
            "queue_id", "patch", "champion_id", "wilson_low",
        ),
        CheckConstraint("tier IS NULL OR tier IN ('S','A','B','C','D')", name="tier_valid"),
    )


class ItemStat(Base):
    __tablename__ = "item_stats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    queue_id: Mapped[int] = mapped_column(Integer, nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    champion_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    patch: Mapped[str] = mapped_column(String(8), nullable=False)
    # -1 = aggregated across positions; 0..6 = specific build position
    build_position: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=-1)
    games: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    pick_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    wilson_low: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    tier: Mapped[str | None] = mapped_column(String(1), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "queue_id", "item_id", "champion_id", "patch", "build_position",
            name="uq_item_stats_queue_item_champ_patch_pos",
        ),
        Index("ix_item_stats_queue_patch_item", "queue_id", "patch", "item_id"),
        Index(
            "ix_item_stats_queue_patch_champ_wilson",
            "queue_id", "patch", "champion_id", "wilson_low",
        ),
        CheckConstraint("tier IS NULL OR tier IN ('S','A','B','C','D')", name="tier_valid"),
    )

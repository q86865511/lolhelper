"""Match + Participant tables.

Both are partitioned by `game_creation` (monthly) in production. Alembic migration
creates the parent + a few initial partitions; a cron job creates new partitions ahead.

For local dev, partitioning can be disabled by setting the parent to a plain table —
the migration handles both modes via env flag.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

MatchSource = Literal["riot_api", "lcu_upload"]


class Match(Base):
    __tablename__ = "matches"

    match_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    platform: Mapped[str] = mapped_column(String(8), nullable=False)
    queue_id: Mapped[int] = mapped_column(Integer, nullable=False)
    game_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    game_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    patch: Mapped[str | None] = mapped_column(String(8), nullable=True)
    game_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, primary_key=True
    )
    game_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_blob: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_matches_queue_patch_creation", "queue_id", "patch", "game_creation"),
        Index("ix_matches_source_ingested", "source", "ingested_at"),
        # Partitioning directive applied in Alembic migration via execute()
        {"postgresql_partition_by": "RANGE (game_creation)"},
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(20), nullable=False)
    puuid: Mapped[str] = mapped_column(String(78), nullable=False)
    team_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    sub_team_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    placement: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    champion_id: Mapped[int] = mapped_column(Integer, nullable=False)
    champion_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    win: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    kills: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    deaths: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    assists: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    damage_dealt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    damage_taken: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gold_earned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    augments: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    summoner_spell1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summoner_spell2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Denormalised columns to avoid JOIN on hot path
    game_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, primary_key=True
    )
    queue_id: Mapped[int] = mapped_column(Integer, nullable=False)
    patch: Mapped[str | None] = mapped_column(String(8), nullable=True)

    __table_args__ = (
        Index("ix_participants_match", "match_id"),
        Index("ix_participants_puuid_creation", "puuid", "game_creation"),
        Index("ix_participants_queue_champ_patch", "queue_id", "champion_id", "patch"),
        # GIN indexes on arrays — created via raw SQL in migration:
        #   CREATE INDEX ... ON participants USING GIN (augments);
        {"postgresql_partition_by": "RANGE (game_creation)"},
    )

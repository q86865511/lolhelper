"""LoL summoner (puuid is the canonical identifier)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Summoner(Base):
    __tablename__ = "summoners"

    puuid: Mapped[str] = mapped_column(String(78), primary_key=True)
    region: Mapped[str] = mapped_column(String(8), nullable=False)  # KR/NA1/EUW1/...
    platform: Mapped[str] = mapped_column(String(8), nullable=False)
    game_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tag_line: Mapped[str | None] = mapped_column(String(8), nullable=True)
    summoner_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_icon_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    solo_tier: Mapped[str | None] = mapped_column(String(16), nullable=True)
    solo_rank: Mapped[str | None] = mapped_column(String(4), nullable=True)
    solo_lp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    linked_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        Index("ix_summoners_region_game_tag", "region", "game_name", "tag_line"),
        Index("ix_summoners_solo_tier_lp", "solo_tier", "solo_lp"),
    )

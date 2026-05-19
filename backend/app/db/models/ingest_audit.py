"""Audit log of .exe Mayhem uploads."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

IngestStatus = Literal["accepted", "duplicate", "invalid", "rejected"]


class IngestAudit(Base):
    __tablename__ = "ingest_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    puuid: Mapped[str | None] = mapped_column(String(78), nullable=True)
    match_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    client_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_ingest_audit_user_received", "user_id", "received_at"),
        Index("ix_ingest_audit_match", "match_id"),
    )

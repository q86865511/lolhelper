"""extend matches/participants partitions backward and forward

Adds monthly partitions for matches and participants covering 18 months back
through 6 months ahead, so that crawled historical Arena games (which can be
several months old since Arena is a rotating mode) have a home.

Revision ID: 0002_extend_partitions
Revises: 0001_initial
Create Date: 2026-05-18
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op

revision: str = "0002_extend_partitions"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = datetime(year, month, 1, tzinfo=timezone.utc).isoformat()
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc).isoformat()
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc).isoformat()
    return start, end


def _create_partitions(parent: str, months_back: int, months_ahead: int) -> None:
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month
    for offset in range(-months_back, months_ahead + 1):
        m = month + offset
        y = year + (m - 1) // 12
        m_norm = ((m - 1) % 12) + 1
        start, end = _month_bounds(y, m_norm)
        partition_name = f"{parent}_y{y}m{m_norm:02d}"
        op.execute(
            f"CREATE TABLE IF NOT EXISTS {partition_name} "
            f"PARTITION OF {parent} "
            f"FOR VALUES FROM ('{start}') TO ('{end}')"
        )


def upgrade() -> None:
    # 18 months back, 6 months ahead. Total = 25 partitions per table.
    _create_partitions("matches", months_back=18, months_ahead=6)
    _create_partitions("participants", months_back=18, months_ahead=6)


def downgrade() -> None:
    # No-op: dropping partitions could destroy data.
    pass

"""add DEFAULT partitions on matches and participants

Catches any row whose game_creation falls outside our explicit monthly
partitions (e.g. very old Arena matches from prior cycles, or rows that
arrive a month after we forget to add the next partition). Belt and
suspenders against partition-not-found IntegrityError.

Revision ID: 0004_default_partitions
Revises: 0003_unique_nulls_not_distinct
Create Date: 2026-05-18
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0004_default_partitions"
down_revision: Union[str, None] = "0003_unique_nulls_not_distinct"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TABLE IF NOT EXISTS matches_default PARTITION OF matches DEFAULT")
    op.execute(
        "CREATE TABLE IF NOT EXISTS participants_default PARTITION OF participants DEFAULT"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS matches_default")
    op.execute("DROP TABLE IF EXISTS participants_default")

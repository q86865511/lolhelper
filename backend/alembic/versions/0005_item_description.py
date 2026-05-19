"""add description column to items

For tooltips on item hovers. Augments already have a description column from
the initial migration.

Revision ID: 0005_item_description
Revises: 0004_default_partitions
Create Date: 2026-05-18
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_item_description"
down_revision: Union[str, None] = "0004_default_partitions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "description")

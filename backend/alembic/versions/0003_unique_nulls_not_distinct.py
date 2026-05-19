"""make aggregate uniques treat NULL champion_id as equal

augment_stats / item_stats use champion_id=NULL to mean "across all champions".
Postgres UNIQUE constraints default to treating NULL as distinct, so the
upsert ON CONFLICT clause never matches and duplicates accumulate.

Postgres 15+ supports `NULLS NOT DISTINCT` on unique constraints, which is
exactly what we want here.

Revision ID: 0003_unique_nulls_not_distinct
Revises: 0002_extend_partitions
Create Date: 2026-05-18
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0003_unique_nulls_not_distinct"
down_revision: Union[str, None] = "0002_extend_partitions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean out any pre-existing duplicates from earlier aggregations that
    # ran without proper NULL handling. We're at MVP so a wipe is fine; the
    # next aggregate-run repopulates.
    op.execute("TRUNCATE TABLE augment_stats")
    op.execute("TRUNCATE TABLE item_stats")

    # Drop old constraints
    op.execute("ALTER TABLE augment_stats DROP CONSTRAINT uq_augment_stats_queue_aug_champ_patch")
    op.execute("ALTER TABLE item_stats DROP CONSTRAINT uq_item_stats_queue_item_champ_patch_pos")

    # Recreate with NULLS NOT DISTINCT
    op.execute(
        """
        ALTER TABLE augment_stats
        ADD CONSTRAINT uq_augment_stats_queue_aug_champ_patch
        UNIQUE NULLS NOT DISTINCT (queue_id, augment_id, champion_id, patch)
        """
    )
    op.execute(
        """
        ALTER TABLE item_stats
        ADD CONSTRAINT uq_item_stats_queue_item_champ_patch_pos
        UNIQUE NULLS NOT DISTINCT (queue_id, item_id, champion_id, patch, build_position)
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE augment_stats DROP CONSTRAINT uq_augment_stats_queue_aug_champ_patch")
    op.execute("ALTER TABLE item_stats DROP CONSTRAINT uq_item_stats_queue_item_champ_patch_pos")
    op.execute(
        """
        ALTER TABLE augment_stats
        ADD CONSTRAINT uq_augment_stats_queue_aug_champ_patch
        UNIQUE (queue_id, augment_id, champion_id, patch)
        """
    )
    op.execute(
        """
        ALTER TABLE item_stats
        ADD CONSTRAINT uq_item_stats_queue_item_champ_patch_pos
        UNIQUE (queue_id, item_id, champion_id, patch, build_position)
        """
    )

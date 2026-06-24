"""initial schema

Creates all core tables. `matches` and `participants` are partitioned by month on
`game_creation` for easy retention/pruning. The migration also seeds the first
3 monthly partitions; a recurring cron job creates the next month ahead of time.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-18
"""

from __future__ import annotations

from datetime import datetime, timezone, UTC
from typing import Union
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# --- Helpers ---------------------------------------------------------------------

def _month_partition_bounds(year: int, month: int) -> tuple[str, str]:
    start = datetime(year, month, 1, tzinfo=UTC)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(year, month + 1, 1, tzinfo=UTC)
    return start.isoformat(), end.isoformat()


def _create_month_partitions(parent: str, months_ahead: int = 3) -> None:
    """Create N monthly partitions ahead of `now`.

    Run again in a worker cron each month so we always have headroom.
    """
    now = datetime.now(UTC)
    year, month = now.year, now.month
    for offset in range(-1, months_ahead):
        m = month + offset
        y = year + (m - 1) // 12
        m_norm = ((m - 1) % 12) + 1
        start, end = _month_partition_bounds(y, m_norm)
        partition_name = f"{parent}_y{y}m{m_norm:02d}"
        op.execute(
            f"CREATE TABLE IF NOT EXISTS {partition_name} "
            f"PARTITION OF {parent} "
            f"FOR VALUES FROM ('{start}') TO ('{end}')"
        )


# --- Migration -------------------------------------------------------------------

def upgrade() -> None:
    # --- extensions are created by infra/postgres/init.sql; ensure here for prod too ---
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("google_sub", sa.String(64), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("display_name", sa.String(64), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_upload", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    # --- summoners ---
    op.create_table(
        "summoners",
        sa.Column("puuid", sa.String(78), nullable=False),
        sa.Column("region", sa.String(8), nullable=False),
        sa.Column("platform", sa.String(8), nullable=False),
        sa.Column("game_name", sa.String(32), nullable=True),
        sa.Column("tag_line", sa.String(8), nullable=True),
        sa.Column("summoner_level", sa.Integer(), nullable=True),
        sa.Column("profile_icon_id", sa.Integer(), nullable=True),
        sa.Column("solo_tier", sa.String(16), nullable=True),
        sa.Column("solo_rank", sa.String(4), nullable=True),
        sa.Column("solo_lp", sa.Integer(), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("linked_user_id", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("puuid", name="pk_summoners"),
        sa.ForeignKeyConstraint(
            ["linked_user_id"], ["users.id"],
            ondelete="SET NULL", name="fk_summoners_linked_user_id_users",
        ),
    )
    op.create_index("ix_summoners_region_game_tag", "summoners", ["region", "game_name", "tag_line"])
    op.create_index("ix_summoners_solo_tier_lp", "summoners", ["solo_tier", "solo_lp"])
    op.create_index("ix_summoners_linked_user_id", "summoners", ["linked_user_id"])

    # --- matches (partitioned) ---
    op.execute(
        """
        CREATE TABLE matches (
            match_id        VARCHAR(20) NOT NULL,
            platform        VARCHAR(8) NOT NULL,
            queue_id        INTEGER NOT NULL,
            game_mode       VARCHAR(16) NOT NULL,
            game_version    VARCHAR(32),
            patch           VARCHAR(8),
            game_creation   TIMESTAMPTZ NOT NULL,
            game_duration   INTEGER,
            source          VARCHAR(16) NOT NULL,
            ingested_at     TIMESTAMPTZ NOT NULL,
            raw_blob        JSONB,
            PRIMARY KEY (match_id, game_creation)
        ) PARTITION BY RANGE (game_creation)
        """
    )
    op.create_index("ix_matches_queue_patch_creation", "matches", ["queue_id", "patch", "game_creation"])
    op.create_index("ix_matches_source_ingested", "matches", ["source", "ingested_at"])
    _create_month_partitions("matches", months_ahead=3)

    # --- participants (partitioned) ---
    op.execute(
        """
        CREATE TABLE participants (
            id                BIGSERIAL NOT NULL,
            match_id          VARCHAR(20) NOT NULL,
            puuid             VARCHAR(78) NOT NULL,
            team_id           SMALLINT,
            sub_team_id       SMALLINT,
            placement         SMALLINT,
            champion_id       INTEGER NOT NULL,
            champion_name     VARCHAR(32),
            win               BOOLEAN,
            kills             SMALLINT,
            deaths            SMALLINT,
            assists           SMALLINT,
            damage_dealt      INTEGER,
            damage_taken      INTEGER,
            gold_earned       INTEGER,
            items             INTEGER[],
            augments          INTEGER[],
            summoner_spell1   INTEGER,
            summoner_spell2   INTEGER,
            game_creation     TIMESTAMPTZ NOT NULL,
            queue_id          INTEGER NOT NULL,
            patch             VARCHAR(8),
            PRIMARY KEY (id, game_creation)
        ) PARTITION BY RANGE (game_creation)
        """
    )
    op.create_index("ix_participants_match", "participants", ["match_id"])
    op.create_index("ix_participants_puuid_creation", "participants", ["puuid", "game_creation"])
    op.create_index("ix_participants_queue_champ_patch", "participants", ["queue_id", "champion_id", "patch"])
    op.execute("CREATE INDEX ix_participants_augments_gin ON participants USING GIN (augments)")
    op.execute("CREATE INDEX ix_participants_items_gin ON participants USING GIN (items)")
    _create_month_partitions("participants", months_ahead=3)

    # --- augment_stats ---
    op.create_table(
        "augment_stats",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("queue_id", sa.Integer(), nullable=False),
        sa.Column("augment_id", sa.Integer(), nullable=False),
        sa.Column("champion_id", sa.Integer(), nullable=True),
        sa.Column("patch", sa.String(8), nullable=False),
        sa.Column("games", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("top1", sa.Integer(), nullable=True),
        sa.Column("avg_placement", sa.Numeric(4, 2), nullable=True),
        sa.Column("pick_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("win_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("wilson_low", sa.Numeric(6, 4), nullable=False),
        sa.Column("tier", sa.String(1), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_augment_stats"),
        sa.UniqueConstraint(
            "queue_id", "augment_id", "champion_id", "patch",
            name="uq_augment_stats_queue_aug_champ_patch",
        ),
        sa.CheckConstraint("tier IS NULL OR tier IN ('S','A','B','C','D')", name="ck_augment_stats_tier_valid"),
    )
    op.create_index("ix_augment_stats_queue_patch_aug", "augment_stats", ["queue_id", "patch", "augment_id"])
    op.create_index(
        "ix_augment_stats_queue_patch_champ_wilson", "augment_stats",
        ["queue_id", "patch", "champion_id", "wilson_low"],
    )

    # --- item_stats ---
    op.create_table(
        "item_stats",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("queue_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("champion_id", sa.Integer(), nullable=True),
        sa.Column("patch", sa.String(8), nullable=False),
        sa.Column("build_position", sa.SmallInteger(), nullable=False, server_default="-1"),
        sa.Column("games", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("win_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("pick_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("wilson_low", sa.Numeric(6, 4), nullable=False),
        sa.Column("tier", sa.String(1), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_item_stats"),
        sa.UniqueConstraint(
            "queue_id", "item_id", "champion_id", "patch", "build_position",
            name="uq_item_stats_queue_item_champ_patch_pos",
        ),
        sa.CheckConstraint("tier IS NULL OR tier IN ('S','A','B','C','D')", name="ck_item_stats_tier_valid"),
    )
    op.create_index("ix_item_stats_queue_patch_item", "item_stats", ["queue_id", "patch", "item_id"])
    op.create_index(
        "ix_item_stats_queue_patch_champ_wilson", "item_stats",
        ["queue_id", "patch", "champion_id", "wilson_low"],
    )

    # --- crawl_state ---
    op.create_table(
        "crawl_state",
        sa.Column("puuid", sa.String(78), nullable=False),
        sa.Column("region_cluster", sa.String(8), nullable=False),
        sa.Column("platform", sa.String(8), nullable=False),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("match_cursor", sa.String(20), nullable=True),
        sa.Column("discovered_by", sa.String(78), nullable=True),
        sa.Column("depth", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("backoff_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("puuid", name="pk_crawl_state"),
    )
    op.execute(
        "CREATE INDEX ix_crawl_state_cluster_priority_stale "
        "ON crawl_state (region_cluster, priority DESC, last_crawled_at NULLS FIRST) "
        "WHERE done = false"
    )

    # --- ingest_audit ---
    op.create_table(
        "ingest_audit",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("puuid", sa.String(78), nullable=True),
        sa.Column("match_id", sa.String(20), nullable=True),
        sa.Column("client_version", sa.String(16), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ingest_audit"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            ondelete="SET NULL", name="fk_ingest_audit_user_id_users",
        ),
    )
    op.create_index("ix_ingest_audit_user_received", "ingest_audit", ["user_id", "received_at"])
    op.create_index("ix_ingest_audit_match", "ingest_audit", ["match_id"])

    # --- metadata tables ---
    op.create_table(
        "augments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("rarity", sa.SmallInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_path", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_augments"),
    )

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("gold", sa.Integer(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("icon_path", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_items"),
    )

    op.create_table(
        "champions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(32), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("icon_path", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_champions"),
        sa.UniqueConstraint("key", name="uq_champions_key"),
    )

    op.create_table(
        "patches",
        sa.Column("version", sa.String(8), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("version", name="pk_patches"),
    )


def downgrade() -> None:
    op.drop_table("patches")
    op.drop_table("champions")
    op.drop_table("items")
    op.drop_table("augments")
    op.drop_index("ix_ingest_audit_match", table_name="ingest_audit")
    op.drop_index("ix_ingest_audit_user_received", table_name="ingest_audit")
    op.drop_table("ingest_audit")
    op.execute("DROP INDEX IF EXISTS ix_crawl_state_cluster_priority_stale")
    op.drop_table("crawl_state")
    op.drop_table("item_stats")
    op.drop_table("augment_stats")
    op.execute("DROP TABLE IF EXISTS participants CASCADE")
    op.execute("DROP TABLE IF EXISTS matches CASCADE")
    op.drop_table("summoners")
    op.drop_table("users")

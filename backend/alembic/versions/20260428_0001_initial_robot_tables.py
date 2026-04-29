"""initial robot tables

Revision ID: 20260428_0001
Revises:
Create Date: 2026-04-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260428_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "robots",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("robot_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="idle", nullable=False),
        sa.Column("battery_level", sa.Integer(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("battery_level IS NULL OR (battery_level >= 0 AND battery_level <= 100)", name="ck_robots_battery_level"),
        sa.CheckConstraint("status IN ('idle', 'running')", name="ck_robots_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("robot_id"),
    )
    op.create_index("ix_robots_last_seen_at", "robots", ["last_seen_at"], unique=False)
    op.create_index("ix_robots_status", "robots", ["status"], unique=False)

    op.create_table(
        "robot_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("robot_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('heartbeat', 'status_update', 'offline_detected', 'command_result')",
            name="ck_robot_events_event_type",
        ),
        sa.ForeignKeyConstraint(["robot_id"], ["robots.robot_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_robot_events_created_at", "robot_events", ["created_at"], unique=False)
    op.create_index("ix_robot_events_robot_created_at", "robot_events", ["robot_id", "created_at"], unique=False)
    op.create_index("ix_robot_events_robot_id", "robot_events", ["robot_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_robot_events_robot_id", table_name="robot_events")
    op.drop_index("ix_robot_events_robot_created_at", table_name="robot_events")
    op.drop_index("ix_robot_events_created_at", table_name="robot_events")
    op.drop_table("robot_events")

    op.drop_index("ix_robots_status", table_name="robots")
    op.drop_index("ix_robots_last_seen_at", table_name="robots")
    op.drop_table("robots")

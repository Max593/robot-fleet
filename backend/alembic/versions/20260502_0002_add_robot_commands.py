"""add robot commands

Revision ID: 20260502_0002
Revises: 20260428_0001
Create Date: 2026-05-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260502_0002"
down_revision: str | None = "20260428_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "robot_commands",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("robot_id", sa.String(length=64), nullable=False),
        sa.Column("command_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "command_type IN ('run_diagnostic', 'pause_for', 'pause_until_resumed', 'resume', 'return_to_base')",
            name="ck_robot_commands_command_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'claimed', 'completed', 'failed', 'expired', 'cancelled')",
            name="ck_robot_commands_status",
        ),
        sa.ForeignKeyConstraint(["robot_id"], ["robots.robot_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_robot_commands_created_at", "robot_commands", ["created_at"], unique=False)
    op.create_index("ix_robot_commands_robot_id", "robot_commands", ["robot_id"], unique=False)
    op.create_index(
        "ix_robot_commands_robot_status_created_at",
        "robot_commands",
        ["robot_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_robot_commands_status_created_at",
        "robot_commands",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_robot_commands_status_created_at", table_name="robot_commands")
    op.drop_index("ix_robot_commands_robot_status_created_at", table_name="robot_commands")
    op.drop_index("ix_robot_commands_robot_id", table_name="robot_commands")
    op.drop_index("ix_robot_commands_created_at", table_name="robot_commands")
    op.drop_table("robot_commands")

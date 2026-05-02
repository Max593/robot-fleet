"""add robot command history index

Revision ID: 20260503_0004
Revises: 20260502_0003
Create Date: 2026-05-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260503_0004"
down_revision: str | None = "20260502_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_robot_commands_robot_created_at",
        "robot_commands",
        ["robot_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_robot_commands_robot_created_at", table_name="robot_commands")

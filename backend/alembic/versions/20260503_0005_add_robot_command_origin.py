"""add robot command origin

Revision ID: 20260503_0005
Revises: 20260503_0004
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260503_0005"
down_revision: str | None = "20260503_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "robot_commands",
        sa.Column("origin", sa.String(length=32), server_default="operator", nullable=False),
    )
    op.create_check_constraint(
        "ck_robot_commands_origin",
        "robot_commands",
        "origin IN ('operator', 'system')",
    )
    op.create_index(
        "ix_robot_commands_robot_origin_type_status",
        "robot_commands",
        ["robot_id", "origin", "command_type", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_robot_commands_robot_origin_type_status", table_name="robot_commands")
    op.drop_constraint("ck_robot_commands_origin", "robot_commands", type_="check")
    op.drop_column("robot_commands", "origin")

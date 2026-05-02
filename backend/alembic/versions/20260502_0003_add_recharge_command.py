"""add recharge command

Revision ID: 20260502_0003
Revises: 20260502_0002
Create Date: 2026-05-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260502_0003"
down_revision: str | None = "20260502_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_COMMAND_TYPES = "'run_diagnostic', 'pause_for', 'pause_until_resumed', 'resume', 'return_to_base'"
NEW_COMMAND_TYPES = f"{OLD_COMMAND_TYPES}, 'recharge_to_full'"


def upgrade() -> None:
    op.drop_constraint("ck_robot_commands_command_type", "robot_commands", type_="check")
    op.create_check_constraint(
        "ck_robot_commands_command_type",
        "robot_commands",
        f"command_type IN ({NEW_COMMAND_TYPES})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_robot_commands_command_type", "robot_commands", type_="check")
    op.create_check_constraint(
        "ck_robot_commands_command_type",
        "robot_commands",
        f"command_type IN ({OLD_COMMAND_TYPES})",
    )

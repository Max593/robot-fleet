"""Add robot lifecycle states and executing command lifecycle.

Revision ID: 20260503_0006
Revises: 20260503_0005
Create Date: 2026-05-03 00:06:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260503_0006"
down_revision: str | None = "20260503_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_robots_status", "robots", type_="check")
    op.create_check_constraint("ck_robots_status", "robots", "status IN ('idle', 'running', 'paused', 'charging')")

    op.drop_constraint("ck_robot_commands_status", "robot_commands", type_="check")
    op.create_check_constraint(
        "ck_robot_commands_status",
        "robot_commands",
        "status IN ('pending', 'claimed', 'executing', 'completed', 'failed', 'expired', 'cancelled')",
    )

    op.drop_constraint("ck_robot_events_event_type", "robot_events", type_="check")
    op.create_check_constraint(
        "ck_robot_events_event_type",
        "robot_events",
        "event_type IN ('heartbeat', 'status_update', 'offline_detected', 'command_lifecycle', 'command_result')",
    )


def downgrade() -> None:
    op.execute("UPDATE robots SET status = 'idle' WHERE status IN ('paused', 'charging')")
    op.execute("UPDATE robot_commands SET status = 'claimed' WHERE status = 'executing'")

    op.drop_constraint("ck_robot_events_event_type", "robot_events", type_="check")
    op.create_check_constraint(
        "ck_robot_events_event_type",
        "robot_events",
        "event_type IN ('heartbeat', 'status_update', 'offline_detected', 'command_result')",
    )

    op.drop_constraint("ck_robot_commands_status", "robot_commands", type_="check")
    op.create_check_constraint(
        "ck_robot_commands_status",
        "robot_commands",
        "status IN ('pending', 'claimed', 'completed', 'failed', 'expired', 'cancelled')",
    )

    op.drop_constraint("ck_robots_status", "robots", type_="check")
    op.create_check_constraint("ck_robots_status", "robots", "status IN ('idle', 'running')")

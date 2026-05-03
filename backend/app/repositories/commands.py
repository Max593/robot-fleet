from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.robot import RobotCommand
from app.schemas.command import RobotCommandOrigin, RobotCommandStatus, RobotCommandType


class RobotCommandRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_command(
        self,
        robot_id: str,
        command_type: RobotCommandType,
        payload: dict[str, Any],
        origin: RobotCommandOrigin,
        expires_at: datetime | None,
    ) -> RobotCommand:
        command = RobotCommand(
            robot_id=robot_id,
            command_type=command_type.value,
            origin=origin.value,
            payload=payload,
            expires_at=expires_at,
        )
        self.db.add(command)
        self.db.flush()
        self.db.refresh(command)
        return command

    def get_pending_system_recharge_command(self, robot_id: str) -> RobotCommand | None:
        stmt = (
            select(RobotCommand)
            .where(
                RobotCommand.robot_id == robot_id,
                RobotCommand.origin == RobotCommandOrigin.SYSTEM.value,
                RobotCommand.command_type == RobotCommandType.RECHARGE_TO_FULL.value,
                RobotCommand.status == RobotCommandStatus.PENDING.value,
            )
            .order_by(RobotCommand.created_at, RobotCommand.id)
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_commands(self, robot_id: str, limit: int, now: datetime) -> list[RobotCommand]:
        self.expire_pending_commands(now)
        stmt = (
            select(RobotCommand)
            .where(RobotCommand.robot_id == robot_id)
            .order_by(RobotCommand.created_at.desc(), RobotCommand.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_commands(self, robot_id: str, now: datetime) -> int:
        self.expire_pending_commands(now)
        stmt = select(func.count(RobotCommand.id)).where(RobotCommand.robot_id == robot_id)
        return int(self.db.execute(stmt).scalar_one())

    def list_commands_page(self, robot_id: str, page: int, page_size: int, now: datetime) -> list[RobotCommand]:
        self.expire_pending_commands(now)
        offset = (page - 1) * page_size
        stmt = (
            select(RobotCommand)
            .where(RobotCommand.robot_id == robot_id)
            .order_by(RobotCommand.created_at.desc(), RobotCommand.id.desc())
            .limit(page_size)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def claim_next_command(self, robot_id: str, claimed_at: datetime) -> RobotCommand | None:
        self.expire_pending_commands(claimed_at)
        stmt = (
            select(RobotCommand)
            .where(
                RobotCommand.robot_id == robot_id,
                RobotCommand.status == RobotCommandStatus.PENDING.value,
                or_(RobotCommand.expires_at.is_(None), RobotCommand.expires_at > claimed_at),
            )
            .order_by(RobotCommand.created_at, RobotCommand.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        command = self.db.execute(stmt).scalar_one_or_none()
        if command is None:
            return None

        command.status = RobotCommandStatus.CLAIMED.value
        command.claimed_at = claimed_at
        self.db.flush()
        self.db.refresh(command)
        return command

    def expire_pending_commands(self, now: datetime) -> int:
        stmt = (
            select(RobotCommand)
            .where(
                RobotCommand.status == RobotCommandStatus.PENDING.value,
                RobotCommand.expires_at.is_not(None),
                RobotCommand.expires_at <= now,
            )
            .with_for_update(skip_locked=True)
        )
        expired_commands = list(self.db.execute(stmt).scalars().all())
        for command in expired_commands:
            command.status = RobotCommandStatus.EXPIRED.value
            command.completed_at = now
            command.error_message = "Command expired before the robot claimed it."

        if expired_commands:
            self.db.flush()

        return len(expired_commands)

    def complete_command(
        self,
        robot_id: str,
        command_id: int,
        completed_at: datetime,
        status: RobotCommandStatus,
        result: dict[str, Any],
        error_message: str | None,
    ) -> RobotCommand | None:
        stmt = select(RobotCommand).where(RobotCommand.id == command_id, RobotCommand.robot_id == robot_id)
        command = self.db.execute(stmt).scalar_one_or_none()
        if command is None:
            return None

        command.status = status.value
        command.result = result
        command.error_message = error_message
        command.completed_at = completed_at
        self.db.flush()
        self.db.refresh(command)
        return command

    def delete_terminal_commands_older_than(self, cutoff: datetime) -> int:
        terminal_statuses = (
            RobotCommandStatus.COMPLETED.value,
            RobotCommandStatus.FAILED.value,
            RobotCommandStatus.EXPIRED.value,
            RobotCommandStatus.CANCELLED.value,
        )
        stmt = delete(RobotCommand).where(
            RobotCommand.status.in_(terminal_statuses),
            func.coalesce(RobotCommand.completed_at, RobotCommand.created_at) < cutoff,
        )
        result = self.db.execute(stmt)
        return int(result.rowcount or 0)

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.robot import Robot, RobotCommand, RobotEvent
from app.schemas.robot import RobotCommandStatus, RobotCommandType, RobotStatusFilter


@dataclass(frozen=True)
class RobotStatusQuery:
    page: int
    page_size: int
    search: str | None
    status_filter: RobotStatusFilter
    offline_cutoff: datetime


@dataclass(frozen=True)
class RobotFleetCounts:
    total: int
    online: int
    offline: int
    running: int
    idle: int


class RobotRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_ping(self, robot_id: str, seen_at: datetime) -> None:
        stmt = (
            insert(Robot)
            .values(robot_id=robot_id, status="idle", last_seen_at=seen_at, updated_at=seen_at)
            .on_conflict_do_update(
                index_elements=[Robot.robot_id],
                set_={"last_seen_at": seen_at, "updated_at": seen_at},
            )
        )
        self.db.execute(stmt)

    def upsert_update(self, robot_id: str, payload: dict[str, Any], seen_at: datetime) -> None:
        insert_values = {
            "robot_id": robot_id,
            "status": payload.get("status", "idle"),
            "battery_level": payload.get("battery_level"),
            "last_seen_at": seen_at,
            "updated_at": seen_at,
        }
        update_values = {"last_seen_at": seen_at, "updated_at": seen_at, **payload}

        stmt = (
            insert(Robot)
            .values(**insert_values)
            .on_conflict_do_update(index_elements=[Robot.robot_id], set_=update_values)
        )
        self.db.execute(stmt)

    def add_event(self, robot_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.db.add(RobotEvent(robot_id=robot_id, event_type=event_type, payload=payload))

    def get_robot(self, robot_id: str) -> Robot | None:
        stmt = select(Robot).where(Robot.robot_id == robot_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create_command(
        self,
        robot_id: str,
        command_type: RobotCommandType,
        payload: dict[str, Any],
        expires_at: datetime,
    ) -> RobotCommand:
        command = RobotCommand(
            robot_id=robot_id,
            command_type=command_type.value,
            payload=payload,
            expires_at=expires_at,
        )
        self.db.add(command)
        self.db.flush()
        self.db.refresh(command)
        return command

    def list_commands(self, robot_id: str, limit: int, now: datetime) -> list[RobotCommand]:
        self.expire_pending_commands(now)
        stmt = (
            select(RobotCommand)
            .where(RobotCommand.robot_id == robot_id)
            .order_by(RobotCommand.created_at.desc(), RobotCommand.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def claim_next_command(self, robot_id: str, claimed_at: datetime) -> RobotCommand | None:
        self.expire_pending_commands(claimed_at)
        stmt = (
            select(RobotCommand)
            .where(
                RobotCommand.robot_id == robot_id,
                RobotCommand.status == RobotCommandStatus.PENDING.value,
                RobotCommand.expires_at > claimed_at,
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

    def delete_events_older_than(self, cutoff: datetime) -> int:
        result = self.db.execute(delete(RobotEvent).where(RobotEvent.created_at < cutoff))
        return int(result.rowcount or 0)

    def count_status_page(self, query: RobotStatusQuery) -> int:
        conditions = _status_page_conditions(query)
        stmt = select(func.count(Robot.id)).select_from(Robot)
        if conditions:
            stmt = stmt.where(*conditions)
        return int(self.db.execute(stmt).scalar_one())

    def list_status_page(self, query: RobotStatusQuery) -> list[Robot]:
        conditions = _status_page_conditions(query)
        offset = (query.page - 1) * query.page_size

        stmt = select(Robot).order_by(Robot.robot_id).limit(query.page_size).offset(offset)
        if conditions:
            stmt = stmt.where(*conditions)

        return list(self.db.execute(stmt).scalars().all())

    def get_fleet_counts(self, offline_cutoff: datetime) -> RobotFleetCounts:
        online_condition = _online_condition(offline_cutoff)
        offline_condition = _offline_condition(offline_cutoff)
        running_condition = and_(online_condition, Robot.status == "running")
        idle_condition = and_(online_condition, Robot.status == "idle")

        stmt = select(
            func.count(Robot.id),
            func.count(Robot.id).filter(online_condition),
            func.count(Robot.id).filter(offline_condition),
            func.count(Robot.id).filter(running_condition),
            func.count(Robot.id).filter(idle_condition),
        )
        total, online, offline, running, idle = self.db.execute(stmt).one()
        return RobotFleetCounts(
            total=int(total),
            online=int(online),
            offline=int(offline),
            running=int(running),
            idle=int(idle),
        )


def _status_page_conditions(query: RobotStatusQuery) -> list[Any]:
    conditions: list[Any] = []
    normalized_search = query.search.strip() if query.search else ""

    if normalized_search:
        conditions.append(Robot.robot_id.ilike(f"%{normalized_search}%"))

    if query.status_filter == RobotStatusFilter.ONLINE:
        conditions.append(_online_condition(query.offline_cutoff))
    elif query.status_filter == RobotStatusFilter.OFFLINE:
        conditions.append(_offline_condition(query.offline_cutoff))
    elif query.status_filter == RobotStatusFilter.RUNNING:
        conditions.append(and_(_online_condition(query.offline_cutoff), Robot.status == "running"))
    elif query.status_filter == RobotStatusFilter.IDLE:
        conditions.append(and_(_online_condition(query.offline_cutoff), Robot.status == "idle"))

    return conditions


def _online_condition(offline_cutoff: datetime) -> Any:
    return Robot.last_seen_at >= offline_cutoff


def _offline_condition(offline_cutoff: datetime) -> Any:
    return or_(Robot.last_seen_at.is_(None), Robot.last_seen_at < offline_cutoff)

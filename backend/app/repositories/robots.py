from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.robot import Robot
from app.schemas.robot import RobotStatusFilter


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
    paused: int
    charging: int


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

    def get_robot(self, robot_id: str) -> Robot | None:
        stmt = select(Robot).where(Robot.robot_id == robot_id)
        return self.db.execute(stmt).scalar_one_or_none()

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
        paused_condition = and_(online_condition, Robot.status == "paused")
        charging_condition = and_(online_condition, Robot.status == "charging")

        stmt = select(
            func.count(Robot.id),
            func.count(Robot.id).filter(online_condition),
            func.count(Robot.id).filter(offline_condition),
            func.count(Robot.id).filter(running_condition),
            func.count(Robot.id).filter(idle_condition),
            func.count(Robot.id).filter(paused_condition),
            func.count(Robot.id).filter(charging_condition),
        )
        total, online, offline, running, idle, paused, charging = self.db.execute(stmt).one()
        return RobotFleetCounts(
            total=int(total),
            online=int(online),
            offline=int(offline),
            running=int(running),
            idle=int(idle),
            paused=int(paused),
            charging=int(charging),
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
    elif query.status_filter == RobotStatusFilter.PAUSED:
        conditions.append(and_(_online_condition(query.offline_cutoff), Robot.status == "paused"))
    elif query.status_filter == RobotStatusFilter.CHARGING:
        conditions.append(and_(_online_condition(query.offline_cutoff), Robot.status == "charging"))

    return conditions


def _online_condition(offline_cutoff: datetime) -> Any:
    return Robot.last_seen_at >= offline_cutoff


def _offline_condition(offline_cutoff: datetime) -> Any:
    return or_(Robot.last_seen_at.is_(None), Robot.last_seen_at < offline_cutoff)

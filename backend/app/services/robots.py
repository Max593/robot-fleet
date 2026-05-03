from datetime import UTC, datetime, timedelta
from math import ceil
from typing import cast

from sqlalchemy.orm import Session

from app.models.robot import Robot
from app.repositories.robots import RobotRepository, RobotStatusQuery
from app.schemas.robot import (
    RobotFleetSummary,
    RobotState,
    RobotStatusFilter,
    RobotStatusListResponse,
    RobotStatusPagination,
    RobotStatusResponse,
    RobotUpdateRequest,
)


def get_robot_status(db: Session, robot_id: str, offline_after_seconds: int) -> RobotStatusResponse | None:
    robot = RobotRepository(db).get_robot(robot_id)
    if robot is None:
        return None
    return _to_status_response(robot, datetime.now(UTC), offline_after_seconds)


def record_ping(db: Session, robot_id: str) -> None:
    now = datetime.now(UTC)
    repository = RobotRepository(db)

    repository.upsert_ping(robot_id, seen_at=now)
    db.commit()


def record_update(db: Session, robot_id: str, update: RobotUpdateRequest) -> None:
    now = datetime.now(UTC)
    payload = update.model_dump(exclude_none=True)
    repository = RobotRepository(db)

    repository.upsert_update(robot_id, payload=payload, seen_at=now)
    db.commit()


def list_robot_status_page(
    db: Session,
    offline_after_seconds: int,
    page: int,
    page_size: int,
    search: str | None,
    status_filter: RobotStatusFilter,
) -> RobotStatusListResponse:
    now = datetime.now(UTC)
    offline_cutoff = now - timedelta(seconds=offline_after_seconds)
    repository = RobotRepository(db)

    initial_query = RobotStatusQuery(
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
        offline_cutoff=offline_cutoff,
    )
    total = repository.count_status_page(initial_query)
    total_pages = max(1, ceil(total / page_size))
    clamped_page = min(page, total_pages)

    query = RobotStatusQuery(
        page=clamped_page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
        offline_cutoff=offline_cutoff,
    )
    robots = repository.list_status_page(query)
    fleet_counts = repository.get_fleet_counts(offline_cutoff)

    return RobotStatusListResponse(
        robots=[_to_status_response(robot, now, offline_after_seconds) for robot in robots],
        pagination=RobotStatusPagination(
            total=total,
            page=clamped_page,
            page_size=page_size,
            total_pages=total_pages,
        ),
        summary=RobotFleetSummary(
            total=fleet_counts.total,
            online=fleet_counts.online,
            offline=fleet_counts.offline,
            running=fleet_counts.running,
            idle=fleet_counts.idle,
            paused=fleet_counts.paused,
            charging=fleet_counts.charging,
        ),
    )


def _to_status_response(robot: Robot, now: datetime, offline_after_seconds: int) -> RobotStatusResponse:
    if robot.last_seen_at is None:
        last_seen_seconds_ago = None
        is_online = False
    else:
        last_seen_at = _ensure_aware(robot.last_seen_at)
        elapsed_seconds = max(0.0, (now - last_seen_at).total_seconds())
        last_seen_seconds_ago = 0 if elapsed_seconds < 1 else ceil(elapsed_seconds)
        is_online = elapsed_seconds <= offline_after_seconds

    return RobotStatusResponse(
        robot_id=robot.robot_id,
        status=cast(RobotState, robot.status),
        battery_level=robot.battery_level,
        last_seen_at=_ensure_aware(robot.last_seen_at) if robot.last_seen_at else None,
        last_seen_seconds_ago=last_seen_seconds_ago,
        is_online=is_online,
    )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value

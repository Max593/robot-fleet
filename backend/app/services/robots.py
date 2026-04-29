from datetime import UTC, datetime
from typing import cast

from sqlalchemy.orm import Session

from app.models.robot import Robot
from app.repositories.robots import RobotRepository
from app.schemas.robot import RobotState, RobotStatusResponse, RobotUpdateRequest


def record_ping(db: Session, robot_id: str) -> None:
    now = datetime.now(UTC)
    repository = RobotRepository(db)

    repository.upsert_ping(robot_id, seen_at=now)
    repository.add_event(robot_id, event_type="heartbeat", payload={})
    db.commit()


def record_update(db: Session, robot_id: str, update: RobotUpdateRequest) -> None:
    now = datetime.now(UTC)
    payload = update.model_dump(exclude_none=True)
    repository = RobotRepository(db)

    repository.upsert_update(robot_id, payload=payload, seen_at=now)
    repository.add_event(robot_id, event_type="status_update", payload=payload)
    db.commit()


def list_robot_statuses(db: Session, offline_after_seconds: int) -> list[RobotStatusResponse]:
    now = datetime.now(UTC)
    robots = RobotRepository(db).list_all()
    return [_to_status_response(robot, now, offline_after_seconds) for robot in robots]


def _to_status_response(robot: Robot, now: datetime, offline_after_seconds: int) -> RobotStatusResponse:
    if robot.last_seen_at is None:
        last_seen_seconds_ago = None
        is_online = False
    else:
        last_seen_at = _ensure_aware(robot.last_seen_at)
        last_seen_seconds_ago = max(0, int((now - last_seen_at).total_seconds()))
        is_online = last_seen_seconds_ago <= offline_after_seconds

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

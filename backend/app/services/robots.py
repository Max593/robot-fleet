from datetime import UTC, datetime, timedelta
from math import ceil
from typing import cast

from sqlalchemy.orm import Session

from app.models.robot import Robot, RobotCommand
from app.repositories.robots import RobotRepository, RobotStatusQuery
from app.schemas.robot import (
    RobotCommandCompleteRequest,
    RobotCommandCreateRequest,
    RobotCommandNextResponse,
    RobotCommandResponse,
    RobotCommandStatus,
    RobotCommandType,
    RobotFleetSummary,
    RobotState,
    RobotStatusFilter,
    RobotStatusListResponse,
    RobotStatusPagination,
    RobotStatusResponse,
    RobotUpdateRequest,
)


def create_robot_command(
    db: Session,
    robot_id: str,
    request: RobotCommandCreateRequest,
    expiration_seconds: int,
) -> RobotCommandResponse | None:
    now = datetime.now(UTC)
    repository = RobotRepository(db)
    if repository.get_robot(robot_id) is None:
        return None

    command = repository.create_command(
        robot_id=robot_id,
        command_type=request.command_type,
        payload=request.payload,
        expires_at=now + timedelta(seconds=expiration_seconds),
    )
    db.commit()
    return _to_command_response(command)


def claim_next_robot_command(db: Session, robot_id: str) -> RobotCommandNextResponse:
    now = datetime.now(UTC)
    repository = RobotRepository(db)
    command = repository.claim_next_command(robot_id, claimed_at=now)
    db.commit()

    return RobotCommandNextResponse(command=_to_command_response(command) if command else None)


def complete_robot_command(
    db: Session,
    robot_id: str,
    command_id: int,
    request: RobotCommandCompleteRequest,
) -> RobotCommandResponse | None:
    now = datetime.now(UTC)
    repository = RobotRepository(db)
    command_status = RobotCommandStatus.COMPLETED if request.success else RobotCommandStatus.FAILED
    command = repository.complete_command(
        robot_id=robot_id,
        command_id=command_id,
        completed_at=now,
        status=command_status,
        result=request.result,
        error_message=request.error_message,
    )
    if command is None:
        db.rollback()
        return None

    repository.add_event(
        robot_id,
        event_type="command_result",
        payload={
            "command_id": command_id,
            "status": command_status.value,
            "result": request.result,
            "error_message": request.error_message,
        },
    )
    db.commit()
    return _to_command_response(command)


def list_robot_commands(db: Session, robot_id: str, limit: int) -> list[RobotCommandResponse]:
    repository = RobotRepository(db)
    commands = repository.list_commands(robot_id, limit=limit, now=datetime.now(UTC))
    db.commit()
    return [_to_command_response(command) for command in commands]


def cleanup_old_robot_commands(db: Session, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    deleted_count = RobotRepository(db).delete_terminal_commands_older_than(cutoff)
    db.commit()
    return deleted_count


def cleanup_old_robot_events(db: Session, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    deleted_count = RobotRepository(db).delete_events_older_than(cutoff)
    db.commit()
    return deleted_count


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


def _to_command_response(command: RobotCommand) -> RobotCommandResponse:
    return RobotCommandResponse(
        id=command.id,
        robot_id=command.robot_id,
        command_type=RobotCommandType(command.command_type),
        payload=command.payload,
        status=RobotCommandStatus(command.status),
        result=command.result,
        error_message=command.error_message,
        created_at=_ensure_aware(command.created_at),
        claimed_at=_ensure_aware(command.claimed_at) if command.claimed_at else None,
        completed_at=_ensure_aware(command.completed_at) if command.completed_at else None,
        expires_at=_ensure_aware(command.expires_at) if command.expires_at else None,
    )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value

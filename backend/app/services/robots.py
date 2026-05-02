import logging
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import cast

from sqlalchemy.orm import Session

from app.models.robot import Robot, RobotCommand, RobotEvent
from app.repositories.robots import RobotRepository, RobotStatusQuery
from app.schemas.robot import (
    RobotBatteryRecoveryRequest,
    RobotCommandCompleteRequest,
    RobotCommandCreateRequest,
    RobotCommandListResponse,
    RobotCommandNextResponse,
    RobotCommandOrigin,
    RobotCommandResponse,
    RobotCommandStatus,
    RobotCommandType,
    RobotEventListResponse,
    RobotEventResponse,
    RobotFleetSummary,
    RobotState,
    RobotStatusFilter,
    RobotStatusListResponse,
    RobotStatusPagination,
    RobotStatusResponse,
    RobotUpdateRequest,
)

logger = logging.getLogger(__name__)


def create_robot_command(
    db: Session,
    robot_id: str,
    request: RobotCommandCreateRequest,
    expiration_seconds: int,
) -> RobotCommandResponse | None:
    now = datetime.now(UTC)
    repository = RobotRepository(db)
    if repository.get_robot(robot_id) is None:
        logger.info(
            "command rejected robot_id=%s command_type=%s reason=robot_not_found",
            robot_id,
            request.command_type.value,
        )
        return None

    command = repository.create_command(
        robot_id=robot_id,
        command_type=request.command_type,
        payload=request.payload,
        origin=RobotCommandOrigin.OPERATOR,
        expires_at=now + timedelta(seconds=expiration_seconds),
    )
    db.commit()
    logger.info(
        "command created command_id=%s robot_id=%s command_type=%s origin=%s expires_at=%s",
        command.id,
        command.robot_id,
        command.command_type,
        command.origin,
        command.expires_at,
    )
    return _to_command_response(command)


def queue_battery_recovery_command(
    db: Session,
    robot_id: str,
    request: RobotBatteryRecoveryRequest,
) -> RobotCommandResponse | None:
    repository = RobotRepository(db)
    if repository.get_robot(robot_id) is None:
        logger.info("battery recovery rejected robot_id=%s reason=robot_not_found", robot_id)
        return None

    active_command = repository.get_active_system_recharge_command(robot_id)
    if active_command is not None:
        logger.debug(
            "battery recovery already pending command_id=%s robot_id=%s status=%s",
            active_command.id,
            active_command.robot_id,
            active_command.status,
        )
        return _to_command_response(active_command)

    command = repository.create_command(
        robot_id=robot_id,
        command_type=RobotCommandType.RECHARGE_TO_FULL,
        origin=RobotCommandOrigin.SYSTEM,
        payload={
            "reason": "low_battery",
            "battery_level": request.battery_level,
            "threshold_percent": request.threshold_percent,
        },
        expires_at=None,
    )
    db.commit()
    logger.info(
        "battery recovery queued command_id=%s robot_id=%s battery_level=%s threshold_percent=%s",
        command.id,
        command.robot_id,
        request.battery_level,
        request.threshold_percent,
    )
    return _to_command_response(command)


def claim_next_robot_command(db: Session, robot_id: str) -> RobotCommandNextResponse:
    now = datetime.now(UTC)
    repository = RobotRepository(db)
    command = repository.claim_next_command(robot_id, claimed_at=now)
    db.commit()
    if command is not None:
        logger.info(
            "command claimed command_id=%s robot_id=%s command_type=%s origin=%s",
            command.id,
            command.robot_id,
            command.command_type,
            command.origin,
        )
    else:
        logger.debug("no pending command robot_id=%s", robot_id)

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
        logger.info("command completion rejected command_id=%s robot_id=%s reason=not_found", command_id, robot_id)
        return None

    repository.add_event(
        robot_id,
        event_type="command_result",
        payload={
            "command_id": command_id,
            "origin": command.origin,
            "status": command_status.value,
            "result": request.result,
            "error_message": request.error_message,
        },
    )
    db.commit()
    logger.info(
        "command completed command_id=%s robot_id=%s status=%s",
        command.id,
        command.robot_id,
        command.status,
    )
    return _to_command_response(command)


def list_robot_commands(db: Session, robot_id: str, limit: int) -> list[RobotCommandResponse]:
    repository = RobotRepository(db)
    commands = repository.list_commands(robot_id, limit=limit, now=datetime.now(UTC))
    db.commit()
    return [_to_command_response(command) for command in commands]


def get_robot_status(db: Session, robot_id: str, offline_after_seconds: int) -> RobotStatusResponse | None:
    robot = RobotRepository(db).get_robot(robot_id)
    if robot is None:
        return None
    return _to_status_response(robot, datetime.now(UTC), offline_after_seconds)


def list_robot_command_page(db: Session, robot_id: str, page: int, page_size: int) -> RobotCommandListResponse | None:
    now = datetime.now(UTC)
    repository = RobotRepository(db)
    if repository.get_robot(robot_id) is None:
        return None

    total = repository.count_commands(robot_id, now)
    total_pages = max(1, ceil(total / page_size))
    clamped_page = min(page, total_pages)
    commands = repository.list_commands_page(robot_id, page=clamped_page, page_size=page_size, now=now)
    db.commit()
    return RobotCommandListResponse(
        commands=[_to_command_response(command) for command in commands],
        pagination=RobotStatusPagination(
            total=total,
            page=clamped_page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


def list_robot_event_page(db: Session, robot_id: str, page: int, page_size: int) -> RobotEventListResponse | None:
    repository = RobotRepository(db)
    if repository.get_robot(robot_id) is None:
        return None

    total = repository.count_events(robot_id)
    total_pages = max(1, ceil(total / page_size))
    clamped_page = min(page, total_pages)
    events = repository.list_events_page(robot_id, page=clamped_page, page_size=page_size)
    return RobotEventListResponse(
        events=[_to_event_response(event) for event in events],
        pagination=RobotStatusPagination(
            total=total,
            page=clamped_page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


def cleanup_old_robot_commands(db: Session, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    logger.debug("cleaning old robot commands cutoff=%s retention_days=%s", cutoff, retention_days)
    deleted_count = RobotRepository(db).delete_terminal_commands_older_than(cutoff)
    db.commit()
    return deleted_count


def cleanup_old_robot_events(db: Session, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    logger.debug("cleaning old robot events cutoff=%s retention_days=%s", cutoff, retention_days)
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
        origin=RobotCommandOrigin(command.origin),
        payload=command.payload,
        status=RobotCommandStatus(command.status),
        result=command.result,
        error_message=command.error_message,
        created_at=_ensure_aware(command.created_at),
        claimed_at=_ensure_aware(command.claimed_at) if command.claimed_at else None,
        completed_at=_ensure_aware(command.completed_at) if command.completed_at else None,
        expires_at=_ensure_aware(command.expires_at) if command.expires_at else None,
    )


def _to_event_response(event: RobotEvent) -> RobotEventResponse:
    return RobotEventResponse(
        id=event.id,
        robot_id=event.robot_id,
        event_type=event.event_type,
        payload=event.payload,
        created_at=_ensure_aware(event.created_at),
    )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value

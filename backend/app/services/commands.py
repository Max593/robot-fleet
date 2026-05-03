import logging
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy.orm import Session

from app.models.robot import RobotCommand
from app.repositories.commands import RobotCommandRepository
from app.repositories.events import RobotEventRepository
from app.repositories.robots import RobotRepository
from app.schemas.command import (
    RobotBatteryRecoveryRequest,
    RobotCommandCompleteRequest,
    RobotCommandCreateRequest,
    RobotCommandListResponse,
    RobotCommandNextResponse,
    RobotCommandOrigin,
    RobotCommandResponse,
    RobotCommandStatus,
    RobotCommandType,
    RobotSystemWorkRequest,
)
from app.schemas.robot import RobotStatusPagination

logger = logging.getLogger(__name__)


def create_robot_command(
    db: Session,
    robot_id: str,
    request: RobotCommandCreateRequest,
    expiration_seconds: int,
) -> RobotCommandResponse | None:
    now = datetime.now(UTC)
    robot_repository = RobotRepository(db)
    command_repository = RobotCommandRepository(db)
    if robot_repository.get_robot(robot_id) is None:
        logger.info(
            "command rejected robot_id=%s command_type=%s reason=robot_not_found",
            robot_id,
            request.command_type.value,
        )
        return None

    command = command_repository.create_command(
        robot_id=robot_id,
        command_type=request.command_type,
        payload=request.payload,
        origin=RobotCommandOrigin.OPERATOR,
        expires_at=now + timedelta(seconds=expiration_seconds),
    )
    RobotEventRepository(db).add_event(
        robot_id,
        event_type="command_lifecycle",
        payload={
            "command_id": command.id,
            "command_type": command.command_type,
            "origin": command.origin,
            "status": RobotCommandStatus.PENDING.value,
        },
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


def queue_system_work_command(
    db: Session,
    robot_id: str,
    request: RobotSystemWorkRequest,
) -> RobotCommandResponse | None:
    robot_repository = RobotRepository(db)
    command_repository = RobotCommandRepository(db)
    if robot_repository.get_robot(robot_id) is None:
        logger.info(
            "system work rejected robot_id=%s command_type=%s reason=robot_not_found",
            robot_id,
            request.command_type.value,
        )
        return None

    open_command = command_repository.get_open_system_work_command(robot_id)
    if open_command is not None:
        logger.debug(
            "system work already open command_id=%s robot_id=%s status=%s",
            open_command.id,
            open_command.robot_id,
            open_command.status,
        )
        return _to_command_response(open_command)

    command = command_repository.create_command(
        robot_id=robot_id,
        command_type=request.command_type,
        payload=request.payload,
        origin=RobotCommandOrigin.SYSTEM,
        expires_at=None,
    )
    RobotEventRepository(db).add_event(
        robot_id,
        event_type="command_lifecycle",
        payload={
            "command_id": command.id,
            "command_type": command.command_type,
            "origin": command.origin,
            "status": RobotCommandStatus.PENDING.value,
        },
    )
    db.commit()
    logger.debug(
        "system work queued command_id=%s robot_id=%s command_type=%s",
        command.id,
        command.robot_id,
        command.command_type,
    )
    return _to_command_response(command)


def queue_battery_recovery_command(
    db: Session,
    robot_id: str,
    request: RobotBatteryRecoveryRequest,
) -> RobotCommandResponse | None:
    robot_repository = RobotRepository(db)
    command_repository = RobotCommandRepository(db)
    if robot_repository.get_robot(robot_id) is None:
        logger.info("battery recovery rejected robot_id=%s reason=robot_not_found", robot_id)
        return None

    active_command = command_repository.get_pending_system_recharge_command(robot_id)
    if active_command is not None:
        logger.debug(
            "battery recovery already pending command_id=%s robot_id=%s status=%s",
            active_command.id,
            active_command.robot_id,
            active_command.status,
        )
        return _to_command_response(active_command)

    command = command_repository.create_command(
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
    RobotEventRepository(db).add_event(
        robot_id,
        event_type="command_lifecycle",
        payload={
            "command_id": command.id,
            "command_type": command.command_type,
            "origin": command.origin,
            "status": RobotCommandStatus.PENDING.value,
        },
    )
    db.commit()
    logger.debug(
        "battery recovery queued command_id=%s robot_id=%s battery_level=%s threshold_percent=%s",
        command.id,
        command.robot_id,
        request.battery_level,
        request.threshold_percent,
    )
    return _to_command_response(command)


def claim_next_robot_command(db: Session, robot_id: str) -> RobotCommandNextResponse:
    now = datetime.now(UTC)
    robot = RobotRepository(db).get_robot(robot_id)
    only_resume = robot is not None and robot.status == "paused"
    repository = RobotCommandRepository(db)
    command = repository.claim_next_command(robot_id, claimed_at=now, only_resume=only_resume)
    if command is not None:
        RobotEventRepository(db).add_event(
            robot_id,
            event_type="command_lifecycle",
            payload={
                "command_id": command.id,
                "command_type": command.command_type,
                "origin": command.origin,
                "status": RobotCommandStatus.EXECUTING.value,
            },
        )
    db.commit()
    if command is not None:
        _log_command(
            command.origin,
            "command executing command_id=%s robot_id=%s command_type=%s origin=%s",
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
    command_repository = RobotCommandRepository(db)
    event_repository = RobotEventRepository(db)
    command_status = RobotCommandStatus.COMPLETED if request.success else RobotCommandStatus.FAILED
    command = command_repository.complete_command(
        robot_id=robot_id,
        command_id=command_id,
        completed_at=now,
        status=command_status,
        result=request.result,
        error_message=request.error_message,
    )
    if command is None:
        db.rollback()
        logger.warning("command completion rejected command_id=%s robot_id=%s reason=not_found", command_id, robot_id)
        return None

    event_repository.add_event(
        robot_id,
        event_type="command_result",
        payload={
            "command_id": command_id,
            "command_type": command.command_type,
            "origin": command.origin,
            "status": command_status.value,
            "result": request.result,
            "error_message": request.error_message,
        },
    )
    db.commit()
    if command_status == RobotCommandStatus.FAILED:
        logger.warning(
            "command failed command_id=%s robot_id=%s error=%s",
            command.id,
            command.robot_id,
            command.error_message,
        )
    else:
        _log_command(
            command.origin,
            "command completed command_id=%s robot_id=%s status=%s",
            command.id,
            command.robot_id,
            command.status,
        )
    return _to_command_response(command)


def list_robot_commands(db: Session, robot_id: str, limit: int) -> list[RobotCommandResponse]:
    repository = RobotCommandRepository(db)
    commands = repository.list_commands(robot_id, limit=limit, now=datetime.now(UTC))
    db.commit()
    return [_to_command_response(command) for command in commands]


def list_robot_command_page(db: Session, robot_id: str, page: int, page_size: int) -> RobotCommandListResponse | None:
    now = datetime.now(UTC)
    command_repository = RobotCommandRepository(db)
    robot_repository = RobotRepository(db)
    if robot_repository.get_robot(robot_id) is None:
        return None

    total = command_repository.count_commands(robot_id, now)
    total_pages = max(1, ceil(total / page_size))
    clamped_page = min(page, total_pages)
    commands = command_repository.list_commands_page(robot_id, page=clamped_page, page_size=page_size, now=now)
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


def cleanup_old_robot_commands(db: Session, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    logger.debug("cleaning old robot commands cutoff=%s retention_days=%s", cutoff, retention_days)
    deleted_count = RobotCommandRepository(db).delete_terminal_commands_older_than(cutoff)
    db.commit()
    return deleted_count


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


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _log_command(origin: str, message: str, *args: object) -> None:
    if origin == RobotCommandOrigin.SYSTEM.value:
        logger.debug(message, *args)
    else:
        logger.info(message, *args)

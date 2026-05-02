from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.robot import (
    RobotAckResponse,
    RobotBatteryRecoveryRequest,
    RobotCommandCompleteRequest,
    RobotCommandCreateRequest,
    RobotCommandListResponse,
    RobotCommandNextResponse,
    RobotCommandResponse,
    RobotEventListResponse,
    RobotStatusFilter,
    RobotStatusListResponse,
    RobotStatusResponse,
    RobotUpdateRequest,
)
from app.services.robots import (
    claim_next_robot_command,
    complete_robot_command,
    create_robot_command,
    get_robot_status,
    list_robot_command_page,
    list_robot_event_page,
    list_robot_status_page,
    queue_battery_recovery_command,
    record_ping,
    record_update,
)

router = APIRouter(tags=["robots"])


@router.post("/robot/{robot_id}/ping", response_model=RobotAckResponse, status_code=status.HTTP_202_ACCEPTED)
def ping_robot(robot_id: str, db: Session = Depends(get_db)) -> RobotAckResponse:
    record_ping(db, robot_id)
    return RobotAckResponse(robot_id=robot_id)


@router.post("/robot/{robot_id}/update", response_model=RobotAckResponse, status_code=status.HTTP_202_ACCEPTED)
def update_robot(robot_id: str, payload: RobotUpdateRequest, db: Session = Depends(get_db)) -> RobotAckResponse:
    record_update(db, robot_id, payload)
    return RobotAckResponse(robot_id=robot_id)


@router.post(
    "/robots/{robot_id}/commands",
    response_model=RobotCommandResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_command(
    robot_id: str,
    payload: RobotCommandCreateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RobotCommandResponse:
    command = create_robot_command(
        db,
        robot_id,
        payload,
        expiration_seconds=settings.command_expiration_seconds,
    )
    if command is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not found")
    return command


@router.get("/robots/{robot_id}/commands", response_model=RobotCommandListResponse)
def get_robot_commands(
    robot_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    db: Session = Depends(get_db),
) -> RobotCommandListResponse:
    commands = list_robot_command_page(db, robot_id, page=page, page_size=page_size)
    if commands is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not found")
    return commands


@router.get("/robots/{robot_id}/events", response_model=RobotEventListResponse)
def get_robot_events(
    robot_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    db: Session = Depends(get_db),
) -> RobotEventListResponse:
    events = list_robot_event_page(db, robot_id, page=page, page_size=page_size)
    if events is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not found")
    return events


@router.get("/robot/{robot_id}/commands/next", response_model=RobotCommandNextResponse)
def get_next_robot_command(robot_id: str, db: Session = Depends(get_db)) -> RobotCommandNextResponse:
    return claim_next_robot_command(db, robot_id)


@router.post(
    "/robot/{robot_id}/commands/battery-recovery",
    response_model=RobotCommandResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_battery_recovery(
    robot_id: str,
    payload: RobotBatteryRecoveryRequest,
    db: Session = Depends(get_db),
) -> RobotCommandResponse:
    command = queue_battery_recovery_command(db, robot_id, payload)
    if command is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not found")
    return command


@router.post("/robot/{robot_id}/commands/{command_id}/complete", response_model=RobotCommandResponse)
def complete_command(
    robot_id: str,
    command_id: int,
    payload: RobotCommandCompleteRequest,
    db: Session = Depends(get_db),
) -> RobotCommandResponse:
    command = complete_robot_command(db, robot_id, command_id, payload)
    if command is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")
    return command


@router.get("/robots/status", response_model=RobotStatusListResponse)
def get_robot_statuses(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    search: Annotated[str | None, Query(max_length=64)] = None,
    status_filter: Annotated[RobotStatusFilter, Query(alias="filter")] = RobotStatusFilter.ALL,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RobotStatusListResponse:
    return list_robot_status_page(
        db,
        offline_after_seconds=settings.offline_after_seconds,
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
    )


@router.get("/robots/{robot_id}", response_model=RobotStatusResponse)
def get_robot(
    robot_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RobotStatusResponse:
    robot = get_robot_status(db, robot_id, offline_after_seconds=settings.offline_after_seconds)
    if robot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not found")
    return robot

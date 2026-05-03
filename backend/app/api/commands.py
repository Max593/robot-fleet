from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.command import (
    RobotBatteryRecoveryRequest,
    RobotCommandCompleteRequest,
    RobotCommandCreateRequest,
    RobotCommandListResponse,
    RobotCommandNextResponse,
    RobotCommandResponse,
    RobotSystemWorkRequest,
)
from app.services.commands import (
    claim_next_robot_command,
    complete_robot_command,
    create_robot_command,
    list_robot_command_page,
    queue_battery_recovery_command,
    queue_system_work_command,
)

router = APIRouter(tags=["commands"])


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


@router.get("/robots/{robot_id}/commands/next", response_model=RobotCommandNextResponse)
def get_next_robot_command(robot_id: str, db: Session = Depends(get_db)) -> RobotCommandNextResponse:
    return claim_next_robot_command(db, robot_id)


@router.post(
    "/robots/{robot_id}/commands/battery-recovery",
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


@router.post(
    "/robots/{robot_id}/commands/system-work",
    response_model=RobotCommandResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_system_work(
    robot_id: str,
    payload: RobotSystemWorkRequest,
    db: Session = Depends(get_db),
) -> RobotCommandResponse:
    command = queue_system_work_command(db, robot_id, payload)
    if command is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not found")
    return command


@router.post("/robots/{robot_id}/commands/{command_id}/complete", response_model=RobotCommandResponse)
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

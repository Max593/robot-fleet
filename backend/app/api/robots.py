from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.robot import (
    RobotAckResponse,
    RobotStatusFilter,
    RobotStatusListResponse,
    RobotStatusResponse,
    RobotUpdateRequest,
)
from app.services.robots import (
    get_robot_status,
    list_robot_status_page,
    record_ping,
    record_update,
)

router = APIRouter(tags=["robots"])


@router.post("/robots/{robot_id}/ping", response_model=RobotAckResponse, status_code=status.HTTP_202_ACCEPTED)
def ping_robot(robot_id: str, db: Session = Depends(get_db)) -> RobotAckResponse:
    record_ping(db, robot_id)
    return RobotAckResponse(robot_id=robot_id)


@router.post("/robots/{robot_id}/update", response_model=RobotAckResponse, status_code=status.HTTP_202_ACCEPTED)
def update_robot(robot_id: str, payload: RobotUpdateRequest, db: Session = Depends(get_db)) -> RobotAckResponse:
    record_update(db, robot_id, payload)
    return RobotAckResponse(robot_id=robot_id)


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

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.robot import RobotAckResponse, RobotStatusListResponse, RobotUpdateRequest
from app.services.robots import list_robot_statuses, record_ping, record_update

router = APIRouter(tags=["robots"])


@router.post("/robot/{robot_id}/ping", response_model=RobotAckResponse, status_code=status.HTTP_202_ACCEPTED)
def ping_robot(robot_id: str, db: Session = Depends(get_db)) -> RobotAckResponse:
    record_ping(db, robot_id)
    return RobotAckResponse(robot_id=robot_id)


@router.post("/robot/{robot_id}/update", response_model=RobotAckResponse, status_code=status.HTTP_202_ACCEPTED)
def update_robot(robot_id: str, payload: RobotUpdateRequest, db: Session = Depends(get_db)) -> RobotAckResponse:
    record_update(db, robot_id, payload)
    return RobotAckResponse(robot_id=robot_id)


@router.get("/robots/status", response_model=RobotStatusListResponse)
def get_robot_statuses(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RobotStatusListResponse:
    return RobotStatusListResponse(robots=list_robot_statuses(db, offline_after_seconds=settings.offline_after_seconds))

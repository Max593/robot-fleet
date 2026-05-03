from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.robot import RobotStatusPagination


class RobotEventResponse(BaseModel):
    id: int
    robot_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class RobotEventListResponse(BaseModel):
    events: list[RobotEventResponse]
    pagination: RobotStatusPagination

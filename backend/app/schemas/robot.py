from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RobotState = Literal["idle", "running"]


class RobotUpdateRequest(BaseModel):
    status: RobotState | None = None
    battery_level: int | None = Field(default=None, ge=0, le=100)


class RobotAckResponse(BaseModel):
    robot_id: str
    accepted: bool = True


class RobotStatusResponse(BaseModel):
    robot_id: str
    status: RobotState
    battery_level: int | None
    last_seen_at: datetime | None
    last_seen_seconds_ago: int | None
    is_online: bool


class RobotStatusListResponse(BaseModel):
    robots: list[RobotStatusResponse]

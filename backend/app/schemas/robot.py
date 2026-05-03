from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

RobotState = Literal["idle", "running", "paused", "charging"]


class RobotStatusFilter(str, Enum):
    ALL = "all"
    ONLINE = "online"
    OFFLINE = "offline"
    RUNNING = "running"
    IDLE = "idle"
    PAUSED = "paused"
    CHARGING = "charging"


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


class RobotStatusPagination(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class RobotFleetSummary(BaseModel):
    total: int
    online: int
    offline: int
    running: int
    idle: int
    paused: int
    charging: int


class RobotStatusListResponse(BaseModel):
    robots: list[RobotStatusResponse]
    pagination: RobotStatusPagination
    summary: RobotFleetSummary

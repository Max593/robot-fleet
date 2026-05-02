from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

RobotState = Literal["idle", "running"]


class RobotStatusFilter(str, Enum):
    ALL = "all"
    ONLINE = "online"
    OFFLINE = "offline"
    RUNNING = "running"
    IDLE = "idle"


class RobotCommandType(str, Enum):
    RUN_DIAGNOSTIC = "run_diagnostic"
    PAUSE_FOR = "pause_for"
    PAUSE_UNTIL_RESUMED = "pause_until_resumed"
    RESUME = "resume"
    RETURN_TO_BASE = "return_to_base"
    RECHARGE_TO_FULL = "recharge_to_full"


class RobotCommandStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RobotCommandOrigin(str, Enum):
    OPERATOR = "operator"
    SYSTEM = "system"


class RobotUpdateRequest(BaseModel):
    status: RobotState | None = None
    battery_level: int | None = Field(default=None, ge=0, le=100)


class RobotAckResponse(BaseModel):
    robot_id: str
    accepted: bool = True


class RobotCommandCreateRequest(BaseModel):
    command_type: RobotCommandType
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self) -> "RobotCommandCreateRequest":
        if self.command_type == RobotCommandType.PAUSE_FOR:
            duration_seconds = self.payload.get("duration_seconds")
            if not isinstance(duration_seconds, int) or duration_seconds < 1 or duration_seconds > 3600:
                raise ValueError("pause_for requires payload.duration_seconds between 1 and 3600")

        return self


class RobotCommandCompleteRequest(BaseModel):
    success: bool = True
    result: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = Field(default=None, max_length=1000)


class RobotBatteryRecoveryRequest(BaseModel):
    battery_level: int = Field(ge=0, le=100)
    threshold_percent: int = Field(ge=1, le=100)


class RobotCommandResponse(BaseModel):
    id: int
    robot_id: str
    command_type: RobotCommandType
    origin: RobotCommandOrigin
    payload: dict[str, Any]
    status: RobotCommandStatus
    result: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    claimed_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime | None


class RobotCommandListResponse(BaseModel):
    commands: list[RobotCommandResponse]
    pagination: "RobotStatusPagination"


class RobotCommandNextResponse(BaseModel):
    command: RobotCommandResponse | None = None


class RobotEventResponse(BaseModel):
    id: int
    robot_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class RobotEventListResponse(BaseModel):
    events: list[RobotEventResponse]
    pagination: "RobotStatusPagination"


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


class RobotStatusListResponse(BaseModel):
    robots: list[RobotStatusResponse]
    pagination: RobotStatusPagination
    summary: RobotFleetSummary

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.robot import RobotStatusPagination


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
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RobotCommandOrigin(str, Enum):
    OPERATOR = "operator"
    SYSTEM = "system"


class RobotCommandCreateRequest(BaseModel):
    command_type: RobotCommandType
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self) -> "RobotCommandCreateRequest":
        if self.command_type == RobotCommandType.PAUSE_FOR:
            duration_seconds = self.payload.get("duration_seconds")
            if not isinstance(duration_seconds, int) or duration_seconds < 1 or duration_seconds > 3600:
                raise ValueError("pause_for requires payload.duration_seconds between 1 and 3600")

        if "failure_reason" in self.payload:
            raise ValueError("payload.failure_reason is simulator-owned and cannot be requested")

        return self


class RobotCommandCompleteRequest(BaseModel):
    success: bool = True
    result: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = Field(default=None, max_length=1000)


class RobotBatteryRecoveryRequest(BaseModel):
    battery_level: int = Field(ge=0, le=100)
    threshold_percent: int = Field(ge=1, le=100)


class RobotSystemWorkRequest(BaseModel):
    command_type: RobotCommandType
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_system_command(self) -> "RobotSystemWorkRequest":
        if self.command_type not in {RobotCommandType.RUN_DIAGNOSTIC, RobotCommandType.RETURN_TO_BASE}:
            raise ValueError("system work supports run_diagnostic and return_to_base")

        if "failure_reason" in self.payload:
            raise ValueError("payload.failure_reason is simulator-owned and cannot be requested")

        return self


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
    pagination: RobotStatusPagination


class RobotCommandNextResponse(BaseModel):
    command: RobotCommandResponse | None = None

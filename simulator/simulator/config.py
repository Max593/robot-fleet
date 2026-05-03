from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    backend_base_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    robot_count: int = Field(default=5000, ge=1)
    heartbeat_interval_seconds: float = Field(default=60.0, gt=0)
    max_concurrent_requests: int = Field(default=100, ge=1)
    request_timeout_seconds: float = Field(default=5.0, gt=0)
    downtime_probability: float = Field(default=0.03, ge=0, le=1)
    min_downtime_seconds: float = Field(default=60.0, ge=0)
    max_downtime_seconds: float = Field(default=120.0, ge=0)
    system_work_probability: float = Field(default=0.01, ge=0, le=1)
    startup_jitter_seconds: float = Field(default=15.0, ge=0)
    command_poll_interval_seconds: float = Field(default=30.0, gt=0)
    command_execution_tick_seconds: float = Field(default=5.0, gt=0)
    command_battery_drain_min_percent: int = Field(default=2, ge=0, le=100)
    command_battery_drain_max_percent: int = Field(default=5, ge=0, le=100)
    command_failure_probability: float = Field(default=0.03, ge=0, le=1)
    command_min_battery_percent: int = Field(default=10, ge=0, le=100)
    diagnostic_duration_seconds: float = Field(default=20.0, gt=0)
    return_to_base_duration_seconds: float = Field(default=45.0, gt=0)
    recharge_tick_seconds: float = Field(default=5.0, gt=0)
    recharge_step_percent: int = Field(default=10, ge=1, le=100)
    low_battery_threshold_percent: int = Field(default=15, ge=1, le=100)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_ranges(self) -> "Settings":
        if self.command_battery_drain_min_percent > self.command_battery_drain_max_percent:
            raise ValueError("COMMAND_BATTERY_DRAIN_MIN_PERCENT must be <= COMMAND_BATTERY_DRAIN_MAX_PERCENT")
        if self.min_downtime_seconds > self.max_downtime_seconds:
            raise ValueError("MIN_DOWNTIME_SECONDS must be <= MAX_DOWNTIME_SECONDS")
        return self

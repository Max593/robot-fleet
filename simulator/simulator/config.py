from pydantic import Field
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
    status_change_probability: float = Field(default=0.15, ge=0, le=1)
    startup_jitter_seconds: float = Field(default=15.0, ge=0)
    command_poll_interval_seconds: float = Field(default=30.0, gt=0)
    diagnostic_duration_seconds: float = Field(default=20.0, gt=0)
    return_to_base_duration_seconds: float = Field(default=45.0, gt=0)
    recharge_tick_seconds: float = Field(default=5.0, gt=0)
    recharge_step_percent: int = Field(default=10, ge=1, le=100)
    low_battery_threshold_percent: int = Field(default=15, ge=1, le=100)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

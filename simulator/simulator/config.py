from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    backend_base_url: str = "http://localhost:8000"
    robot_count: int = Field(default=5000, ge=1)
    heartbeat_interval_seconds: float = Field(default=60.0, gt=0)
    max_concurrent_requests: int = Field(default=100, ge=1)
    request_timeout_seconds: float = Field(default=5.0, gt=0)
    downtime_probability: float = Field(default=0.03, ge=0, le=1)
    min_downtime_seconds: float = Field(default=60.0, ge=0)
    max_downtime_seconds: float = Field(default=120.0, ge=0)
    status_change_probability: float = Field(default=0.15, ge=0, le=1)
    startup_jitter_seconds: float = Field(default=15.0, ge=0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

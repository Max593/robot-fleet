from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://robot:robot@localhost:5432/robot_fleet"
    log_level: str = "INFO"
    offline_after_seconds: int = 45
    command_retention_days: int = 30
    command_expiration_seconds: int = 120
    event_retention_days: int = 1
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

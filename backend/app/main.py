import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.commands import router as commands_router
from app.api.events import router as events_router
from app.api.robots import router as robots_router
from app.config import get_settings
from app.db.session import SessionLocal
from app.logging_config import configure_logging
from app.services.commands import cleanup_old_robot_commands
from app.services.events import cleanup_old_robot_events

logger = logging.getLogger(__name__)

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "backend starting, log_level=%s, offline_after_seconds=%s, command_expiration_seconds=%s",
        settings.log_level.upper(),
        settings.offline_after_seconds,
        settings.command_expiration_seconds,
    )
    with SessionLocal() as db:
        deleted_commands = cleanup_old_robot_commands(db, settings.command_retention_days)
        deleted_events = cleanup_old_robot_events(db, settings.event_retention_days)
        logger.info(
            "retention cleanup completed deleted_commands=%s deleted_events=%s",
            deleted_commands,
            deleted_events,
        )

    yield

    logger.info("backend shutting down")


app = FastAPI(title="Robot Fleet Operations API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(robots_router)
app.include_router(commands_router)
app.include_router(events_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

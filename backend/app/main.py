import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.robots import router as robots_router
from app.config import get_settings
from app.db.session import SessionLocal
from app.services.robots import cleanup_old_robot_commands, cleanup_old_robot_events

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with SessionLocal() as db:
        deleted_commands = cleanup_old_robot_commands(db, settings.command_retention_days)
        deleted_events = cleanup_old_robot_events(db, settings.event_retention_days)
        if deleted_commands > 0:
            logger.info("deleted %s old robot commands", deleted_commands)
        if deleted_events > 0:
            logger.info("deleted %s old robot events", deleted_events)

    yield


app = FastAPI(title="Robot Fleet Operations API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(robots_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

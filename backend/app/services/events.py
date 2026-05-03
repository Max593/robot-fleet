import logging
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy.orm import Session

from app.models.robot import RobotEvent
from app.repositories.events import RobotEventRepository
from app.repositories.robots import RobotRepository
from app.schemas.event import RobotEventListResponse, RobotEventResponse
from app.schemas.robot import RobotStatusPagination

logger = logging.getLogger(__name__)


def list_robot_event_page(db: Session, robot_id: str, page: int, page_size: int) -> RobotEventListResponse | None:
    robot_repository = RobotRepository(db)
    event_repository = RobotEventRepository(db)
    if robot_repository.get_robot(robot_id) is None:
        return None

    total = event_repository.count_events(robot_id)
    total_pages = max(1, ceil(total / page_size))
    clamped_page = min(page, total_pages)
    events = event_repository.list_events_page(robot_id, page=clamped_page, page_size=page_size)
    return RobotEventListResponse(
        events=[_to_event_response(event) for event in events],
        pagination=RobotStatusPagination(
            total=total,
            page=clamped_page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


def cleanup_old_robot_events(db: Session, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    logger.debug("cleaning old robot events cutoff=%s retention_days=%s", cutoff, retention_days)
    deleted_count = RobotEventRepository(db).delete_events_older_than(cutoff)
    db.commit()
    return deleted_count


def _to_event_response(event: RobotEvent) -> RobotEventResponse:
    return RobotEventResponse(
        id=event.id,
        robot_id=event.robot_id,
        event_type=event.event_type,
        payload=event.payload,
        created_at=_ensure_aware(event.created_at),
    )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value

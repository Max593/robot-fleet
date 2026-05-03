from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.robot import RobotEvent


class RobotEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_event(self, robot_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.db.add(RobotEvent(robot_id=robot_id, event_type=event_type, payload=payload))

    def count_events(self, robot_id: str) -> int:
        stmt = select(func.count(RobotEvent.id)).where(RobotEvent.robot_id == robot_id)
        return int(self.db.execute(stmt).scalar_one())

    def list_events_page(self, robot_id: str, page: int, page_size: int) -> list[RobotEvent]:
        offset = (page - 1) * page_size
        stmt = (
            select(RobotEvent)
            .where(RobotEvent.robot_id == robot_id)
            .order_by(RobotEvent.created_at.desc(), RobotEvent.id.desc())
            .limit(page_size)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def delete_events_older_than(self, cutoff: datetime) -> int:
        result = self.db.execute(delete(RobotEvent).where(RobotEvent.created_at < cutoff))
        return int(result.rowcount or 0)

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.robot import Robot, RobotEvent


class RobotRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_ping(self, robot_id: str, seen_at: datetime) -> None:
        stmt = (
            insert(Robot)
            .values(robot_id=robot_id, status="idle", last_seen_at=seen_at, updated_at=seen_at)
            .on_conflict_do_update(
                index_elements=[Robot.robot_id],
                set_={"last_seen_at": seen_at, "updated_at": seen_at},
            )
        )
        self.db.execute(stmt)

    def upsert_update(self, robot_id: str, payload: dict[str, Any], seen_at: datetime) -> None:
        insert_values = {
            "robot_id": robot_id,
            "status": payload.get("status", "idle"),
            "battery_level": payload.get("battery_level"),
            "last_seen_at": seen_at,
            "updated_at": seen_at,
        }
        update_values = {"last_seen_at": seen_at, "updated_at": seen_at, **payload}

        stmt = (
            insert(Robot)
            .values(**insert_values)
            .on_conflict_do_update(index_elements=[Robot.robot_id], set_=update_values)
        )
        self.db.execute(stmt)

    def add_event(self, robot_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.db.add(RobotEvent(robot_id=robot_id, event_type=event_type, payload=payload))

    def list_all(self) -> list[Robot]:
        return list(self.db.execute(select(Robot).order_by(Robot.robot_id)).scalars().all())

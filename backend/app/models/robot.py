from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Robot(Base):
    __tablename__ = "robots"
    __table_args__ = (
        CheckConstraint("status IN ('idle', 'running')", name="ck_robots_status"),
        CheckConstraint(
            "battery_level IS NULL OR (battery_level >= 0 AND battery_level <= 100)",
            name="ck_robots_battery_level",
        ),
        Index("ix_robots_last_seen_at", "last_seen_at"),
        Index("ix_robots_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="idle", server_default="idle")
    battery_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["RobotEvent"]] = relationship(
        back_populates="robot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RobotEvent(Base):
    __tablename__ = "robot_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('heartbeat', 'status_update', 'offline_detected', 'command_result')",
            name="ck_robot_events_event_type",
        ),
        Index("ix_robot_events_robot_created_at", "robot_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    robot_id: Mapped[str] = mapped_column(String(64), ForeignKey("robots.robot_id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    robot: Mapped[Robot] = relationship(back_populates="events")

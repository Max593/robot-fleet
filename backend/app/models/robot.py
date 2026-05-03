from datetime import datetime

from sqlalchemy import JSON, BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

json_document_type = JSONB().with_variant(JSON(), "sqlite")
big_integer_id_type = BigInteger().with_variant(Integer(), "sqlite")


class Robot(Base):
    __tablename__ = "robots"
    __table_args__ = (
        CheckConstraint("status IN ('idle', 'running', 'paused', 'charging')", name="ck_robots_status"),
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
    commands: Mapped[list["RobotCommand"]] = relationship(
        back_populates="robot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RobotEvent(Base):
    __tablename__ = "robot_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('heartbeat', 'status_update', 'offline_detected', 'command_lifecycle', 'command_result')",
            name="ck_robot_events_event_type",
        ),
        Index("ix_robot_events_robot_created_at", "robot_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(big_integer_id_type, primary_key=True, autoincrement=True)
    robot_id: Mapped[str] = mapped_column(String(64), ForeignKey("robots.robot_id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(json_document_type, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    robot: Mapped[Robot] = relationship(back_populates="events")


class RobotCommand(Base):
    __tablename__ = "robot_commands"
    __table_args__ = (
        CheckConstraint(
            "command_type IN ("
            "'run_diagnostic', 'pause_for', 'pause_until_resumed', 'resume', 'return_to_base', 'recharge_to_full'"
            ")",
            name="ck_robot_commands_command_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'claimed', 'executing', 'completed', 'failed', 'expired', 'cancelled')",
            name="ck_robot_commands_status",
        ),
        CheckConstraint("origin IN ('operator', 'system')", name="ck_robot_commands_origin"),
        Index("ix_robot_commands_robot_origin_type_status", "robot_id", "origin", "command_type", "status"),
        Index("ix_robot_commands_robot_created_at", "robot_id", "created_at"),
        Index("ix_robot_commands_robot_status_created_at", "robot_id", "status", "created_at"),
        Index("ix_robot_commands_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(big_integer_id_type, primary_key=True, autoincrement=True)
    robot_id: Mapped[str] = mapped_column(String(64), ForeignKey("robots.robot_id", ondelete="CASCADE"), index=True)
    command_type: Mapped[str] = mapped_column(String(64))
    origin: Mapped[str] = mapped_column(String(32), default="operator", server_default="operator")
    payload: Mapped[dict] = mapped_column(json_document_type, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(32), default="pending", server_default="pending")
    result: Mapped[dict | None] = mapped_column(json_document_type, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    robot: Mapped[Robot] = relationship(back_populates="commands")

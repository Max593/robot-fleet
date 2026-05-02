from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.robot import Robot, RobotCommand, RobotEvent
from app.repositories.robots import RobotRepository
from app.schemas.robot import RobotCommandCreateRequest, RobotCommandStatus, RobotCommandType


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        yield session


def test_pause_for_requires_duration() -> None:
    with pytest.raises(ValidationError):
        RobotCommandCreateRequest(command_type=RobotCommandType.PAUSE_FOR)


def test_pause_for_accepts_bounded_duration() -> None:
    request = RobotCommandCreateRequest(
        command_type=RobotCommandType.PAUSE_FOR,
        payload={"duration_seconds": 60},
    )

    assert request.payload == {"duration_seconds": 60}


def test_recharge_to_full_does_not_require_payload() -> None:
    request = RobotCommandCreateRequest(command_type=RobotCommandType.RECHARGE_TO_FULL)

    assert request.payload == {}


def test_cleanup_deletes_only_old_terminal_commands(db: Session) -> None:
    now = datetime(2026, 5, 2, tzinfo=UTC)
    old = now - timedelta(days=31)
    recent = now - timedelta(days=5)
    repository = RobotRepository(db)

    db.add(Robot(robot_id="robot-000001"))
    db.flush()
    db.add_all(
        [
            RobotCommand(
                id=1,
                robot_id="robot-000001",
                command_type="run_diagnostic",
                status="completed",
                created_at=old,
                completed_at=old,
            ),
            RobotCommand(
                id=2,
                robot_id="robot-000001",
                command_type="run_diagnostic",
                status="failed",
                created_at=old,
                completed_at=old,
            ),
            RobotCommand(
                id=3,
                robot_id="robot-000001",
                command_type="run_diagnostic",
                status="completed",
                created_at=recent,
                completed_at=recent,
            ),
            RobotCommand(
                id=4,
                robot_id="robot-000001",
                command_type="run_diagnostic",
                status="pending",
                created_at=old,
            ),
            RobotCommand(
                id=5,
                robot_id="robot-000001",
                command_type="run_diagnostic",
                status="claimed",
                created_at=old,
            ),
        ]
    )
    db.commit()

    deleted_count = repository.delete_terminal_commands_older_than(now - timedelta(days=30))
    db.commit()

    remaining_statuses = db.execute(select(RobotCommand.status).order_by(RobotCommand.id)).scalars().all()
    assert deleted_count == 2
    assert remaining_statuses == ["completed", "pending", "claimed"]


def test_cleanup_deletes_old_events(db: Session) -> None:
    now = datetime(2026, 5, 2, tzinfo=UTC)
    old = now - timedelta(days=8)
    recent = now - timedelta(days=3)
    repository = RobotRepository(db)

    db.add(Robot(robot_id="robot-000001"))
    db.flush()
    db.add_all(
        [
            RobotEvent(id=1, robot_id="robot-000001", event_type="command_result", payload={}, created_at=old),
            RobotEvent(id=2, robot_id="robot-000001", event_type="command_result", payload={}, created_at=recent),
        ]
    )
    db.commit()

    deleted_count = repository.delete_events_older_than(now - timedelta(days=7))
    db.commit()

    remaining_events = db.execute(select(RobotEvent.id)).scalars().all()
    assert deleted_count == 1
    assert remaining_events == [2]


def test_claim_next_command_expires_overdue_pending_commands(db: Session) -> None:
    now = datetime(2026, 5, 2, tzinfo=UTC)
    repository = RobotRepository(db)

    db.add(Robot(robot_id="robot-000001"))
    db.flush()
    db.add_all(
        [
            RobotCommand(
                id=1,
                robot_id="robot-000001",
                command_type="run_diagnostic",
                status="pending",
                created_at=now - timedelta(minutes=5),
                expires_at=now - timedelta(seconds=1),
            ),
            RobotCommand(
                id=2,
                robot_id="robot-000001",
                command_type="run_diagnostic",
                status="pending",
                created_at=now,
                expires_at=now + timedelta(minutes=2),
            ),
        ]
    )
    db.commit()

    command = repository.claim_next_command("robot-000001", claimed_at=now)
    db.commit()

    statuses = db.execute(select(RobotCommand.status).order_by(RobotCommand.id)).scalars().all()
    assert command is not None
    assert command.id == 2
    assert statuses == [RobotCommandStatus.EXPIRED.value, RobotCommandStatus.CLAIMED.value]


def test_list_commands_expires_overdue_pending_commands(db: Session) -> None:
    now = datetime(2026, 5, 2, tzinfo=UTC)
    repository = RobotRepository(db)

    db.add(Robot(robot_id="robot-000001"))
    db.flush()
    db.add(
        RobotCommand(
            id=1,
            robot_id="robot-000001",
            command_type="run_diagnostic",
            status="pending",
            created_at=now - timedelta(minutes=5),
            expires_at=now - timedelta(seconds=1),
        )
    )
    db.commit()

    commands = repository.list_commands("robot-000001", limit=10, now=now)
    db.commit()

    assert len(commands) == 1
    assert commands[0].status == RobotCommandStatus.EXPIRED.value
    assert commands[0].completed_at == now.replace(tzinfo=None)

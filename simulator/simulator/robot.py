import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

import httpx

from simulator.config import Settings

logger = logging.getLogger(__name__)

EXECUTABLE_COMMANDS = {"run_diagnostic", "return_to_base"}
FAILURE_REASONS = ("navigation_blocked", "sensor_error", "timeout", "diagnostic_failed")


@dataclass
class RobotState:
    robot_id: str
    status: str = "idle"
    battery_level: int = 100

    def drain_idle(self) -> None:
        self.battery_level = max(0, self.battery_level - random.randint(0, 1))

    def drain_running(self, settings: Settings) -> None:
        self.battery_level = max(
            0,
            self.battery_level
            - random.randint(settings.command_battery_drain_min_percent, settings.command_battery_drain_max_percent),
        )


@dataclass
class ActiveCommand:
    command_id: int
    command_type: str
    origin: str
    finishes_at: float
    failure_reason: str | None = None


@dataclass
class RobotControlState:
    paused_until: float | None = None
    paused_until_resumed: bool = False
    pause_command_id: int | None = None
    active_command: ActiveCommand | None = None
    recharge_command_id: int | None = None
    battery_recovery_requested: bool = False

    def is_paused(self, now: float) -> bool:
        if self.paused_until_resumed:
            return True
        return self.paused_until is not None and now < self.paused_until

    def elapsed_pause_command_id(self, now: float) -> int | None:
        if self.paused_until_resumed or self.paused_until is None or now < self.paused_until:
            return None

        command_id = self.pause_command_id
        self.paused_until = None
        self.pause_command_id = None
        return command_id

    def start_timed_pause(self, command_id: int, paused_until: float) -> None:
        self.paused_until = paused_until
        self.paused_until_resumed = False
        self.pause_command_id = command_id
        self.active_command = None

    def start_indefinite_pause(self, command_id: int) -> None:
        self.paused_until = None
        self.paused_until_resumed = True
        self.pause_command_id = command_id
        self.active_command = None

    def resume(self) -> int | None:
        paused_command_id = self.pause_command_id
        self.paused_until = None
        self.paused_until_resumed = False
        self.pause_command_id = None
        return paused_command_id

    def is_recharging(self) -> bool:
        return self.recharge_command_id is not None

    def is_busy(self) -> bool:
        return self.active_command is not None or self.is_recharging()

    def start_recharge(self, command_id: int) -> None:
        self.recharge_command_id = command_id
        self.battery_recovery_requested = True
        self.paused_until = None
        self.paused_until_resumed = False
        self.pause_command_id = None
        self.active_command = None

    def finish_recharge(self) -> int | None:
        command_id = self.recharge_command_id
        self.recharge_command_id = None
        self.battery_recovery_requested = False
        return command_id


async def simulate_robot(
    robot_number: int,
    client: httpx.AsyncClient,
    settings: Settings,
    request_gate: asyncio.Semaphore,
) -> None:
    state = RobotState(robot_id=f"robot-{robot_number:06d}", battery_level=random.randint(40, 100))
    control_state = RobotControlState()
    next_command_poll_at = 0.0

    if settings.startup_jitter_seconds > 0:
        await asyncio.sleep(random.uniform(0, settings.startup_jitter_seconds))

    while True:
        now = time.monotonic()
        await _complete_elapsed_pause(client, request_gate, state, control_state, now)

        if now >= next_command_poll_at and not control_state.is_busy():
            await _poll_and_apply_command(client, request_gate, state, control_state, settings)
            next_command_poll_at = _next_command_poll_at(settings)

        if control_state.is_recharging():
            await _run_recharge_tick(client, request_gate, state, control_state, settings)
            continue

        if control_state.active_command is not None:
            await _run_active_command_tick(client, request_gate, state, control_state, settings)
            continue

        if control_state.is_paused(time.monotonic()):
            await _run_pause_tick(client, request_gate, state, control_state, settings)
            continue

        if random.random() < settings.downtime_probability:
            downtime = random.uniform(settings.min_downtime_seconds, settings.max_downtime_seconds)
            logger.debug("%s offline for %.1fs", state.robot_id, downtime)
            await asyncio.sleep(downtime)

        state.status = "idle"
        state.drain_idle()

        await _send_robot_state(client, request_gate, state)
        await _queue_battery_recovery_if_needed(client, request_gate, state, control_state, settings)
        await _queue_system_work_if_needed(client, request_gate, state, control_state, settings)

        heartbeat_jitter = random.uniform(-0.15, 0.15) * settings.heartbeat_interval_seconds
        sleep_for = max(1.0, settings.heartbeat_interval_seconds + heartbeat_jitter)
        next_command_poll_at = await _sleep_with_command_polling(
            client,
            request_gate,
            state,
            control_state,
            settings,
            sleep_for,
            next_command_poll_at,
        )


async def _sleep_with_command_polling(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
    control_state: RobotControlState,
    settings: Settings,
    sleep_for: float,
    next_command_poll_at: float,
) -> float:
    sleep_until = time.monotonic() + sleep_for

    while time.monotonic() < sleep_until:
        now = time.monotonic()
        await _complete_elapsed_pause(client, request_gate, state, control_state, now)
        if now >= next_command_poll_at and not control_state.is_busy():
            await _poll_and_apply_command(client, request_gate, state, control_state, settings)
            next_command_poll_at = _next_command_poll_at(settings)
            if control_state.is_busy() or control_state.is_paused(time.monotonic()):
                return next_command_poll_at

        await asyncio.sleep(min(1.0, max(0.0, sleep_until - time.monotonic())))

    return next_command_poll_at


async def _poll_and_apply_command(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
    control_state: RobotControlState,
    settings: Settings,
) -> None:
    command = await _get_next_command(client, request_gate, state.robot_id)
    if command is None:
        logger.debug("no command available robot_id=%s", state.robot_id)
        return

    command_id = int(command["id"])
    command_type = str(command["command_type"])
    origin = str(command.get("origin", "operator"))
    payload = command.get("payload") or {}
    _log_command(
        origin,
        "command started robot_id=%s command_id=%s command_type=%s origin=%s",
        state.robot_id,
        command_id,
        command_type,
        origin,
    )

    try:
        if command_type == "pause_for":
            duration_seconds = float(payload["duration_seconds"])
            control_state.start_timed_pause(command_id, time.monotonic() + duration_seconds)
            state.status = "paused"
            await _send_robot_state(client, request_gate, state)
            return

        if command_type == "pause_until_resumed":
            control_state.start_indefinite_pause(command_id)
            state.status = "paused"
            await _send_robot_state(client, request_gate, state)
            return

        if command_type == "resume":
            paused_command_id = control_state.resume()
            state.status = "idle"
            await _send_robot_state(client, request_gate, state)
            if paused_command_id is not None:
                await _complete_command(
                    client,
                    request_gate,
                    state.robot_id,
                    paused_command_id,
                    success=True,
                    result={"resumed_by_command_id": command_id},
                    origin=origin,
                )
            await _complete_command(
                client,
                request_gate,
                state.robot_id,
                command_id,
                success=True,
                result={"resumed": True},
                origin=origin,
            )
            return

        if command_type in EXECUTABLE_COMMANDS:
            await _start_executable_command(
                client,
                request_gate,
                state,
                control_state,
                settings,
                command_id,
                command_type,
                origin,
            )
            return

        if command_type == "recharge_to_full":
            if state.battery_level >= 100:
                state.status = "idle"
                await _complete_command(
                    client,
                    request_gate,
                    state.robot_id,
                    command_id,
                    success=True,
                    result={"battery_level": state.battery_level, "already_full": True},
                    origin=origin,
                )
                return

            state.status = "charging"
            control_state.start_recharge(command_id)
            logger.debug(
                "recharge started robot_id=%s command_id=%s battery_level=%s",
                state.robot_id,
                command_id,
                state.battery_level,
            )
            return

        raise ValueError(f"unsupported command type {command_type}")
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "command failed robot_id=%s command_id=%s command_type=%s error=%s",
            state.robot_id,
            command_id,
            command_type,
            exc,
        )
        await _complete_command(
            client,
            request_gate,
            state.robot_id,
            command_id,
            success=False,
            error_message=str(exc),
            origin=origin,
        )


async def _start_executable_command(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
    control_state: RobotControlState,
    settings: Settings,
    command_id: int,
    command_type: str,
    origin: str,
) -> None:
    if state.battery_level <= settings.command_min_battery_percent:
        await _complete_command(
            client,
            request_gate,
            state.robot_id,
            command_id,
            success=False,
            error_message="low_battery",
            result={"battery_level": state.battery_level},
            origin=origin,
        )
        return

    duration_seconds = _command_duration(command_type, settings)
    failure_reason = _failure_reason(settings)
    control_state.active_command = ActiveCommand(
        command_id=command_id,
        command_type=command_type,
        origin=origin,
        finishes_at=time.monotonic() + duration_seconds,
        failure_reason=failure_reason,
    )
    state.status = "running"
    await _send_robot_state(client, request_gate, state)
    _log_command(
        origin,
        "command execution started robot_id=%s command_id=%s command_type=%s duration_seconds=%.1f failure_reason=%s",
        state.robot_id,
        command_id,
        command_type,
        duration_seconds,
        failure_reason,
    )


async def _run_active_command_tick(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
    control_state: RobotControlState,
    settings: Settings,
) -> None:
    active_command = control_state.active_command
    if active_command is None:
        return

    state.status = "running"
    state.drain_running(settings)
    await _send_robot_state(client, request_gate, state)

    if state.battery_level <= 0:
        control_state.active_command = None
        state.status = "idle"
        await _complete_command(
            client,
            request_gate,
            state.robot_id,
            active_command.command_id,
            success=False,
            error_message="low_battery",
            result={"battery_level": state.battery_level},
            origin=active_command.origin,
        )
        return

    if time.monotonic() >= active_command.finishes_at:
        control_state.active_command = None
        state.status = "idle"
        if active_command.failure_reason is not None:
            await _complete_command(
                client,
                request_gate,
                state.robot_id,
                active_command.command_id,
                success=False,
                error_message=active_command.failure_reason,
                result={"battery_level": state.battery_level},
                origin=active_command.origin,
            )
        else:
            await _complete_command(
                client,
                request_gate,
                state.robot_id,
                active_command.command_id,
                success=True,
                result={
                    "battery_level": state.battery_level,
                    "executed_for_seconds": _command_duration(active_command.command_type, settings),
                },
                origin=active_command.origin,
            )
        return

    await asyncio.sleep(
        min(settings.command_execution_tick_seconds, max(1.0, active_command.finishes_at - time.monotonic()))
    )


async def _run_pause_tick(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
    control_state: RobotControlState,
    settings: Settings,
) -> None:
    state.status = "paused"
    state.drain_idle()
    await _send_robot_state(client, request_gate, state)
    await _queue_battery_recovery_if_needed(client, request_gate, state, control_state, settings)
    await asyncio.sleep(min(settings.command_poll_interval_seconds, settings.heartbeat_interval_seconds))


async def _complete_elapsed_pause(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
    control_state: RobotControlState,
    now: float,
) -> None:
    command_id = control_state.elapsed_pause_command_id(now)
    if command_id is None:
        return

    state.status = "idle"
    await _send_robot_state(client, request_gate, state)
    await _complete_command(
        client,
        request_gate,
        state.robot_id,
        command_id,
        success=True,
        result={"pause_elapsed": True},
    )


async def _run_recharge_tick(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
    control_state: RobotControlState,
    settings: Settings,
) -> None:
    state.status = "charging"
    state.battery_level = min(100, state.battery_level + settings.recharge_step_percent)
    logger.debug(
        "recharge tick robot_id=%s command_id=%s battery_level=%s",
        state.robot_id,
        control_state.recharge_command_id,
        state.battery_level,
    )
    await _send_robot_state(client, request_gate, state)

    if state.battery_level >= 100:
        command_id = control_state.finish_recharge()
        state.status = "idle"
        await _send_robot_state(client, request_gate, state)
        if command_id is not None:
            logger.debug("recharge completed robot_id=%s command_id=%s", state.robot_id, command_id)
            await _complete_command(
                client,
                request_gate,
                state.robot_id,
                command_id,
                success=True,
                result={"battery_level": state.battery_level, "recharged_to_full": True},
                origin="system",
            )
        return

    await asyncio.sleep(settings.recharge_tick_seconds)


async def _complete_command(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    robot_id: str,
    command_id: int,
    success: bool,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
    origin: str = "operator",
) -> None:
    await _post(
        client,
        request_gate,
        f"/robots/{robot_id}/commands/{command_id}/complete",
        json={"success": success, "result": result or {}, "error_message": error_message},
    )
    if success:
        _log_command(
            origin,
            "command completion reported robot_id=%s command_id=%s success=%s",
            robot_id,
            command_id,
            success,
        )
    else:
        logger.warning(
            "command failure reported robot_id=%s command_id=%s error=%s",
            robot_id,
            command_id,
            error_message,
        )


async def _queue_battery_recovery_if_needed(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
    control_state: RobotControlState,
    settings: Settings,
) -> None:
    if state.battery_level > settings.low_battery_threshold_percent:
        control_state.battery_recovery_requested = False
        return
    if control_state.battery_recovery_requested:
        return

    try:
        async with request_gate:
            response = await client.post(
                f"/robots/{state.robot_id}/commands/battery-recovery",
                json={
                    "battery_level": state.battery_level,
                    "threshold_percent": settings.low_battery_threshold_percent,
                },
            )
            response.raise_for_status()
            command = response.json()
            logger.debug(
                "battery recovery requested robot_id=%s command_id=%s battery_level=%s",
                state.robot_id,
                command["id"],
                state.battery_level,
            )
            control_state.battery_recovery_requested = True
    except httpx.HTTPError as exc:
        logger.warning("battery recovery request failed for %s: %s", state.robot_id, exc)


async def _queue_system_work_if_needed(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
    control_state: RobotControlState,
    settings: Settings,
) -> None:
    if control_state.is_busy() or control_state.is_paused(time.monotonic()):
        return
    if state.battery_level <= settings.low_battery_threshold_percent:
        return
    if random.random() >= settings.system_work_probability:
        return

    command_type = random.choice(tuple(EXECUTABLE_COMMANDS))
    try:
        async with request_gate:
            response = await client.post(
                f"/robots/{state.robot_id}/commands/system-work",
                json={"command_type": command_type, "payload": {"reason": "autonomous_schedule"}},
            )
            response.raise_for_status()
            command = response.json()
            logger.debug(
                "system work requested robot_id=%s command_id=%s command_type=%s",
                state.robot_id,
                command["id"],
                command_type,
            )
    except httpx.HTTPError as exc:
        logger.warning("system work request failed for %s: %s", state.robot_id, exc)


async def _get_next_command(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    robot_id: str,
) -> dict[str, Any] | None:
    try:
        async with request_gate:
            response = await client.get(f"/robots/{robot_id}/commands/next")
            response.raise_for_status()
            data = response.json()
            return data.get("command")
    except httpx.HTTPError as exc:
        logger.warning("command poll failed for %s: %s", robot_id, exc)
        return None


async def _send_robot_state(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
) -> None:
    await _post(client, request_gate, f"/robots/{state.robot_id}/ping", json=None)
    await _post(
        client,
        request_gate,
        f"/robots/{state.robot_id}/update",
        json={"status": state.status, "battery_level": state.battery_level},
    )


def _command_duration(command_type: str, settings: Settings) -> float:
    if command_type == "run_diagnostic":
        return settings.diagnostic_duration_seconds
    if command_type == "return_to_base":
        return settings.return_to_base_duration_seconds
    raise ValueError(f"unsupported executable command type {command_type}")


def _failure_reason(settings: Settings) -> str | None:
    if random.random() < settings.command_failure_probability:
        return random.choice(FAILURE_REASONS)

    return None


def _next_command_poll_at(settings: Settings) -> float:
    jitter = random.uniform(-0.15, 0.15) * settings.command_poll_interval_seconds
    return time.monotonic() + max(1.0, settings.command_poll_interval_seconds + jitter)


def _log_command(origin: str, message: str, *args: object) -> None:
    if origin == "system":
        logger.debug(message, *args)
    else:
        logger.info(message, *args)


async def _post(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    path: str,
    json: dict | None,
) -> None:
    try:
        async with request_gate:
            if json is None:
                response = await client.post(path)
            else:
                response = await client.post(path, json=json)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("request failed for %s: %s", path, exc)

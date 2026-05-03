import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

import httpx

from simulator.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class RobotState:
    robot_id: str
    status: str = "idle"
    battery_level: int = 100

    def tick(self, status_change_probability: float, low_battery_threshold_percent: int) -> None:
        if random.random() < status_change_probability:
            self.status = "running" if self.status == "idle" else "idle"

        if self.status == "running":
            self.battery_level = max(0, self.battery_level - random.randint(2, 5))
        else:
            self.battery_level = max(0, self.battery_level - random.randint(0, 1))

        if self.battery_level <= low_battery_threshold_percent:
            self.status = "idle"


@dataclass
class RobotControlState:
    paused_until: float | None = None
    paused_until_resumed: bool = False
    forced_status: str | None = None
    forced_status_until: float | None = None
    recharge_command_id: int | None = None
    battery_recovery_requested: bool = False

    def is_paused(self, now: float) -> bool:
        if self.paused_until_resumed:
            return True
        if self.paused_until is None:
            return False
        if now < self.paused_until:
            return True

        self.paused_until = None
        return False

    def effective_status(self, now: float) -> str | None:
        if self.forced_status_until is None or self.forced_status is None:
            return None
        if now < self.forced_status_until:
            return self.forced_status

        self.forced_status = None
        self.forced_status_until = None
        return None

    def resume(self) -> None:
        self.paused_until = None
        self.paused_until_resumed = False

    def is_recharging(self) -> bool:
        return self.recharge_command_id is not None

    def start_recharge(self, command_id: int) -> None:
        self.recharge_command_id = command_id
        self.battery_recovery_requested = True
        self.paused_until = None
        self.paused_until_resumed = False
        self.forced_status = None
        self.forced_status_until = None

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
        if now >= next_command_poll_at and not control_state.is_recharging():
            await _poll_and_apply_command(client, request_gate, state, control_state, settings)
            next_command_poll_at = _next_command_poll_at(settings)

        if control_state.is_recharging():
            await _run_recharge_tick(client, request_gate, state, control_state, settings)
            continue

        if control_state.is_paused(time.monotonic()):
            await asyncio.sleep(min(settings.command_poll_interval_seconds, settings.heartbeat_interval_seconds))
            continue

        if random.random() < settings.downtime_probability:
            downtime = random.uniform(settings.min_downtime_seconds, settings.max_downtime_seconds)
            logger.debug("%s offline for %.1fs", state.robot_id, downtime)
            await asyncio.sleep(downtime)

        forced_status = control_state.effective_status(time.monotonic())
        if forced_status:
            state.status = forced_status
            state.tick(
                status_change_probability=0,
                low_battery_threshold_percent=settings.low_battery_threshold_percent,
            )
        else:
            state.tick(
                status_change_probability=settings.status_change_probability,
                low_battery_threshold_percent=settings.low_battery_threshold_percent,
            )

        await _post(client, request_gate, f"/robots/{state.robot_id}/ping", json=None)
        await _post(
            client,
            request_gate,
            f"/robots/{state.robot_id}/update",
            json={"status": state.status, "battery_level": state.battery_level},
        )
        await _queue_battery_recovery_if_needed(client, request_gate, state, control_state, settings)

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
        if now >= next_command_poll_at and not control_state.is_recharging():
            await _poll_and_apply_command(client, request_gate, state, control_state, settings)
            next_command_poll_at = _next_command_poll_at(settings)
            if control_state.is_recharging():
                return next_command_poll_at
            if control_state.is_paused(time.monotonic()):
                return next_command_poll_at

        await asyncio.sleep(min(1.0, sleep_until - time.monotonic()))

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
    logger.info("command claimed robot_id=%s command_id=%s command_type=%s", state.robot_id, command_id, command_type)
    try:
        should_complete, result = _apply_command(command, state, control_state, settings)
        logger.info(
            "command applied robot_id=%s command_id=%s command_type=%s completes_immediately=%s",
            state.robot_id,
            command_id,
            command_type,
            should_complete,
        )
        if should_complete:
            await _complete_command(client, request_gate, state.robot_id, command_id, result)
    except (KeyError, TypeError, ValueError) as exc:
        logger.info(
            "command failed robot_id=%s command_id=%s command_type=%s error=%s",
            state.robot_id,
            command_id,
            command_type,
            exc,
        )
        await _post(
            client,
            request_gate,
            f"/robots/{state.robot_id}/commands/{command['id']}/complete",
            json={"success": False, "error_message": str(exc)},
        )


def _apply_command(
    command: dict[str, Any],
    state: RobotState,
    control_state: RobotControlState,
    settings: Settings,
) -> tuple[bool, dict[str, Any]]:
    command_type = command["command_type"]
    payload = command.get("payload") or {}
    now = time.monotonic()

    if command_type == "pause_for":
        duration_seconds = float(payload["duration_seconds"])
        control_state.paused_until = now + duration_seconds
        control_state.paused_until_resumed = False
        return True, {"paused_for_seconds": duration_seconds}

    if command_type == "pause_until_resumed":
        control_state.paused_until = None
        control_state.paused_until_resumed = True
        return True, {"paused_until_resumed": True}

    if command_type == "resume":
        control_state.resume()
        return True, {"resumed": True}

    if command_type == "run_diagnostic":
        control_state.forced_status = "running"
        control_state.forced_status_until = now + settings.diagnostic_duration_seconds
        return True, {"forced_status": "running", "duration_seconds": settings.diagnostic_duration_seconds}

    if command_type == "return_to_base":
        control_state.forced_status = "running"
        control_state.forced_status_until = now + settings.return_to_base_duration_seconds
        return True, {"forced_status": "running", "duration_seconds": settings.return_to_base_duration_seconds}

    if command_type == "recharge_to_full":
        state.status = "idle"
        if state.battery_level >= 100:
            return True, {"battery_level": state.battery_level, "already_full": True}

        control_state.start_recharge(int(command["id"]))
        logger.info(
            "recharge started robot_id=%s command_id=%s battery_level=%s",
            state.robot_id,
            command["id"],
            state.battery_level,
        )
        return False, {"recharge_started": True}

    raise ValueError(f"unsupported command type {command_type}")


async def _run_recharge_tick(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    state: RobotState,
    control_state: RobotControlState,
    settings: Settings,
) -> None:
    state.status = "idle"
    state.battery_level = min(100, state.battery_level + settings.recharge_step_percent)
    logger.debug(
        "recharge tick robot_id=%s command_id=%s battery_level=%s",
        state.robot_id,
        control_state.recharge_command_id,
        state.battery_level,
    )
    await _post(client, request_gate, f"/robots/{state.robot_id}/ping", json=None)
    await _post(
        client,
        request_gate,
        f"/robots/{state.robot_id}/update",
        json={"status": state.status, "battery_level": state.battery_level},
    )

    if state.battery_level >= 100:
        command_id = control_state.finish_recharge()
        if command_id is not None:
            logger.info("recharge completed robot_id=%s command_id=%s", state.robot_id, command_id)
            await _complete_command(
                client,
                request_gate,
                state.robot_id,
                command_id,
                {"battery_level": state.battery_level, "recharged_to_full": True},
            )
        return

    await asyncio.sleep(settings.recharge_tick_seconds)


async def _complete_command(
    client: httpx.AsyncClient,
    request_gate: asyncio.Semaphore,
    robot_id: str,
    command_id: int,
    result: dict[str, Any],
) -> None:
    await _post(
        client,
        request_gate,
        f"/robots/{robot_id}/commands/{command_id}/complete",
        json={"success": True, "result": result},
    )
    logger.info("command completion reported robot_id=%s command_id=%s", robot_id, command_id)


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
            logger.info(
                "battery recovery requested robot_id=%s command_id=%s battery_level=%s",
                state.robot_id,
                command["id"],
                state.battery_level,
            )
            control_state.battery_recovery_requested = True
    except httpx.HTTPError as exc:
        logger.warning("battery recovery request failed for %s: %s", state.robot_id, exc)


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


def _next_command_poll_at(settings: Settings) -> float:
    jitter = random.uniform(-0.15, 0.15) * settings.command_poll_interval_seconds
    return time.monotonic() + max(1.0, settings.command_poll_interval_seconds + jitter)


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

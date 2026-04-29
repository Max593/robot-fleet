import asyncio
import logging
import random
from dataclasses import dataclass

import httpx

from simulator.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class RobotState:
    robot_id: str
    status: str = "idle"
    battery_level: int = 100

    def tick(self, status_change_probability: float) -> None:
        if random.random() < status_change_probability:
            self.status = "running" if self.status == "idle" else "idle"

        if self.status == "running":
            self.battery_level = max(0, self.battery_level - random.randint(1, 3))
        else:
            self.battery_level = min(100, self.battery_level + random.randint(0, 1))

        if self.battery_level <= 10:
            self.status = "idle"


async def simulate_robot(
    robot_number: int,
    client: httpx.AsyncClient,
    settings: Settings,
    request_gate: asyncio.Semaphore,
) -> None:
    state = RobotState(robot_id=f"robot-{robot_number:06d}", battery_level=random.randint(40, 100))

    if settings.startup_jitter_seconds > 0:
        await asyncio.sleep(random.uniform(0, settings.startup_jitter_seconds))

    while True:
        if random.random() < settings.downtime_probability:
            downtime = random.uniform(settings.min_downtime_seconds, settings.max_downtime_seconds)
            logger.debug("%s offline for %.1fs", state.robot_id, downtime)
            await asyncio.sleep(downtime)

        state.tick(settings.status_change_probability)
        await _post(client, request_gate, f"/robot/{state.robot_id}/ping", json=None)
        await _post(
            client,
            request_gate,
            f"/robot/{state.robot_id}/update",
            json={"status": state.status, "battery_level": state.battery_level},
        )

        heartbeat_jitter = random.uniform(-0.15, 0.15) * settings.heartbeat_interval_seconds
        sleep_for = max(1.0, settings.heartbeat_interval_seconds + heartbeat_jitter)
        await asyncio.sleep(sleep_for)


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

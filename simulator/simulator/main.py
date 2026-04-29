import asyncio
import logging
import time

import httpx

from simulator.config import Settings
from simulator.robot import simulate_robot


async def run() -> None:
    settings = Settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.info(
        "starting simulator with %s robots, heartbeat interval %.1fs, max concurrency %s",
        settings.robot_count,
        settings.heartbeat_interval_seconds,
        settings.max_concurrent_requests,
    )

    request_gate = asyncio.Semaphore(settings.max_concurrent_requests)
    timeout = httpx.Timeout(settings.request_timeout_seconds)

    async with httpx.AsyncClient(base_url=settings.backend_base_url, timeout=timeout) as client:
        await wait_for_backend(client)
        async with asyncio.TaskGroup() as task_group:
            for robot_number in range(1, settings.robot_count + 1):
                task_group.create_task(simulate_robot(robot_number, client, settings, request_gate))


async def wait_for_backend(client: httpx.AsyncClient) -> None:
    last_log_at = 0.0

    while True:
        try:
            response = await client.get("/health")
            response.raise_for_status()
            logging.info("backend is reachable")
            return
        except httpx.HTTPError:
            now = time.monotonic()
            if now - last_log_at >= 5:
                logging.info("waiting for backend at %s", client.base_url)
                last_log_at = now
            await asyncio.sleep(1)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()

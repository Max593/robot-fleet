# Development Notes

This page collects the lower-level details for running and extending Robot Fleet Operations locally.

## Simulation Model

The simulator is intentionally configurable. The current settings aim to make the dashboard active while keeping local load bounded:

```text
ROBOT_COUNT=5000
HEARTBEAT_INTERVAL_SECONDS=60
MAX_CONCURRENT_REQUESTS=100
DOWNTIME_PROBABILITY=0.03
MIN_DOWNTIME_SECONDS=60
MAX_DOWNTIME_SECONDS=120
OFFLINE_AFTER_SECONDS=45
LOG_LEVEL=INFO
COMMAND_RETENTION_DAYS=30
COMMAND_EXPIRATION_SECONDS=120
EVENT_RETENTION_DAYS=1
COMMAND_POLL_INTERVAL_SECONDS=30
RECHARGE_TICK_SECONDS=5
RECHARGE_STEP_PERCENT=10
LOW_BATTERY_THRESHOLD_PERCENT=15
```

Each robot periodically sends a heartbeat and a state update. Status and battery level change locally inside the simulator. Running robots drain battery faster, idle robots drain battery slowly, and battery is recovered only through recharge behavior. Downtime is simulated by pausing a robot loop so it stops sending updates for a short period.

`MAX_CONCURRENT_REQUESTS` limits simultaneous simulator HTTP requests even when thousands of robot tasks are running.

Robots also poll for queued commands. Command overrides take priority over autonomous behavior while they are active, then the robot returns to the regular simulator loop.

When a robot battery reaches `LOW_BATTERY_THRESHOLD_PERCENT`, the simulator asks the backend to queue a non-expiring system `recharge_to_full` command if one is not already pending or claimed. This records autonomous recovery as command history instead of silently changing battery state.

Downtime must be longer than the backend `OFFLINE_AFTER_SECONDS` threshold to become visible as offline in the dashboard. The default values use a 45-second offline threshold and 60-120 second downtime windows so short outages are visible but robots return quickly.

Part of the project is calibrating heartbeat frequency, downtime duration, offline thresholds, and state-change probability so the local simulation behaves like a plausible robot fleet rather than a fixed script.

## API Surface

Current endpoints:

```text
POST /robots/{robot_id}/ping
POST /robots/{robot_id}/update
GET /robots/status
GET /robots/{robot_id}
GET /robots/{robot_id}/events
POST /robots/{robot_id}/commands
GET /robots/{robot_id}/commands
POST /robots/{robot_id}/commands/battery-recovery
GET /robots/{robot_id}/commands/next
POST /robots/{robot_id}/commands/{command_id}/complete
```

`GET /robots/status` supports backend-side pagination and dashboard filters:

```text
GET /robots/status?page=1&page_size=25
GET /robots/status?page=1&page_size=50&filter=online
GET /robots/status?page=1&page_size=10&filter=running&search=robot-0001
```

Supported page sizes in the dashboard are:

```text
10 / 25 / 50 / 100
```

Supported filter values are:

```text
all / online / offline / running / idle
```

The `running` and `idle` filters currently apply only to robots that are online. Offline robots retain their last reported status in the database, but they are grouped by connectivity first in the dashboard.

The response includes the current page, pagination metadata, and global fleet summary counts:

```json
{
  "robots": [],
  "pagination": {
    "total": 5000,
    "page": 1,
    "page_size": 25,
    "total_pages": 200
  },
  "summary": {
    "total": 5000,
    "online": 4864,
    "offline": 136,
    "running": 699,
    "idle": 4165
  }
}
```

Robot detail uses the current-state endpoint plus paginated history endpoints:

```text
GET /robots/robot-000001
GET /robots/robot-000001/events?page=1&page_size=25
GET /robots/robot-000001/commands?page=1&page_size=25
```

Event and command history are ordered newest first. The dashboard links to these views by making each robot row clickable.

Example update:

```bash
curl -X POST http://localhost:8000/robots/robot-000001/update \
  -H "content-type: application/json" \
  -d '{"status":"running","battery_level":82}'
```

Operator command creation:

```bash
curl -X POST http://localhost:8000/robots/robot-000001/commands \
  -H "content-type: application/json" \
  -d '{"command_type":"pause_for","payload":{"duration_seconds":60}}'
```

Supported command types are:

```text
run_diagnostic / pause_for / pause_until_resumed / resume / return_to_base / recharge_to_full
```

Commands include an `origin` field:

```text
operator / system
```

Dashboard-created commands are stored as `operator`. Low-battery recharge jobs created by the simulator are stored as `system` and use `expires_at = null`, so they do not expire while waiting to be claimed.

The simulator claims pending commands through `GET /robots/{robot_id}/commands/next` and reports the outcome through `POST /robots/{robot_id}/commands/{command_id}/complete`. `COMMAND_EXPIRATION_SECONDS` controls how long a pending command may wait before being claimed. If the robot does not claim it in time, the backend marks it as `expired`.

`recharge_to_full` is a long-running simulator override. While it is active, the robot stays online, reports `idle`, skips random downtime, increases battery by `RECHARGE_STEP_PERCENT` every `RECHARGE_TICK_SECONDS`, then completes the command when battery reaches 100.

The current implementation keeps command override state in simulator memory. Command history is persisted in PostgreSQL, but active runtime overrides reset when the simulator container restarts.

## Frontend API Contract

FastAPI exposes an OpenAPI contract at `/openapi.json`. As the API surface grows, the frontend can use that contract to generate TypeScript types or a typed API client. This would reduce duplicated request/response definitions between the backend Pydantic schemas and frontend TypeScript code.

OpenAPI generation should be considered a contract and typing improvement, not a replacement for clear frontend organization. Page, component, API module, and shared type boundaries still need to be designed explicitly.

The current frontend keeps those boundaries explicit with small responsibility-based modules:

```text
api/         backend request helpers
components/ reusable dashboard and detail UI pieces
pages/      route-level dashboard and robot detail views
types.ts    shared frontend data types
utils/      formatting, routing, and theme helpers
```

## Database And Migrations

PostgreSQL stores the current robot state, command history, and significant event history.

Current tables:

- `robots`: latest known state for each robot
- `robot_events`: significant event history such as command results
- `robot_commands`: command queue, lifecycle state, payloads, results, and retention history

`COMMAND_RETENTION_DAYS` controls command cleanup. On backend startup, terminal command rows older than the retention window are deleted. Active commands are not deleted by cleanup.

`EVENT_RETENTION_DAYS` controls event cleanup. It is intentionally short for this simulation because `robot_events` backs recent robot-detail logs rather than long-term analytics. Routine heartbeat and status-update calls update the `robots` current-state table but are not inserted into `robot_events`; this keeps the simulator from producing high-volume audit rows for normal traffic.

Retention cleanup currently runs from FastAPI lifespan startup, so it executes when the backend process starts or restarts. It does not run on every request. A scheduled cleanup worker can be added later if the backend needs to stay online for long periods without restarts.

Schema migrations are managed with Alembic from `backend/alembic`. The backend container runs:

```bash
alembic upgrade head
```

before starting Uvicorn.

Robot status is currently stored as a string column with a database `CHECK` constraint. That keeps early migrations simple. If the status model grows beyond `idle` and `running`, a good next step is introducing a shared Python `RobotStatus(str, Enum)` for application typing, then deciding whether the database should remain string-plus-check or move to a native PostgreSQL enum.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic
- **Database:** PostgreSQL
- **Migrations:** Alembic
- **Simulator:** Python asyncio, HTTPX
- **Frontend:** React, Vite, TypeScript
- **Runtime:** Docker Compose

## Project Layout

```text
backend/          FastAPI app, SQLAlchemy models, repositories, Alembic
simulator/        Async robot simulator
frontend/         React dashboard
.infrastructure/  Docker Compose and service Dockerfiles
docs/assets/      README images and project media
```

Within `backend/app`, API routes, schemas, repositories, and services are split by responsibility:

```text
robots    current robot state, check-ins, fleet status
commands  command queueing, claiming, completion, recovery jobs
events    robot event history and cleanup
```

The SQLAlchemy models currently stay together in `models/robot.py` because `Robot`, `RobotCommand`, and `RobotEvent` are tightly related through foreign keys and relationships.

## Local Backend Development

For local backend development outside Docker:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
export DATABASE_URL=postgresql+psycopg://robot:robot@localhost:5432/robot_fleet
alembic upgrade head
uvicorn app.main:app --reload
```

Create a migration after model changes:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Logging

Backend and simulator logs use Python's standard `logging` module and write to stdout/stderr, so they are visible through Docker Compose:

```bash
docker compose -f .infrastructure/docker-compose.yml logs -f backend
docker compose -f .infrastructure/docker-compose.yml logs -f simulator
```

`LOG_LEVEL` defaults to `INFO`. Use `DEBUG` when you need lower-level details such as empty command polls, recharge ticks, or cleanup cutoffs. Routine heartbeat and status-update requests are intentionally not logged per robot because the simulator runs thousands of robots.

## Linting And Formatting

Python linting and formatting are handled by Ruff. The repository uses a root-level `ruff.toml` so the backend and simulator share one policy.

Install the development tools from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Common commands are also available from the root `Makefile`:

```bash
make backend-test
make frontend-typecheck
make frontend-build
make lint
make up
make down
```

Run Ruff manually:

```bash
ruff check backend simulator
ruff format backend simulator
```

Install the Git hook:

```bash
pre-commit install
```

After that, every commit runs:

```text
ruff check --fix
ruff format
```

If Ruff modifies files during a commit, review the changes, stage them, and commit again.

Frontend validation currently uses TypeScript:

```bash
cd frontend
npm run typecheck
```

ESLint can be added later if the frontend grows enough to need a dedicated linting policy.

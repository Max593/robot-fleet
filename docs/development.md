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
```

Each robot periodically sends a heartbeat and a state update. Status and battery level change locally inside the simulator. Downtime is simulated by pausing a robot loop so it stops sending updates for a short period.

`MAX_CONCURRENT_REQUESTS` limits simultaneous simulator HTTP requests even when thousands of robot tasks are running.

Downtime must be longer than the backend `OFFLINE_AFTER_SECONDS` threshold to become visible as offline in the dashboard. The default values use a 45-second offline threshold and 60-120 second downtime windows so short outages are visible but robots return quickly.

Part of the project is calibrating heartbeat frequency, downtime duration, offline thresholds, and state-change probability so the local simulation behaves like a plausible robot fleet rather than a fixed script.

## API Surface

Current endpoints:

```text
POST /robot/{robot_id}/ping
POST /robot/{robot_id}/update
GET /robots/status
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

Example update:

```bash
curl -X POST http://localhost:8000/robot/robot-000001/update \
  -H "content-type: application/json" \
  -d '{"status":"running","battery_level":82}'
```

## Database And Migrations

PostgreSQL stores the current robot state and a lightweight event history.

Initial tables:

- `robots`: latest known state for each robot
- `robot_events`: heartbeat and status-update history

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

## Linting And Formatting

Python linting and formatting are handled by Ruff. The repository uses a root-level `ruff.toml` so the backend and simulator share one policy.

Install the development tools from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
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

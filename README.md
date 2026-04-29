<h1 align="center">Robot Fleet Operations</h1>

<p align="center">
  <img src="docs/assets/dashboard.png" alt="Robot Fleet Operations dashboard">
</p>

Robot Fleet Operations is a proof of concept for monitoring a simulated fleet of robots. It models common systems concerns in robotics-adjacent software: periodic heartbeats, online/offline detection, state ingestion, database persistence, schema migrations, and an operations dashboard for quickly understanding fleet health.

The project is simulation-first: robots, downtime, battery levels, and status changes are generated locally so the backend can be exercised without physical hardware. Docker Compose runs the full stack with a FastAPI backend, PostgreSQL database, async Python robot simulator, and React dashboard. The simulator can run thousands of lightweight robot tasks while bounding request concurrency, making it useful for testing backend behavior under realistic local load.

This is currently the MVP foundation. The first version focuses on fleet status and heartbeat monitoring. Upcoming work will build on these service boundaries with command dispatch, telemetry ingestion, Redis/WebSocket workflows, Prometheus metrics, and Grafana dashboards.

## Core Capabilities

- FastAPI service design with typed request and response schemas
- PostgreSQL persistence with SQLAlchemy repositories
- Alembic database migrations
- Async Python simulation for thousands of robots
- Online/offline detection from heartbeat freshness
- Docker Compose orchestration for local reproducibility
- React/Vite dashboard with search, pagination, and status filters

## Architecture

```text
simulator -> FastAPI backend -> PostgreSQL
frontend  -> FastAPI backend
```

The simulator runs many lightweight asyncio tasks inside one Python process. Scale is controlled through environment variables, and concurrent HTTP pressure is bounded so the local machine is not overwhelmed.

## Features

- Simulates 5,000 robots by default
- Robots report heartbeat, status, and battery level
- Dashboard shows total, online, offline, running, and idle counts
- Metric cards filter the robot table
- Robot table supports search and pagination
- Backend stores current robot state and lightweight event history
- Migrations run automatically when the backend starts

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic
- **Database:** PostgreSQL
- **Migrations:** Alembic
- **Simulator:** Python asyncio, HTTPX
- **Frontend:** React, Vite, TypeScript
- **Runtime:** Docker Compose

## Quick Start

From the repository root:

```bash
docker compose -f .infrastructure/docker-compose.yml up --build
```

Then open:

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/health

PostgreSQL is exposed on:

```text
localhost:5432
```

To stop the stack:

```bash
docker compose -f .infrastructure/docker-compose.yml down
```

To stop the stack and delete local database data:

```bash
docker compose -f .infrastructure/docker-compose.yml down -v
```

The backend runs Alembic automatically on startup, so a fresh database volume is migrated again when the stack starts.

## API

Core endpoints:

```text
POST /robot/{robot_id}/ping
POST /robot/{robot_id}/update
GET /robots/status
```

Example update:

```bash
curl -X POST http://localhost:8000/robot/robot-000001/update \
  -H "content-type: application/json" \
  -d '{"status":"running","battery_level":82}'
```

## Database

Schema migrations are managed with Alembic from `backend/alembic`.

Initial tables:

- `robots`: latest known robot state
- `robot_events`: lightweight audit/event history

Robot status is currently stored as a string column with a database `CHECK` constraint. That keeps early migrations simple. If the status model grows beyond `idle` and `running`, a good next step is introducing a shared Python `RobotStatus(str, Enum)` for application typing, then deciding whether the database should remain string-plus-check or move to a native PostgreSQL enum.

## Simulator Controls

Default runtime values are configured in `.infrastructure/docker-compose.yml`:

```text
ROBOT_COUNT=5000
HEARTBEAT_INTERVAL_SECONDS=60
MAX_CONCURRENT_REQUESTS=100
DOWNTIME_PROBABILITY=0.03
MIN_DOWNTIME_SECONDS=60
MAX_DOWNTIME_SECONDS=120
OFFLINE_AFTER_SECONDS=45
```

`MAX_CONCURRENT_REQUESTS` limits simultaneous simulator HTTP requests even when thousands of robot tasks are running.

Downtime must be longer than the backend `OFFLINE_AFTER_SECONDS` threshold to become visible as offline in the dashboard. The default values use a 45-second offline threshold and 60-120 second downtime windows so short outages are visible but robots return quickly.

The simulator values are intentionally configurable. Part of the project is calibrating heartbeat frequency, downtime duration, offline thresholds, and state-change probability so the local simulation behaves like a plausible robot fleet rather than a fixed script.

## Local Backend Development

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

## Project Layout

```text
backend/          FastAPI app, SQLAlchemy models, repositories, Alembic
simulator/        Async robot simulator
frontend/         React dashboard
.infrastructure/  Docker Compose and service Dockerfiles
```

## Roadmap

- Robot command dispatch
- Command result reporting
- Backend-side pagination and filtering
- Prometheus metrics endpoint
- Grafana dashboard
- Redis queue/pub-sub layer if ingestion or command delivery needs decoupling
- Offline robot log buffering and later synchronization

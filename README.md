<h1 align="center">Robot Fleet Operations</h1>

<p align="center">
  <img src="docs/assets/dashboard.png" alt="Robot Fleet Operations dashboard">
</p>

Robot Fleet Operations is a proof of concept for a local robot fleet monitoring platform. It simulates thousands of robots reporting heartbeats, status, and battery levels to a FastAPI backend, stores fleet state in PostgreSQL, and presents the current system state through a lightweight operations dashboard.

The project is simulation-first. Robot behavior such as downtime, status changes, and battery movement is generated locally, which makes it possible to explore backend reliability, state management, and observability patterns without physical hardware.

The current version focuses on heartbeat monitoring and fleet state. The project is designed to evolve toward command dispatch, telemetry ingestion, Redis/WebSocket workflows, and Prometheus/Grafana observability.

## Overview

The system is built as a small local platform rather than a single script. A robot simulator produces periodic state updates, the backend ingests and persists the latest known state, and the dashboard gives a compact view of fleet health.

The goal of the first version is to make the core workflow tangible:

```text
robot checks in -> backend stores state -> dashboard shows fleet status
```

From there, the project can grow into more operational workflows: sending commands to robots, collecting telemetry, exposing metrics, and visualizing system behavior over time.

## Current Capabilities

- Simulates 5,000 robots by default
- Tracks robot heartbeat, status, battery level, and last-seen time
- Detects online/offline state from heartbeat freshness
- Stores latest fleet state in PostgreSQL
- Records lightweight robot events for audit/history
- Provides a dashboard with search, pagination, and status filters
- Runs locally with Docker Compose
- Applies database migrations automatically on backend startup

## System Architecture

```text
simulator -> FastAPI backend -> PostgreSQL
frontend  -> FastAPI backend
```

The simulator runs many lightweight asyncio tasks inside one Python process. Request concurrency is capped independently from robot count, so the simulator can model thousands of robots without opening thousands of simultaneous HTTP requests.

The backend owns the API, database access, and fleet-state rules. PostgreSQL stores the latest robot state and a lightweight event history. The frontend polls the backend and presents the current status of the fleet.

## Running Locally

From the repository root:

```bash
docker compose -f .infrastructure/docker-compose.yml up --build
```

Then open:

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/health

To stop the stack:

```bash
docker compose -f .infrastructure/docker-compose.yml down
```

To stop the stack and delete local database data:

```bash
docker compose -f .infrastructure/docker-compose.yml down -v
```

The backend runs Alembic automatically on startup, so a fresh database volume is migrated again when the stack starts.

## Roadmap

- Robot command dispatch
- Command result reporting
- Backend-side pagination and filtering
- Telemetry ingestion
- Prometheus metrics endpoint
- Grafana dashboard
- Redis queue/pub-sub layer for async ingestion and command delivery
- WebSocket updates for the dashboard
- Offline robot log buffering and later synchronization

## Documentation

For simulator settings, API details, database migrations, project layout, and local development commands, see [Development Notes](docs/development.md).

COMPOSE = docker compose -f .infrastructure/docker-compose.yml

.PHONY: up down logs backend-test frontend-typecheck frontend-build lint

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

backend-test:
	.venv/bin/pytest backend/tests

frontend-typecheck:
	$(COMPOSE) exec -T frontend npm run typecheck

frontend-build:
	$(COMPOSE) exec -T frontend npm run build

lint:
	.venv/bin/pre-commit run --all-files

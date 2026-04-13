PYTHON ?= 3.14.4

.PHONY: help setup install lint format typecheck test precommit run docker-up docker-down

help:
	@echo "setup        - install python, sync deps, install pre-commit"
	@echo "install      - sync dependencies"
	@echo "lint         - run ruff check"
	@echo "format       - run ruff format"
	@echo "typecheck    - run ty"
	@echo "test         - run pytest"
	@echo "precommit    - run all local quality checks"
	@echo "run          - run backend locally"
	@echo "web-install  - install frontend dependencies"
	@echo "web-lint     - run frontend lint"
	@echo "web-build    - run frontend production build"
	@echo "web-dev      - run frontend dev server"
	@echo "ci           - run backend + frontend quality checks"
	@echo "docker-up    - start local containers"
	@echo "docker-down  - stop local containers"

setup:
	uv python install $(PYTHON)
	uv sync
	uv run pre-commit install

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run ty check

test:
	uv run pytest

precommit: lint typecheck test web-lint

web-install:
	cd apps/web && npm ci

web-lint:
	cd apps/web && npm run lint

web-build:
	cd apps/web && npm run build

web-dev:
	cd apps/web && npm run dev

ci: lint typecheck test web-lint web-build

run:
	uv run vvt-api

docker-up:
	docker compose up --build

docker-down:
	docker compose down

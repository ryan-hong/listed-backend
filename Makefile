.PHONY: dev install upgrade migrate migrate-down migrate-history migrate-new

dev:
	uv run fastapi dev listed_backend/main.py

install:
	uv sync

upgrade:
	uv lock --upgrade && uv sync

migrate:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

migrate-history:
	uv run alembic history

migrate-new:
	@read -p "Migration name: " name; uv run alembic revision -m "$$name"

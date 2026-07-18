.PHONY: dev install upgrade audit migrate migrate-down migrate-history migrate-new

dev:
	uv run fastapi dev listed_backend/main.py

install:
	uv sync

upgrade:
	uv lock --upgrade && uv sync

audit:
	uv export --format requirements-txt --no-hashes --no-emit-project -o /tmp/listed-backend-requirements.txt
	uvx pip-audit --no-deps --strict -r /tmp/listed-backend-requirements.txt

migrate:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

migrate-history:
	uv run alembic history

migrate-new:
	@read -p "Migration name: " name; uv run alembic revision -m "$$name"

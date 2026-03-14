.PHONY: dev install sync upgrade

dev:
	uv run fastapi dev listed_backend/main.py

install:
	uv sync

upgrade:
	uv lock --upgrade && uv sync

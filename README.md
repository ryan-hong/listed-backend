# listed-backend

FastAPI backend for Listed. All auth flows through this service — the frontend has no direct Supabase access.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL database
- Supabase project

## Setup

1. Install dependencies:
   ```bash
   make install
   ```

2. Copy the env file and fill in your values:
   ```bash
   cp .env.development.example .env.development
   ```

   Required variables:
   ```
   DATABASE_URL=postgresql+asyncpg://...
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=...
   ```

3. Run database migrations:
   ```bash
   make migrate
   ```

4. Start the dev server:
   ```bash
   make dev
   ```

   API docs available at http://localhost:8000/docs

## Commands

| Command | Description |
|---|---|
| `make dev` | Start development server with hot reload |
| `make install` | Install dependencies |
| `make upgrade` | Upgrade all dependencies |
| `make migrate` | Apply all pending migrations |
| `make migrate-down` | Roll back the last migration |
| `make migrate-history` | Show migration history |
| `make migrate-new` | Create a new migration file (prompts for name) |

## Project Structure

```
listed_backend/
  routers/        # Route handlers
  services/       # Business logic
  models/         # SQLAlchemy ORM models
  schemas/        # Pydantic request/response schemas
  dependencies/   # FastAPI injectable dependencies
  database.py     # DB engine and session setup
  supabase_client.py
  config.py
alembic/
  versions/       # Migration files
specs/
  backend/        # Architecture decision docs
```

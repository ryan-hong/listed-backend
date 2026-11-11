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
2. Create your local env file:
  ```bash
   cp .env.example .env.development.local
   chmod 600 .env.development.local
  ```
  Fill in your values in `.env.development.local`. This file is gitignored and overrides anything in `.env.development`. If you already have a local file, add missing variables instead of overwriting it. Keep `.env.example` free of credentials.

  Required variables:
  ```
  DATABASE_URL=postgresql+asyncpg://...
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_SERVICE_ROLE_KEY=...
  ```

3. Run database migrations:
  ```bash
   make migrate
  ```
4. Start the dev server:
  ```bash
   make dev
  ```
   API docs available at [http://localhost:8000/docs](http://localhost:8000/docs)

## External API credentials

Add these values to `.env.development.local` for local development:

| Variable | Credential |
| --- | --- |
| `TMDB_READ_ACCESS_TOKEN` | TMDB API Read Access Token, without a `Bearer ` prefix |
| `GEOAPIFY_API_KEY` | Geoapify project API key, shared across its endpoints |
| `IGDB_CLIENT_ID` | Twitch application's Client ID |
| `IGDB_CLIENT_SECRET` | Twitch application's Client Secret |
| `TICKETMASTER_API_KEY` | Ticketmaster Discovery API Consumer Key |

Apple iTunes podcast search and Open Library book search require no API keys.
The provider settings default to empty values so existing backend functionality
can run before all credentials are configured. This sets up configuration only;
provider search and autofill integrations are still to be implemented. Restart
the backend after editing environment variables.

For production, store these values in the backend hosting provider's secret
manager or protected environment settings, and set `ENV=prod`. The host should
inject them into the backend process at runtime; no production env file is
required. Process environment variables override dotenv files. Local files load
after their corresponding base files (`.env.development` or `.env.production`).

Keep a backup of credentials in a password manager. Never put real credentials
in tracked files, frontend/mobile app configuration, container images, or logs.
The local env file is plaintext: Git exclusion and owner-only permissions help
protect it but do not encrypt it.

The new provider secret fields use Pydantic `SecretStr`, which masks their normal
string representation and JSON serialization. Provider clients should call
`.get_secret_value()` only when constructing authenticated requests and avoid
logging request headers or URLs containing API keys. Existing database and
Supabase settings remain plain strings; never log the entire settings object.

## Deploying to Vercel

The FastAPI entry point is configured in `pyproject.toml` as
`listed_backend.main:app`. Vercel supports the project's Python 3.14 runtime and
installs dependencies from `pyproject.toml` and `uv.lock`. Keep the framework's
default install/build settings; do not use the development server or run database
migrations in the build command.

1. Push the deployment configuration to GitHub, then import this repository as a
   new project in Vercel. Select the **FastAPI** framework preset and leave the
   root directory at the repository root.
2. Add the following under the project's **Settings > Environment Variables**,
   targeting **Production**:

   | Variable | Value |
   | --- | --- |
   | `ENV` | `prod` |
   | `DEBUG` | `false` |
   | `DATABASE_URL` | Supabase session-pooler URL, as described below |
   | `SUPABASE_URL` | Supabase project URL |
   | `SUPABASE_SERVICE_ROLE_KEY` | Backend-only Supabase service-role key |
   | Provider variables | The five credential fields listed above |
   | `SENTRY_DSN` | Optional error-reporting DSN |

   Do not paste quotation marks around dashboard values. Mark credentials as
   sensitive where available. Keep Preview credentials separate from Production;
   use a separate Supabase project for previews that need database access.
3. In Supabase, use **Connect > Session pooler** (port `5432`) for the initial
   deployment. Copy its actual host and username. Change the URL scheme to
   `postgresql+asyncpg://` and add `?ssl=require` if there is no existing query
   string. URL-encode special characters in the database password. This is the
   database password, not the Supabase service-role key.

   Session mode supports this application's existing asyncpg prepared statements
   and IPv4 connections. Do not substitute the transaction-pooler URL (port
   `6543`) without first adapting and testing the driver's prepared-statement
   configuration. Review connection pooling before scaling beyond the beta.
4. Apply any pending Alembic migrations to the intended database from a trusted
   local terminal or release workflow before deploying. Load that database's
   credentials securely into the process environment, set `ENV=prod`, then run
   `uv run alembic upgrade head`. Do not put credentials in shell command history.
   Migrations must not run on every serverless startup or preview build.
5. Deploy, then check `/` for a successful health response and `/docs` for the API
   schema. These checks alone do not verify database connectivity: also test an
   authenticated list request before pointing the mobile app at the deployment.

Use the stable production URL as the mobile app's API base URL, rather than a
single deployment's preview URL. Preview deployments may require Vercel login;
do not embed a deployment-protection bypass secret in the mobile app. The API's
own authentication remains required for private data.

Local dotenv files are excluded by `.vercelignore`. On Vercel, settings default
to `prod` even if `ENV` is omitted, and runtime secrets come from project settings.
Redeploy after changing environment variables. Native mobile requests do not
require browser CORS changes; add the exact frontend origin when a website is
introduced.

References: [Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi),
[Supabase connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres).

## Commands


| Command                | Description                                    |
| ---------------------- | ---------------------------------------------- |
| `make dev`             | Start development server with hot reload       |
| `make install`         | Install dependencies                           |
| `make upgrade`         | Upgrade all dependencies                       |
| `make migrate`         | Apply all pending migrations                   |
| `make migrate-down`    | Roll back the last migration                   |
| `make migrate-history` | Show migration history                         |
| `make migrate-new`     | Create a new migration file (prompts for name) |


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


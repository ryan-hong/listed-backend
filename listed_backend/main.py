from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI

from listed_backend.config import settings
from listed_backend.database import close_db, init_db
from listed_backend.routers import auth
from listed_backend.supabase_client import init_supabase

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url:
        init_db(settings.database_url)
    if settings.supabase_url and settings.supabase_anon_key:
        await init_supabase(settings.supabase_url, settings.supabase_anon_key)
    yield
    await close_db()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.include_router(auth.router)


@app.get("/")
async def health_check():
    return {"status": "okk"}

@app.get("/init")
async def init_check():
    return {"hello world"}
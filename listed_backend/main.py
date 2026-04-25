from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from listed_backend.config import settings
from listed_backend.database import close_db, init_db
from listed_backend.routers import auth, lists
from listed_backend.supabase_client import init_supabase

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url:
        init_db(settings.database_url)
    if settings.supabase_url and settings.supabase_service_role_key:
        await init_supabase(settings.supabase_url, settings.supabase_service_role_key)
    yield
    await close_db()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(lists.router)


@app.get("/")
async def health_check():
    return {"status": "okk"}

@app.get("/init")
async def init_check():
    return {"hello world"}
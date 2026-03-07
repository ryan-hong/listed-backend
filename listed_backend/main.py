import sentry_sdk
from fastapi import FastAPI

from listed_backend.config import settings

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn)

app = FastAPI(title=settings.app_name, debug=settings.debug)


@app.get("/")
async def health_check():
    return {"status": "okk"}

@app.get("/init")
async def init_check():
    return {"hello world"}
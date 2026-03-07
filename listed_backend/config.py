import os
from pathlib import Path

from pydantic_settings import BaseSettings

ENV_FILE_MAP = {
    "dev": ".env.development",
    "prod": ".env.production",
}

_env = os.getenv("ENV", "dev")
_env_file = Path(__file__).resolve().parent.parent / ENV_FILE_MAP.get(_env, ".env.development")


class Settings(BaseSettings):
    app_name: str = "listed"
    debug: bool = False
    env: str = _env
    sentry_dsn: str = ""

    model_config = {"env_file": str(_env_file), "env_file_encoding": "utf-8"}


settings = Settings()

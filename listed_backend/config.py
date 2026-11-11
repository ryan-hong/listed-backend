import os
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings

ENV_FILE_MAP = {
    "dev": ".env.development",
    "prod": ".env.production",
}

_env = os.getenv("ENV", "prod" if os.getenv("VERCEL") == "1" else "dev")
_base_dir = Path(__file__).resolve().parent.parent
_env_file = _base_dir / ENV_FILE_MAP.get(_env, ".env.development")
_env_local_file = _base_dir / f"{ENV_FILE_MAP.get(_env, '.env.development')}.local"


class Settings(BaseSettings):
    app_name: str = "listed"
    debug: bool = False
    env: str = _env
    sentry_dsn: str = ""
    database_url: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Optional until the corresponding provider is integrated.
    tmdb_read_access_token: SecretStr = SecretStr("")
    geoapify_api_key: SecretStr = SecretStr("")
    igdb_client_id: str = ""
    igdb_client_secret: SecretStr = SecretStr("")
    ticketmaster_api_key: SecretStr = SecretStr("")

    model_config = {
        "env_file": (str(_env_file), str(_env_local_file)),
        "env_file_encoding": "utf-8",
    }


settings = Settings()

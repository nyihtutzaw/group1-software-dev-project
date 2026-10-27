from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (see docker-compose.yml)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://crvr:crvr@localhost:5432/crvr"
    test_database_url: str = "postgresql+psycopg://crvr:crvr@localhost:5432/crvr_test"

    jwt_secret: str = "dev-only-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    session_cookie: str = "crvr_session"

    seed_demo_users: bool = True
    storage_dir: str = "/data/evidence"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

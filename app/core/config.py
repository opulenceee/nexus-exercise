"""Application configuration, loaded from environment variables.

Using pydantic-settings means config is typed and validated at startup:
if a required variable (e.g. DATABASE_URL) is missing, the app fails fast
with a clear error instead of blowing up deep in a request.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Field names map case-insensitively to env vars (database_url <- DATABASE_URL).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Nexus Coupon Marketplace"

    # Postgres connection string (SQLAlchemy URL).
    database_url: str

    # Bearer token that guards the Admin API.
    admin_api_token: str

    # Demo seeding controls.
    seed_on_start: bool = False
    seed_reseller_token: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Cached so the env is parsed once per process."""
    return Settings()

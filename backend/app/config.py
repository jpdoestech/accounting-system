"""
Application configuration.

All environment/deployment-specific values live here and load from
environment variables / .env -- never hard-coded in business logic.
This keeps the accounting and tax engines free of deployment concerns
(spec Section 2: everything important must be configurable).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Philippine Accounting System"
    environment: str = "development"
    secret_key: str = "insecure-dev-key-change-me"

    database_url: str = "sqlite:///./dev.db"

    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    algorithm: str = "HS256"

    api_v1_prefix: str = "/api/v1"

    # Comma-separated list of allowed origins for CORS, e.g.
    # "https://app.example.com,https://admin.example.com". Defaults to
    # the local Vite dev server only -- production deployments MUST
    # override this via the CORS_ORIGINS env var rather than relying
    # on a hard-coded allowlist here.
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.secret_key == "insecure-dev-key-change-me":
        raise RuntimeError(
            "SECRET_KEY is still the insecure default. Set a real, random SECRET_KEY "
            "via environment variable before running with ENVIRONMENT=production."
        )
    return settings

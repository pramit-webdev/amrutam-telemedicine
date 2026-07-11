from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://amrutam:amrutam@localhost:5432/amrutam"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = Field(
        default="dev-secret-not-for-production",
        description="JWT signing key. MUST be a strong random value in production.",
    )
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    environment: str = "development"
    log_level: str = "DEBUG"

    otel_service_name: str = "amrutam-api"
    enable_metrics: bool = True
    enable_tracing: bool = False
    otel_exporter_otlp_endpoint: str | None = None

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    rate_limit_requests_per_minute: int = 100
    rate_limit_auth_requests_per_minute: int = 10

    model_config = {"env_file": ".env", "extra": "ignore"}

    def model_post_init(self, __context):
        if self.environment == "production" and self.jwt_secret_key == "dev-secret-not-for-production":
            raise ValueError("JWT_SECRET_KEY must be set to a strong random value in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()

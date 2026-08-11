"""Application configuration — loaded from environment / .env file."""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for the FastAPI backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Postgres ---
    database_url: str = Field(
        default="postgresql+psycopg://a2a:changeme@localhost:5432/a2a_platform",
        alias="DATABASE_URL",
    )

    # --- JWT ---
    jwt_secret: str = Field(default="dev-secret-change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=10080, alias="JWT_EXPIRE_MINUTES")

    # --- API ---
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_origins: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
    )

    # --- A2A Gateway ---
    a2a_gateway_url: str = Field(
        default="http://a2a-gateway:8080",
        alias="NEXT_PUBLIC_A2A_GATEWAY_URL",
    )

    # --- Stripe ---
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_per_invocation_cents: int = Field(
        default=10, alias="STRIPE_PRICE_PER_INVOCATION_CENTS"
    )

    # --- Agent runtime ---
    agent_runtime_port_start: int = Field(default=8081, alias="AGENT_RUNTIME_PORT_START")
    docker_network: str = Field(default="a2a-platform_default", alias="DOCKER_NETWORK")

    # --- LangSmith (optional) ---
    langsmith_api_key: str = Field(default="", alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="a2a-platform", alias="LANGSMITH_PROJECT")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()

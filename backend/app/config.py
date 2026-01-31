"""Application configuration via Pydantic settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "AWS Monitor"
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/aws_monitor"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    cache_ttl: int = Field(default=300)  # 5 minutes

    # AWS
    aws_region: str = Field(default="us-east-1")
    aws_role_arn: Optional[str] = Field(default=None)
    aws_external_id: Optional[str] = Field(default=None)

    # Cognito
    cognito_user_pool_id: Optional[str] = Field(default=None)
    cognito_client_id: Optional[str] = Field(default=None)
    cognito_region: str = Field(default="us-east-1")

    # Security
    admin_override_code: Optional[str] = Field(default=None)
    protected_tags_raw: str = Field(
        default="production,prod,critical",
        validation_alias="PROTECTED_TAGS"
    )

    # CORS - use string field to avoid JSON parsing issues
    cors_origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        validation_alias="CORS_ORIGINS"
    )

    @computed_field
    @property
    def protected_tags(self) -> list[str]:
        """Parse comma-separated protected tags."""
        return [tag.strip() for tag in self.protected_tags_raw.split(",") if tag.strip()]

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

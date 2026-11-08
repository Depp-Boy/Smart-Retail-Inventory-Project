from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/postgres",
        description="PostgreSQL / Supabase connection string",
    )

    # Supabase (Optional for direct DB access, used for Auth/Storage if needed)
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    # Application
    APP_NAME: str = "Smart Retail Inventory Management System"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "replace_with_a_long_random_secret_key_at_least_32_characters"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS & Frontend
    FRONTEND_URL: str = "http://localhost:5173"
    ADDITIONAL_CORS_ORIGINS: List[str] = []

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")

    @property
    def cors_origins(self) -> List[str]:
        origins = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        }
        if self.FRONTEND_URL:
            origins.add(self.FRONTEND_URL.rstrip("/"))
        for o in self.ADDITIONAL_CORS_ORIGINS:
            if o:
                origins.add(o.rstrip("/"))
        return sorted(list(origins))

    @property
    def sqlalchemy_database_uri(self) -> str:
        """
        Ensure SQLAlchemy uses the psycopg 3 driver (postgresql+psycopg://).
        Normalizes postgresql:// or postgres:// schemes.
        """
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return url


@lru_cache()
def get_settings() -> Settings:
    return Settings()

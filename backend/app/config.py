from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://justbet:justbet_secret@localhost:5432/justbet"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """Render provides postgresql:// — convert to asyncpg driver format."""
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and "+asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # App
    APP_NAME: str = "JustBet"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Rate Limiting
    RATE_LIMIT_AUTH: int = 100
    RATE_LIMIT_ANON: int = 30

    # ── Admin Seeding (first boot) ──
    FIRST_ADMIN_PHONE: Optional[str] = None
    FIRST_ADMIN_PIN: Optional[str] = None
    ADMIN_SECRET_TOKEN: Optional[str] = None

    # ── Kenya Locale & Currency ──
    DEFAULT_CURRENCY: str = "KES"
    MIN_STAKE: int = 50
    MAX_STAKE: int = 500000
    MIN_DEPOSIT: int = 100
    MAX_DEPOSIT: int = 150000
    MIN_WITHDRAWAL: int = 100
    MAX_WITHDRAWAL: int = 70000
    MAX_SELECTIONS: int = 30
    MAX_POTENTIAL_WIN: int = 10000000

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()

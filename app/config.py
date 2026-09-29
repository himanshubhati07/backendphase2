"""Immutable, environment-backed application settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is absent or invalid."""


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigurationError(f"{name} must be configured")
    return value


def _positive_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if parsed < 1:
        raise ConfigurationError(f"{name} must be positive")
    return parsed


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    database_url: str
    jwt_secret: str
    jwt_issuer: str
    access_token_minutes: int
    refresh_token_days: int
    cors_origins: tuple[str, ...]
    log_level: str

    @classmethod
    def from_environment(cls) -> "Settings":
        origins = tuple(
            origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
        )
        return cls(
            environment=os.getenv("APP_ENV", "production"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///gym.db"),
            jwt_secret=_required("JWT_SECRET"),
            jwt_issuer=os.getenv("JWT_ISSUER", "gym-api"),
            access_token_minutes=_positive_int("JWT_ACCESS_TOKEN_MINUTES", 15),
            refresh_token_days=_positive_int("JWT_REFRESH_TOKEN_DAYS", 7),
            cors_origins=origins,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process settings. Importing this module does not read secrets."""
    return Settings.from_environment()

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


def _ttl_seconds(seconds_name: str, legacy_name: str, legacy_default: int, multiplier: int) -> int:
    """Read the seconds contract, falling back to the legacy unit-based setting."""
    if seconds_name in os.environ:
        return _positive_int(seconds_name, legacy_default * multiplier)
    return _positive_int(legacy_name, legacy_default) * multiplier


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    database_url: str
    jwt_secret: str
    jwt_issuer: str
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    cors_origins: tuple[str, ...]
    log_level: str
    host: str
    port: int

    @classmethod
    def from_environment(cls) -> "Settings":
        origins = tuple(
            origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
        )
        # The *_TTL_SECONDS names are the deployment contract. The older names
        # remain accepted so existing installations can upgrade without a flag day.
        access_ttl = _ttl_seconds("JWT_ACCESS_TTL_SECONDS", "JWT_ACCESS_TOKEN_MINUTES", 15, 60)
        refresh_ttl = _ttl_seconds("JWT_REFRESH_TTL_SECONDS", "JWT_REFRESH_TOKEN_DAYS", 7, 86400)
        environment = os.getenv("APP_ENV", "production").strip().lower()
        database_url = os.getenv("DATABASE_URL")
        # SQLite is allowed only for deliberately selected test mode. Production
        # and development must supply their database endpoint explicitly.
        if not database_url:
            if environment == "test":
                database_url = "sqlite:///:memory:"
            else:
                raise ConfigurationError("DATABASE_URL must be configured outside test mode")
        return cls(
            environment=environment,
            database_url=database_url,
            jwt_secret=_required("JWT_SECRET"),
            jwt_issuer=os.getenv("JWT_ISSUER", "gym-api"),
            access_token_ttl_seconds=access_ttl,
            refresh_token_ttl_seconds=refresh_ttl,
            cors_origins=origins,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            host=os.getenv("HOST", "0.0.0.0"),
            port=_positive_int("PORT", 8000),
        )

    @property
    def access_token_minutes(self) -> float:
        """Compatibility view for callers that previously used whole minutes."""
        return self.access_token_ttl_seconds / 60

    @property
    def refresh_token_days(self) -> float:
        """Compatibility view for callers that previously used whole days."""
        return self.refresh_token_ttl_seconds / 86400


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process settings. Importing this module does not read secrets."""
    return Settings.from_environment()

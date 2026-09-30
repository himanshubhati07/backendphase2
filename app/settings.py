from __future__ import annotations

from dataclasses import dataclass
import os
from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    host: str
    port: int
    database_url: str
    api_keys: tuple[str, ...]
    kafka_bootstrap_servers: str
    kafka_client_id: str
    kafka_topic: str
    log_level: str
    flask_secret_key: str

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        def required(name: str) -> str:
            value = os.getenv(name, "").strip()
            if not value:
                raise RuntimeError(f"{name} must be configured")
            return value
        keys = tuple(key.strip() for key in required("API_KEYS").split(",") if key.strip())
        if not keys:
            raise RuntimeError("API_KEYS must contain at least one key")
        return cls(required("APP_ENV"), os.getenv("HOST", "0.0.0.0"), int(os.getenv("PORT", "8000")), required("DATABASE_URL"), keys, required("KAFKA_BOOTSTRAP_SERVERS"), required("KAFKA_CLIENT_ID"), required("KAFKA_TOPIC"), os.getenv("LOG_LEVEL", "INFO"), required("FLASK_SECRET_KEY"))

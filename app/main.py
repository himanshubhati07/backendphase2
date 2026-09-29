"""Bottle application factory and production WSGI entry point."""
from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from bottle import Bottle, request, response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings, get_settings
from .database import create_database_engine, create_session_factory
from .errors import AppError, ConflictError, DatabaseError, register_error_handlers
from .openapi import build_openapi_document
from .responses import error, success
from .routes_attendance import register_attendance_routes
from .routes_auth import register_auth_routes
from .routes_members import register_member_routes
from .routes_memberships import register_membership_routes
from .routes_payments import register_payment_routes
from .routes_plans import register_plan_routes
from .routes_trainers import register_trainer_routes
from .routes_workouts import register_workout_routes


class JsonFormatter(logging.Formatter):
    """Conservative request logging: never serialize request bodies or headers."""
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
                           "logger": record.name, "message": record.getMessage()}, separators=(",", ":"))


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    root.setLevel(level)


class SafeErrorPlugin:
    """Convert expected and SQLAlchemy exceptions into safe JSON responses."""
    name = "safe-error-plugin"
    api = 2

    def apply(self, callback: Callable[..., Any], _: Any) -> Callable[..., Any]:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            try:
                return callback(*args, **kwargs)
            except AppError as exc:
                return error(exc.message, exc.error_code, exc.status)
            except IntegrityError as exc:
                session = request.environ.get("gym.db")
                if isinstance(session, Session):
                    session.rollback()
                logging.getLogger(__name__).warning(
                    "database_error_redacted request_id=%s", request.environ.get("gym.request_id", "unknown")
                )
                safe_error = ConflictError()
                return error(safe_error.message, safe_error.error_code, safe_error.status)
            except SQLAlchemyError as exc:
                session = request.environ.get("gym.db")
                if isinstance(session, Session):
                    session.rollback()
                # Driver messages can include SQL, connection details, and values;
                # do not attach the exception or traceback to operational logs.
                logging.getLogger(__name__).warning(
                    "database_error_redacted request_id=%s", request.environ.get("gym.request_id", "unknown")
                )
                safe_error = DatabaseError()
                return error(safe_error.message, safe_error.error_code, safe_error.status)
        return wrapped


def _openapi_document() -> dict[str, Any]:
    return build_openapi_document()


def create_app(settings: Settings | None = None) -> Bottle:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = create_database_engine(settings.database_url)
    session_factory: sessionmaker[Session] = create_session_factory(engine)
    app = Bottle()
    app.config.update(settings=settings, engine=engine, session_factory=session_factory)
    app.config["openapi_paths"] = _openapi_document()["paths"]
    app.install(SafeErrorPlugin())

    @app.hook("before_request")
    def open_session() -> None:
        request.environ["gym.request_id"] = uuid.uuid4().hex
        request.environ["gym.db"] = session_factory()

    @app.hook("after_request")
    def close_session_and_secure_response() -> None:
        session = request.environ.pop("gym.db", None)
        if isinstance(session, Session):
            session.close()
        origin = request.get_header("Origin")
        if origin and origin in settings.cors_origins:
            response.set_header("Access-Control-Allow-Origin", origin)
            response.set_header("Vary", "Origin")
            response.set_header("Access-Control-Allow-Credentials", "true")
        response.set_header("X-Content-Type-Options", "nosniff")
        response.set_header("X-Frame-Options", "DENY")
        response.set_header("Referrer-Policy", "no-referrer")
        response.set_header("Cache-Control", "no-store")
        logging.getLogger("gym.request").info("request_complete method=%s path=%s status=%s request_id=%s", request.method, request.path, response.status_code, request.environ.get("gym.request_id"))

    @app.route("/<path:re:.*>", method="OPTIONS")
    def options(path: str) -> Any:
        response.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        response.set_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        return ""

    @app.get("/health")
    @app.get("/api/health")
    def health() -> Any:
        return success({"status": "healthy"}, "Service healthy")

    @app.get("/api/openapi.json")
    def openapi() -> Any:
        document = _openapi_document()
        document["paths"] = app.config["openapi_paths"]
        return success(document, "OpenAPI document")

    register_auth_routes(app)
    register_member_routes(app)
    register_trainer_routes(app)
    register_plan_routes(app)
    register_membership_routes(app)
    register_attendance_routes(app)
    register_payment_routes(app)
    register_workout_routes(app)
    register_error_handlers(app)
    return app


# Gunicorn imports ``app.main:create_app()``. Do not start Bottle's development
# server here; production invocation belongs to the Gunicorn/start.sh command.
if __name__ == "__main__":
    raise SystemExit("Run with Gunicorn, for example: gunicorn 'app.main:create_app()'")

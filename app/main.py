"""Bottle application factory and WSGI entry point."""
from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from bottle import Bottle, request, response, run
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings, get_settings
from .database import create_database_engine, create_session_factory
from .errors import AppError, register_error_handlers
from .responses import error, success
from .routes_attendance import register_attendance_routes
from .routes_auth import register_auth_routes
from .routes_members import register_member_routes
from .routes_trainers import register_trainer_routes
from .routes_memberships import register_membership_routes
from .routes_plans import register_plan_routes
from .routes_payments import register_payment_routes
from .routes_workouts import register_workout_routes


class JsonFormatter(logging.Formatter):
    """A conservative formatter that never serializes request bodies or headers."""
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }, separators=(",", ":"))


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    root.setLevel(level)


class SafeErrorPlugin:
    name = "safe-error-plugin"
    api = 2

    def apply(self, callback: Callable[..., Any], _: Any) -> Callable[..., Any]:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            try:
                return callback(*args, **kwargs)
            except AppError as exc:
                return error(exc.message, exc.error_code, exc.status)
            except IntegrityError:
                session = request.environ.get("gym.db")
                if isinstance(session, Session):
                    session.rollback()
                logging.getLogger(__name__).warning("database_integrity_error")
                return error("Request conflicts with existing data", "CONFLICT", 409)
        return wrapped


def _openapi_document() -> dict[str, Any]:
    return {
        "openapi": "3.0.3",
        "info": {"title": "Gym API", "version": "1.0.0"},
        "paths": {
            "/health": {"get": {"summary": "Health check", "responses": {"200": {"description": "Service healthy"}}}},
            "/api/auth/register": {"post": {"summary": "Register a member or trainer", "responses": {"201": {"description": "Registered"}}}},
            "/api/auth/login": {"post": {"summary": "Log in", "responses": {"200": {"description": "Authenticated"}}}},
            "/api/auth/refresh": {"post": {"summary": "Exchange a refresh token", "responses": {"200": {"description": "Refreshed"}}}},
            "/api/auth/me": {"get": {"summary": "Current user", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "Current user"}}}},
            "/api/payments": {"post": {"summary": "Create a payment record", "security": [{"bearerAuth": []}]}, "get": {"summary": "List visible payments", "security": [{"bearerAuth": []}]}},
            "/api/payments/{payment_id}": {"get": {"summary": "Get a payment", "security": [{"bearerAuth": []}]}},
            "/api/payments/{payment_id}/status": {"patch": {"summary": "Update payment status", "security": [{"bearerAuth": []}]}},
            "/api/members/{member_id}/payments": {"get": {"summary": "Get member payment history", "security": [{"bearerAuth": []}]}},
            "/api/workout-plans": {"post": {"summary": "Create a workout plan", "security": [{"bearerAuth": []}]}},
            "/api/workout-plans/{workout_plan_id}": {"put": {"summary": "Update a workout plan", "security": [{"bearerAuth": []}]}, "delete": {"summary": "Deactivate a workout plan", "security": [{"bearerAuth": []}]}},
            "/api/workout-plans/{workout_plan_id}/members/{member_id}": {"put": {"summary": "Assign a workout plan", "security": [{"bearerAuth": []}]}},
            "/api/members/{member_id}/workout-plans": {"get": {"summary": "Get member workout plans", "security": [{"bearerAuth": []}]}},
        },
        "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}},
    }


def create_app(settings: Settings | None = None) -> Bottle:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = create_database_engine(settings.database_url)
    session_factory: sessionmaker[Session] = create_session_factory(engine)
    app = Bottle()
    app.config["settings"] = settings
    app.config["engine"] = engine
    app.config["session_factory"] = session_factory
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


if __name__ == "__main__":
    app = create_app()
    run(app=app, host="0.0.0.0", port=8000, reloader=False)

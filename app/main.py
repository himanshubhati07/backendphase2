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
    """Return a compact but complete OpenAPI 3 document for public API discovery."""
    public = {
        "/health": {"get": "Health check"}, "/api/health": {"get": "API health check"},
        "/api/openapi.json": {"get": "OpenAPI document"},
        "/api/auth/register": {"post": "Register a member or trainer"},
        "/api/auth/login": {"post": "Authenticate and issue tokens"},
        "/api/auth/refresh": {"post": "Exchange a refresh token"},
    }
    protected = {
        "/api/auth/me": {"get": "Get current identity"},
        "/api/members": {"post": "Create member", "get": "List/search members"},
        "/api/members/{member_id}": {"get": "Get member", "put": "Update member", "delete": "Deactivate member"},
        "/api/trainers": {"post": "Create trainer", "get": "List trainers"},
        "/api/trainers/{trainer_id}": {"get": "Get trainer", "put": "Update trainer", "delete": "Deactivate trainer"},
        "/api/trainers/{trainer_id}/members/{member_id}": {"put": "Assign trainer to member"},
        "/api/membership-plans": {"post": "Create membership plan", "get": "List membership plans"},
        "/api/membership-plans/{plan_id}": {"get": "Get membership plan", "put": "Update membership plan", "delete": "Deactivate membership plan"},
        "/api/members/{member_id}/memberships": {"post": "Assign membership", "get": "Get membership history"},
        "/api/members/{member_id}/memberships/active": {"get": "Get active membership"},
        "/api/memberships/{membership_id}/renew": {"post": "Renew membership"},
        "/api/memberships/{membership_id}/cancel": {"post": "Cancel membership"},
        "/api/attendance/check-in": {"post": "Check in a member"},
        "/api/attendance/check-out": {"post": "Check out a member"},
        "/api/members/{member_id}/attendance": {"get": "Get attendance history"},
        "/api/attendance/daily": {"get": "Get daily attendance"},
        "/api/attendance": {"get": "Get attendance date range"},
        "/api/payments": {"post": "Create payment", "get": "List payments"},
        "/api/payments/{payment_id}": {"get": "Get payment"},
        "/api/payments/{payment_id}/status": {"patch": "Update payment status"},
        "/api/members/{member_id}/payments": {"get": "Get payment history"},
        "/api/workout-plans": {"post": "Create workout plan"},
        "/api/workout-plans/{workout_plan_id}": {"put": "Update workout plan", "delete": "Deactivate workout plan"},
        "/api/workout-plans/{workout_plan_id}/members/{member_id}": {"put": "Assign workout plan"},
        "/api/members/{member_id}/workout-plans": {"get": "Get member workout plans"},
    }
    response_schema = {"type": "object", "required": ["success", "message"], "properties": {"success": {"type": "boolean"}, "message": {"type": "string"}, "data": {"nullable": True}}}
    error_schema = {"type": "object", "required": ["success", "message", "error_code"], "properties": {"success": {"type": "boolean", "example": False}, "message": {"type": "string"}, "error_code": {"type": "string"}}}
    paths: dict[str, Any] = {}
    for path, methods in public.items():
        paths[path] = {method: {"summary": summary, "responses": {"200": {"description": "Success", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Success"}}}}, "422": {"$ref": "#/components/responses/Error"}}} for method, summary in methods.items()}
    for path, methods in protected.items():
        parameters = [{"name": name, "in": "path", "required": True, "schema": {"type": "integer"}} for name in ("member_id", "trainer_id", "plan_id", "membership_id", "payment_id", "workout_plan_id") if "{" + name + "}" in path]
        paths[path] = {method: {"summary": summary, "security": [{"bearerAuth": []}], "parameters": parameters, "requestBody": {"required": method in {"post", "put", "patch"}, "content": {"application/json": {"schema": {"type": "object"}}}}, "responses": {"200": {"description": "Success", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Success"}}}}, "201": {"description": "Created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Success"}}}}, "401": {"$ref": "#/components/responses/Error"}, "403": {"$ref": "#/components/responses/Error"}, "404": {"$ref": "#/components/responses/Error"}, "409": {"$ref": "#/components/responses/Error"}, "422": {"$ref": "#/components/responses/Error"}}} for method, summary in methods.items()}
    return {"openapi": "3.0.3", "info": {"title": "Gym Management REST API", "version": "1.0.0"}, "paths": paths, "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}, "schemas": {"Success": response_schema, "Error": error_schema}, "responses": {"Error": {"description": "Safe API error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}}}}


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

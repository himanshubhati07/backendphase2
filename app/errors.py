"""Safe application errors and Bottle error registration."""
from __future__ import annotations

import logging
from typing import Any

from bottle import Bottle, HTTPError, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .responses import error

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, message: str, error_code: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status = status


class NotFoundError(AppError):
    """A requested resource does not exist (or is deliberately undisclosed)."""
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, "NOT_FOUND", 404)


class ConflictError(AppError):
    """The requested change conflicts with existing state."""
    def __init__(self, message: str = "Request conflicts with existing data") -> None:
        super().__init__(message, "CONFLICT", 409)


class DatabaseError(AppError):
    """A deliberately non-leaking response for unexpected database failures."""
    def __init__(self) -> None:
        super().__init__("A database error occurred", "DATABASE_ERROR", 500)


class ValidationError(AppError):
    def __init__(self, message: str = "Invalid request") -> None:
        super().__init__(message, "VALIDATION_ERROR", 422)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, "UNAUTHENTICATED", 401)


class AuthorizationError(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action") -> None:
        super().__init__(message, "FORBIDDEN", 403)


def register_error_handlers(app: Bottle) -> None:
    @app.error(400)
    def bad_request(_: HTTPError) -> Any:
        return error("Malformed request", "BAD_REQUEST", 400)

    @app.error(404)
    def not_found(_: HTTPError) -> Any:
        return error("Resource not found", "NOT_FOUND", 404)

    @app.error(405)
    def method_not_allowed(_: HTTPError) -> Any:
        return error("Method not allowed", "METHOD_NOT_ALLOWED", 405)

    @app.error(500)
    def internal_error(err: HTTPError) -> Any:
        original = err.exception
        # Normally AppError is converted by SafeErrorPlugin. Keep this fallback for
        # exceptions raised before/without the plugin (for example a Bottle hook).
        if isinstance(original, AppError):
            return error(original.message, original.error_code, original.status)
        if isinstance(original, IntegrityError):
            logger.warning("database_error_redacted request_id=%s", request.environ.get("gym.request_id", "unknown"))
            safe_error = ConflictError()
            return error(safe_error.message, safe_error.error_code, safe_error.status)
        if isinstance(original, SQLAlchemyError):
            logger.warning("database_error_redacted request_id=%s", request.environ.get("gym.request_id", "unknown"))
            safe_error = DatabaseError()
            return error(safe_error.message, safe_error.error_code, safe_error.status)
        # Do not attach exception objects/traces: locals in an unexpected failure
        # can contain request credentials, SQL values, or payment data.
        logger.error("unhandled_request_error_redacted request_id=%s", request.environ.get("gym.request_id", "unknown"))
        return error("An unexpected error occurred", "INTERNAL_ERROR", 500)

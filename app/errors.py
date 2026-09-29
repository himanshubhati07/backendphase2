"""Safe application errors and Bottle error registration."""
from __future__ import annotations

import logging
from typing import Any

from bottle import Bottle, HTTPError

from .responses import error

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, message: str, error_code: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status = status


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
        if isinstance(original, AppError):
            return error(original.message, original.error_code, original.status)
        logger.exception("unhandled_request_error", exc_info=original)
        return error("An unexpected error occurred", "INTERNAL_ERROR", 500)

"""Domain errors and centralized client-safe error translation."""
import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import Error as DatabaseError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base domain error with a safe public message."""
    status_code = 400
    error_code = "application_error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or "The request could not be completed."
        super().__init__(self.message)


class NotFoundError(ApplicationError):
    status_code = 404
    error_code = "not_found"


class ConflictError(ApplicationError):
    status_code = 409
    error_code = "conflict"


class AuthenticationError(ApplicationError):
    status_code = 401
    error_code = "authentication_error"


class ForbiddenError(ApplicationError):
    status_code = 403
    error_code = "forbidden"


def _correlation_id(request: Request) -> str:
    return request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID") or str(uuid4())


def _error_response(request: Request, status_code: int, code: str, message: str, details: object | None = None) -> JSONResponse:
    correlation_id = _correlation_id(request)
    payload: dict[str, object] = {
        "success": False, "message": message, "error_code": code,
        "timestamp": datetime.now(UTC).isoformat(), "correlation_id": correlation_id,
    }
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Install one error translation boundary for API and browser requests."""
    @app.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, error: ApplicationError) -> JSONResponse:
        logger.warning("request_failed correlation_id=%s code=%s", _correlation_id(request), error.error_code)
        response = _error_response(request, error.status_code, error.error_code, error.message)
        if error.status_code == 401:
            response.headers["WWW-Authenticate"] = "Bearer"
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        logger.warning("validation_failed correlation_id=%s", _correlation_id(request))
        return _error_response(request, 422, "validation_error", "Request validation failed.", error.errors())

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        message = error.detail if isinstance(error.detail, str) else "Request failed."
        return _error_response(request, error.status_code, "http_error", message)

    @app.exception_handler(DatabaseError)
    async def handle_database_error(request: Request, error: DatabaseError) -> JSONResponse:
        logger.error("database_failed correlation_id=%s", _correlation_id(request), exc_info=True)
        return _error_response(request, 500, "database_error", "A database error occurred.")

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error("unexpected_failure correlation_id=%s", _correlation_id(request), exc_info=True)
        return _error_response(request, 500, "internal_error", "An unexpected error occurred.")

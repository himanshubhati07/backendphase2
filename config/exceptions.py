"""Domain exceptions and the centralized DRF exception adapter."""
from __future__ import annotations

import logging
from typing import Any

from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed, NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class Conflict(APIException):
    """Signals a state conflict such as a duplicate favorite."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with current resource state."
    default_code = "conflict"


def _details(data: Any) -> Any:
    """Return safe validation details without framework-specific internals."""
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return data
    return None


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """Convert DRF and unexpected exceptions to the documented error envelope."""
    response = exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", "unknown")
    timestamp = timezone.now().isoformat()
    if response is None:
        logger.exception("Unhandled API exception request_id=%s", request_id, exc_info=exc)
        return Response(
            {"success": False, "message": "An unexpected error occurred.", "error_code": "internal_error", "details": None, "timestamp": timestamp, "request_id": request_id},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = "request_error"
    message = "The request could not be completed."
    if isinstance(exc, ValidationError):
        code, message = "validation_error", "Request validation failed."
    elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        code, message = "authentication_failed", "Authentication credentials were not provided or are invalid."
    elif isinstance(exc, PermissionDenied):
        code, message = "permission_denied", "You do not have permission to perform this action."
    elif isinstance(exc, Http404):
        code, message = "not_found", "The requested resource was not found."
    elif isinstance(exc, Conflict):
        code, message = "conflict", str(exc.detail)
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        code, message = "not_found", "The requested resource was not found."
    response.data = {"success": False, "message": message, "error_code": code, "details": _details(response.data), "timestamp": timestamp, "request_id": request_id}
    return response

"""Request correlation middleware."""
from __future__ import annotations

import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse


class CorrelationIdMiddleware:
    """Attach a caller-provided or generated identifier to each request."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        response = self._get_response(request)
        response["X-Request-ID"] = request.request_id
        return response

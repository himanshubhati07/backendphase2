"""Shared API response envelope helpers."""
from __future__ import annotations

from typing import Any

from rest_framework.response import Response


def success_response(data: Any = None, message: str = "OK.", status_code: int = 200) -> Response:
    """Build the standard successful API response envelope."""
    return Response({"success": True, "message": message, "data": data}, status=status_code)

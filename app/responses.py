"""Canonical API response envelopes."""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from bottle import HTTPResponse


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _response(payload: dict[str, Any], status: int) -> HTTPResponse:
    return HTTPResponse(
        status=status,
        body=json.dumps(payload, default=_json_default, separators=(",", ":")),
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )


def success(data: Any, message: str = "OK", status: int = 200) -> HTTPResponse:
    return _response({"success": True, "message": message, "data": data}, status)


def error(message: str, error_code: str, status: int) -> HTTPResponse:
    return _response({"success": False, "message": message, "error_code": error_code}, status)

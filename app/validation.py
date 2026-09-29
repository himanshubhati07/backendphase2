"""Small shared JSON request validation helpers."""
from __future__ import annotations

from typing import Any

from bottle import request

from .errors import ValidationError


def json_body() -> dict[str, Any]:
    body = request.json
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")
    return body


def required_string(body: dict[str, Any], field: str, *, min_length: int = 1, max_length: int = 255) -> str:
    value = body.get(field)
    if not isinstance(value, str) or not (min_length <= len(value.strip()) <= max_length):
        raise ValidationError(f"{field} must be a string between {min_length} and {max_length} characters")
    return value.strip()


def optional_string(body: dict[str, Any], field: str, *, max_length: int = 255) -> str | None:
    value = body.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or len(value.strip()) > max_length:
        raise ValidationError(f"{field} must be a string up to {max_length} characters")
    return value.strip() or None

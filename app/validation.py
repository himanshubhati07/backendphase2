from __future__ import annotations

from datetime import date
from typing import Any, Mapping
from uuid import UUID
from flask import Request, request
from app.errors import ValidationError


def require_json_object() -> dict[str, Any]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")
    return data


def require_uuid(value: str | None, field: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValidationError(f"{field} must be a UUID") from exc


def required_string(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} is required")
    return value.strip()


def optional_string(payload: Mapping[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    return value.strip() or None


def optional_date(payload: Mapping[str, Any], field: str) -> date | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO date") from exc


def reject_unknown_fields(payload: Mapping[str, Any], allowed: frozenset[str]) -> None:
    unknown = set(payload) - allowed
    if unknown:
        raise ValidationError("Unknown fields", {"fields": sorted(unknown)})


def parse_pagination(args: Mapping[str, str]) -> tuple[int, int]:
    try:
        page, per_page = int(args.get("page", "1")), int(args.get("per_page", "20"))
    except ValueError as exc:
        raise ValidationError("page and per_page must be integers") from exc
    if page < 1 or not 1 <= per_page <= 100:
        raise ValidationError("page must be positive and per_page must be between 1 and 100")
    return page, per_page

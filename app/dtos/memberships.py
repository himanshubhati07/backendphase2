"""DTO shaping for membership API responses."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


def _json_value(value: Any) -> Any:
    if isinstance(value, (UUID, date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        # Prices are represented as JSON numbers at the HTTP boundary.
        return float(value)
    return value


def membership_plan_dto(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in row.items()}


def membership_dto(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in row.items()}

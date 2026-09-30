"""JSON serialization helpers for the member resource."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping
from uuid import UUID

_MEMBER_FIELDS = (
    "id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "date_of_birth",
    "created_at",
    "updated_at",
)


def member_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return the public, JSON-ready representation of a member database row."""
    member: dict[str, Any] = {}
    for field in _MEMBER_FIELDS:
        value = row[field]
        if isinstance(value, UUID):
            member[field] = str(value)
        elif isinstance(value, (date, datetime)):
            member[field] = value.isoformat()
        else:
            member[field] = value
    return member

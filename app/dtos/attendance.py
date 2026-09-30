"""DTOs used by the attendance resource.

They deliberately contain only JSON-compatible primitives at the controller
boundary.  The service accepts UUID instances or their string form.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


@dataclass(frozen=True, slots=True)
class AttendanceDTO:
    id: UUID
    member_id: UUID
    checked_in_at: datetime
    checked_out_at: datetime | None

    @classmethod
    def from_row(cls, row: Any) -> "AttendanceDTO":
        # psycopg's dict_row is the normal production row factory, while the
        # tuple fallback keeps this repository usable with a simple test fake.
        if isinstance(row, dict):
            return cls(
                id=row["id"],
                member_id=row["member_id"],
                checked_in_at=row["checked_in_at"],
                checked_out_at=row["checked_out_at"],
            )
        return cls(*row)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": str(self.id),
            "member_id": str(self.member_id),
            "checked_in_at": _iso(self.checked_in_at),
            "checked_out_at": _iso(self.checked_out_at),
        }

"""JSON-facing DTO for trainer records returned by psycopg."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TrainerDTO:
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    specialization: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: Any) -> "TrainerDTO":
        if isinstance(row, dict):
            return cls(**{field: row[field] for field in cls.__dataclass_fields__})
        return cls(*row)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": str(self.id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "specialization": self.specialization,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

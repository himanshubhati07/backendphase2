"""Parameterized PostgreSQL persistence for trainer profiles.

The caller owns the connection and transaction boundary.  This keeps repository
methods composable and makes every statement straightforward to exercise with a
psycopg connection or a focused test double.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.dtos.trainers import TrainerDTO


class TrainerRepository:
    """Persistence operations for the ``trainers`` table."""

    _COLUMNS = "id, first_name, last_name, email, phone, specialization, created_at, updated_at"

    @staticmethod
    def _one(cursor: Any) -> TrainerDTO | None:
        row = cursor.fetchone()
        return TrainerDTO.from_row(row) if row is not None else None

    def create(self, connection: Any, *, trainer_id: UUID, data: dict[str, Any]) -> TrainerDTO:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO trainers (id, first_name, last_name, email, phone, specialization)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING {self._COLUMNS}
                """,
                (
                    trainer_id,
                    data["first_name"],
                    data["last_name"],
                    data["email"],
                    data.get("phone"),
                    data.get("specialization"),
                ),
            )
            trainer = self._one(cursor)
        assert trainer is not None
        return trainer

    def get(self, connection: Any, trainer_id: UUID) -> TrainerDTO | None:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT {self._COLUMNS} FROM trainers WHERE id = %s", (trainer_id,))
            return self._one(cursor)

    def update(self, connection: Any, trainer_id: UUID, *, data: dict[str, Any]) -> TrainerDTO | None:
        # Field names are selected from a closed allow-list, never request input.
        fields = tuple(name for name in ("first_name", "last_name", "email", "phone", "specialization") if name in data)
        if not fields:
            return self.get(connection, trainer_id)
        assignments = ", ".join(f"{field} = %s" for field in fields)
        values = [data[field] for field in fields]
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE trainers
                SET {assignments}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING {self._COLUMNS}
                """,
                (*values, trainer_id),
            )
            return self._one(cursor)

    def delete(self, connection: Any, trainer_id: UUID) -> bool:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM trainers WHERE id = %s", (trainer_id,))
            return cursor.rowcount == 1

    def list(self, connection: Any, *, page: int, per_page: int) -> tuple[list[TrainerDTO], int]:
        offset = (page - 1) * per_page
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM trainers")
            total = cursor.fetchone()[0]
            cursor.execute(
                f"""
                SELECT {self._COLUMNS}
                FROM trainers
                ORDER BY first_name ASC, last_name ASC, id ASC
                LIMIT %s OFFSET %s
                """,
                (per_page, offset),
            )
            return [TrainerDTO.from_row(row) for row in cursor.fetchall()], total

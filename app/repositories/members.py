"""Direct PostgreSQL persistence operations for gym members."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.dtos.members import member_to_dict


class MemberRepository:
    """Persistence gateway for the ``members`` table.

    Connections are deliberately supplied by callers.  This makes a service's
    transaction boundary explicit and prevents repository methods from
    independently committing work that is coupled to an event publication.
    """

    _RETURNING = """
        id, first_name, last_name, email, phone, date_of_birth, created_at, updated_at
    """
    _MUTABLE_COLUMNS = frozenset({"first_name", "last_name", "email", "phone", "date_of_birth"})

    def create(self, connection: Any, data: Mapping[str, Any]) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO members (id, first_name, last_name, email, phone, date_of_birth)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s)
                RETURNING {self._RETURNING}
                """,
                (
                    data["first_name"],
                    data["last_name"],
                    data["email"],
                    data.get("phone"),
                    data.get("date_of_birth"),
                ),
            )
            row = cursor.fetchone()
        return member_to_dict(row)

    def get(self, connection: Any, member_id: UUID | str) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {self._RETURNING} FROM members WHERE id = %s",
                (member_id,),
            )
            row = cursor.fetchone()
        return member_to_dict(row) if row is not None else None

    def update(
        self, connection: Any, member_id: UUID | str, data: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        # Identifiers cannot be parameterized, so they are checked against a
        # local allow-list before being interpolated into this static statement.
        fields = tuple(data.keys())
        if not fields or set(fields) - self._MUTABLE_COLUMNS:
            raise ValueError("Invalid member update fields")
        assignments = ", ".join(f"{field} = %s" for field in fields)
        values = tuple(data[field] for field in fields) + (member_id,)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE members
                SET {assignments}, updated_at = NOW()
                WHERE id = %s
                RETURNING {self._RETURNING}
                """,
                values,
            )
            row = cursor.fetchone()
        return member_to_dict(row) if row is not None else None

    def delete(self, connection: Any, member_id: UUID | str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM members WHERE id = %s", (member_id,))
            return cursor.rowcount == 1

    def list(
        self, connection: Any, page: int, per_page: int
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * per_page
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM members")
            count_row = cursor.fetchone()
            cursor.execute(
                f"""
                SELECT {self._RETURNING}
                FROM members
                ORDER BY first_name ASC, last_name ASC, id ASC
                LIMIT %s OFFSET %s
                """,
                (per_page, offset),
            )
            rows = cursor.fetchall()
        return [member_to_dict(row) for row in rows], int(count_row["total"])

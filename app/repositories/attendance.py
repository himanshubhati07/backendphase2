"""PostgreSQL persistence for attendance.

The repository deliberately holds no connection.  Every operation receives the
active caller-owned transaction connection, so it can never accidentally reuse
a connection that a transaction manager has already closed.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.dtos.attendance import AttendanceDTO


class AttendanceRepository:
    @staticmethod
    def _one(cursor: Any) -> AttendanceDTO | None:
        row = cursor.fetchone()
        return AttendanceDTO.from_row(row) if row is not None else None

    def member_exists(self, connection: Any, member_id: UUID) -> bool:
        """Lock the member key until this caller's transaction completes."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM members WHERE id = %s FOR KEY SHARE",
                (member_id,),
            )
            return cursor.fetchone() is not None

    def check_in(self, connection: Any, member_id: UUID) -> AttendanceDTO:
        # The partial unique index on member_id WHERE checked_out_at IS NULL is
        # the authority that prevents concurrent open attendances.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO attendance (member_id, checked_in_at)
                VALUES (%s, CURRENT_TIMESTAMP)
                RETURNING id, member_id, checked_in_at, checked_out_at
                """,
                (member_id,),
            )
            attendance = self._one(cursor)
        assert attendance is not None
        return attendance

    def get(self, connection: Any, attendance_id: UUID) -> AttendanceDTO | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, member_id, checked_in_at, checked_out_at
                   FROM attendance WHERE id = %s""",
                (attendance_id,),
            )
            return self._one(cursor)

    def check_out(self, connection: Any, attendance_id: UUID) -> AttendanceDTO | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE attendance
                SET checked_out_at = CURRENT_TIMESTAMP
                WHERE id = %s AND checked_out_at IS NULL
                RETURNING id, member_id, checked_in_at, checked_out_at
                """,
                (attendance_id,),
            )
            return self._one(cursor)

    def list_for_member(
        self, connection: Any, member_id: UUID, *, page: int, per_page: int,
        checked_in_on: date | None = None,
    ) -> tuple[list[AttendanceDTO], int]:
        return self._list(
            connection, member_id=member_id, page=page, per_page=per_page,
            checked_in_on=checked_in_on,
        )

    def list(
        self, connection: Any, *, page: int, per_page: int,
        member_id: UUID | None = None, checked_in_on: date | None = None,
    ) -> tuple[list[AttendanceDTO], int]:
        return self._list(
            connection, member_id=member_id, page=page, per_page=per_page,
            checked_in_on=checked_in_on,
        )

    def _list(
        self, connection: Any, *, member_id: UUID | None, page: int,
        per_page: int, checked_in_on: date | None,
    ) -> tuple[list[AttendanceDTO], int]:
        where: list[str] = []
        params: list[Any] = []
        if member_id is not None:
            where.append("member_id = %s")
            params.append(member_id)
        if checked_in_on is not None:
            # PostgreSQL's configured session timezone defines the local date,
            # matching the existing expression index on checked_in_at::date.
            where.append("checked_in_at::date = %s")
            params.append(checked_in_on)
        clause = " WHERE " + " AND ".join(where) if where else ""
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM attendance" + clause, tuple(params))
            total = cursor.fetchone()[0]
            cursor.execute(
                """SELECT id, member_id, checked_in_at, checked_out_at
                   FROM attendance""" + clause +
                " ORDER BY checked_in_at DESC, id DESC LIMIT %s OFFSET %s",
                tuple(params + [per_page, (page - 1) * per_page]),
            )
            return [AttendanceDTO.from_row(row) for row in cursor.fetchall()], int(total)

"""PostgreSQL persistence for attendance.

All values are supplied as psycopg parameters; timestamps are intentionally
made by PostgreSQL so the API does not depend on an application-server clock.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.dtos.attendance import AttendanceDTO


class AttendanceRepository:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    @staticmethod
    def _one(cursor: Any) -> AttendanceDTO | None:
        row = cursor.fetchone()
        return AttendanceDTO.from_row(row) if row is not None else None

    def check_in(self, member_id: UUID) -> AttendanceDTO:
        # The partial unique index on member_id WHERE checked_out_at IS NULL is
        # the authority that prevents two simultaneous open attendances.
        with self._connection.cursor() as cursor:
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

    def get(self, attendance_id: UUID) -> AttendanceDTO | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, member_id, checked_in_at, checked_out_at
                FROM attendance WHERE id = %s
                """,
                (attendance_id,),
            )
            return self._one(cursor)

    def check_out(self, attendance_id: UUID) -> AttendanceDTO | None:
        with self._connection.cursor() as cursor:
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
        self, member_id: UUID, *, page: int, per_page: int,
        checked_in_from: date | None = None, checked_in_to: date | None = None,
    ) -> tuple[list[AttendanceDTO], int]:
        return self._list(
            member_id=member_id,
            page=page,
            per_page=per_page,
            checked_in_from=checked_in_from,
            checked_in_to=checked_in_to,
        )

    def list(
        self, *, page: int, per_page: int, member_id: UUID | None = None,
        checked_in_from: date | None = None, checked_in_to: date | None = None,
    ) -> tuple[list[AttendanceDTO], int]:
        return self._list(
            member_id=member_id,
            page=page,
            per_page=per_page,
            checked_in_from=checked_in_from,
            checked_in_to=checked_in_to,
        )

    def _list(self, *, member_id: UUID | None, page: int, per_page: int,
              checked_in_from: date | None, checked_in_to: date | None) -> tuple[list[AttendanceDTO], int]:
        where: list[str] = []
        params: list[Any] = []
        if member_id is not None:
            where.append("member_id = %s")
            params.append(member_id)
        if checked_in_from is not None:
            where.append("checked_in_at >= %s")
            params.append(checked_in_from)
        if checked_in_to is not None:
            # An exclusive upper bound includes the whole supplied calendar day.
            where.append("checked_in_at < (%s::date + INTERVAL '1 day')")
            params.append(checked_in_to)
        clause = " WHERE " + " AND ".join(where) if where else ""
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM attendance" + clause, tuple(params))
            total = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT id, member_id, checked_in_at, checked_out_at
                FROM attendance""" + clause + " ORDER BY checked_in_at DESC, id DESC LIMIT %s OFFSET %s",
                tuple(params + [per_page, (page - 1) * per_page]),
            )
            return [AttendanceDTO.from_row(row) for row in cursor.fetchall()], total

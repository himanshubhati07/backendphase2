"""Attendance application service and resource-level errors."""
from __future__ import annotations

from contextlib import nullcontext
from datetime import date
from typing import Any
from uuid import UUID

from app.dtos.attendance import AttendanceDTO
from app.repositories.attendance import AttendanceRepository


class AttendanceError(Exception):
    status_code = 400
    code = "attendance_error"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class AttendanceNotFoundError(AttendanceError):
    status_code = 404
    code = "attendance_not_found"


class AttendanceConflictError(AttendanceError):
    status_code = 409
    code = "attendance_conflict"


class AttendanceService:
    """Coordinates repository writes, transactions, and post-commit events.

    ``transaction_manager`` may be omitted where the injected connection's
    transaction context is already owned by the caller.  In production it is
    normally an object exposing ``transaction()``.
    """
    def __init__(self, repository: AttendanceRepository, event_publisher: Any,
                 transaction_manager: Any | None = None) -> None:
        self._repository = repository
        self._event_publisher = event_publisher
        self._transaction_manager = transaction_manager

    def _transaction(self):
        if self._transaction_manager is None:
            return nullcontext()
        transaction = getattr(self._transaction_manager, "transaction", None)
        return transaction() if transaction is not None else self._transaction_manager

    @staticmethod
    def _is_unique_violation(error: Exception) -> bool:
        # psycopg's UniqueViolation and a database-agnostic fake both expose
        # SQLSTATE 23505.  Avoid tying domain code to a driver exception class.
        return getattr(error, "sqlstate", None) == "23505"

    def _publish_marked(self, attendance: AttendanceDTO, action: str) -> None:
        event = {
            "type": "attendance.marked",
            "action": action,
            "data": attendance.to_dict(),
        }
        self._event_publisher.publish(event)

    def check_in(self, member_id: UUID) -> AttendanceDTO:
        try:
            with self._transaction():
                attendance = self._repository.check_in(member_id)
        except Exception as error:
            if self._is_unique_violation(error):
                raise AttendanceConflictError("Member already has an open attendance") from error
            raise
        # This line runs only after the transaction context has committed.
        self._publish_marked(attendance, "check_in")
        return attendance

    def check_out(self, attendance_id: UUID) -> AttendanceDTO:
        with self._transaction():
            attendance = self._repository.check_out(attendance_id)
            if attendance is None:
                existing = self._repository.get(attendance_id)
                if existing is None:
                    raise AttendanceNotFoundError("Attendance was not found")
                raise AttendanceConflictError("Attendance has already been checked out")
        self._publish_marked(attendance, "check_out")
        return attendance

    def member_history(self, member_id: UUID, *, page: int, per_page: int,
                       checked_in_from: date | None = None,
                       checked_in_to: date | None = None) -> tuple[list[AttendanceDTO], int]:
        return self._repository.list_for_member(
            member_id, page=page, per_page=per_page,
            checked_in_from=checked_in_from, checked_in_to=checked_in_to,
        )

    def search(self, *, page: int, per_page: int, member_id: UUID | None = None,
               checked_in_from: date | None = None,
               checked_in_to: date | None = None) -> tuple[list[AttendanceDTO], int]:
        return self._repository.list(
            page=page, per_page=per_page, member_id=member_id,
            checked_in_from=checked_in_from, checked_in_to=checked_in_to,
        )

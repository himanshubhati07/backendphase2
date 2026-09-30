"""Attendance application service, transaction boundary, and domain errors."""
from __future__ import annotations

from datetime import date
from typing import Any, Protocol
from uuid import UUID

from app.dtos.attendance import AttendanceDTO


class AttendanceRepositoryPort(Protocol):
    def member_exists(self, connection: Any, member_id: UUID) -> bool: ...
    def check_in(self, connection: Any, member_id: UUID) -> AttendanceDTO: ...
    def get(self, connection: Any, attendance_id: UUID) -> AttendanceDTO | None: ...
    def check_out(self, connection: Any, attendance_id: UUID) -> AttendanceDTO | None: ...
    def list_for_member(self, connection: Any, member_id: UUID, *, page: int, per_page: int, checked_in_on: date | None = None) -> tuple[list[AttendanceDTO], int]: ...
    def list(self, connection: Any, *, page: int, per_page: int, member_id: UUID | None = None, checked_in_on: date | None = None) -> tuple[list[AttendanceDTO], int]: ...


class TransactionManagerPort(Protocol):
    def transaction(self) -> Any: ...


class EventProducerPort(Protocol):
    def publish(self, event_type: str, payload: dict[str, Any]) -> None: ...


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


class AttendanceMemberNotFoundError(AttendanceError):
    status_code = 404
    code = "member_not_found"


class AttendanceConflictError(AttendanceError):
    status_code = 409
    code = "attendance_conflict"


class AttendanceService:
    """Owns every attendance transaction and publishes only after commit."""

    def __init__(self, transactions: TransactionManagerPort,
                 repository: AttendanceRepositoryPort,
                 event_producer: EventProducerPort) -> None:
        self._transactions = transactions
        self._repository = repository
        self._event_producer = event_producer

    @staticmethod
    def _is_unique_violation(error: Exception) -> bool:
        return getattr(error, "sqlstate", None) == "23505"

    def _publish_marked(self, attendance: AttendanceDTO, action: str) -> None:
        # KafkaEventProducer supplies the outer event_type/occurred_at envelope.
        self._event_producer.publish("attendance.marked", {
            "action": action,
            "attendance": attendance.to_dict(),
        })

    @staticmethod
    def _member_not_found(member_id: UUID) -> None:
        raise AttendanceMemberNotFoundError(f"Member {member_id} was not found")

    def check_in(self, member_id: UUID) -> AttendanceDTO:
        try:
            with self._transactions.transaction() as connection:
                # This lookup and insert share one transaction. Besides giving
                # callers a deterministic 404, FOR KEY SHARE in the repository
                # prevents a concurrent member deletion before the insert.
                if not self._repository.member_exists(connection, member_id):
                    self._member_not_found(member_id)
                attendance = self._repository.check_in(connection, member_id)
        except Exception as error:
            if self._is_unique_violation(error):
                raise AttendanceConflictError("Member already has an open attendance") from error
            raise
        self._publish_marked(attendance, "check_in")
        return attendance

    def check_out(self, attendance_id: UUID) -> AttendanceDTO:
        with self._transactions.transaction() as connection:
            attendance = self._repository.check_out(connection, attendance_id)
            if attendance is None:
                existing = self._repository.get(connection, attendance_id)
                if existing is None:
                    raise AttendanceNotFoundError("Attendance was not found")
                raise AttendanceConflictError("Attendance has already been checked out")
        self._publish_marked(attendance, "check_out")
        return attendance

    def member_history(self, member_id: UUID, *, page: int, per_page: int,
                       checked_in_on: date | None = None) -> tuple[list[AttendanceDTO], int]:
        with self._transactions.transaction() as connection:
            if not self._repository.member_exists(connection, member_id):
                self._member_not_found(member_id)
            return self._repository.list_for_member(
                connection, member_id, page=page, per_page=per_page,
                checked_in_on=checked_in_on,
            )

    def search(self, *, page: int, per_page: int, member_id: UUID | None = None,
               checked_in_on: date | None = None) -> tuple[list[AttendanceDTO], int]:
        with self._transactions.transaction() as connection:
            return self._repository.list(
                connection, page=page, per_page=per_page, member_id=member_id,
                checked_in_on=checked_in_on,
            )

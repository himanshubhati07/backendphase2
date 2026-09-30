"""Member application service and transaction boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID

from app.errors import ConflictError, NotFoundError, ValidationError


class MemberRepositoryPort(Protocol):
    def create(self, connection: Any, data: Mapping[str, Any]) -> dict[str, Any]: ...
    def get(self, connection: Any, member_id: UUID | str) -> dict[str, Any] | None: ...
    def update(
        self, connection: Any, member_id: UUID | str, data: Mapping[str, Any]
    ) -> dict[str, Any] | None: ...
    def delete(self, connection: Any, member_id: UUID | str) -> bool: ...
    def list(self, connection: Any, page: int, per_page: int) -> tuple[list[dict[str, Any]], int]: ...


class TransactionManagerPort(Protocol):
    def transaction(self) -> Any: ...


class EventProducerPort(Protocol):
    def publish(self, event_type: str, payload: dict[str, Any]) -> None: ...


class MemberService:
    """Coordinates member persistence and its post-commit domain event."""

    _CREATE_FIELDS = frozenset({"first_name", "last_name", "email", "phone", "date_of_birth"})
    _UPDATE_FIELDS = _CREATE_FIELDS

    def __init__(
        self,
        transactions: TransactionManagerPort,
        repository: MemberRepositoryPort,
        event_producer: EventProducerPort,
    ) -> None:
        self._transactions = transactions
        self._repository = repository
        self._event_producer = event_producer

    def create(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        data = self._create_data(payload)
        try:
            # The context exits (and commits) before the producer is called.
            with self._transactions.transaction() as connection:
                member = self._repository.create(connection, data)
        except Exception as exc:
            self._raise_if_unique_email(exc)
            raise
        self._event_producer.publish("member.created", member)
        return member

    def get(self, member_id: UUID | str) -> dict[str, Any]:
        with self._transactions.transaction() as connection:
            member = self._repository.get(connection, member_id)
        return member if member is not None else self._not_found(member_id)

    def update(self, member_id: UUID | str, payload: Mapping[str, Any]) -> dict[str, Any]:
        data = self._update_data(payload)
        try:
            with self._transactions.transaction() as connection:
                member = self._repository.update(connection, member_id, data)
        except Exception as exc:
            self._raise_if_unique_email(exc)
            raise
        return member if member is not None else self._not_found(member_id)

    def delete(self, member_id: UUID | str) -> None:
        with self._transactions.transaction() as connection:
            deleted = self._repository.delete(connection, member_id)
        if not deleted:
            self._not_found(member_id)

    def list(self, page: int, per_page: int) -> dict[str, Any]:
        with self._transactions.transaction() as connection:
            items, total = self._repository.list(connection, page, per_page)
        return {"items": items, "page": page, "per_page": per_page, "total": total}

    def _create_data(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._reject_unknown(payload, self._CREATE_FIELDS)
        required = ("first_name", "last_name", "email")
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValidationError(f"Missing required field(s): {', '.join(missing)}")
        data = dict(payload)
        for field in required:
            if not isinstance(data[field], str) or not data[field].strip():
                raise ValidationError(f"{field} must be a non-empty string")
            data[field] = data[field].strip()
        for field in ("phone",):
            if field in data and data[field] is not None:
                if not isinstance(data[field], str):
                    raise ValidationError(f"{field} must be a string or null")
                data[field] = data[field].strip() or None
        return data

    def _update_data(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._reject_unknown(payload, self._UPDATE_FIELDS)
        if not payload:
            raise ValidationError("At least one field must be supplied")
        data = dict(payload)
        for field in ("first_name", "last_name", "email"):
            if field in data:
                if not isinstance(data[field], str) or not data[field].strip():
                    raise ValidationError(f"{field} must be a non-empty string")
                data[field] = data[field].strip()
        if "phone" in data and data["phone"] is not None:
            if not isinstance(data["phone"], str):
                raise ValidationError("phone must be a string or null")
            data["phone"] = data["phone"].strip() or None
        return data

    @staticmethod
    def _reject_unknown(payload: Mapping[str, Any], allowed: frozenset[str]) -> None:
        unknown = set(payload) - allowed
        if unknown:
            raise ValidationError(f"Unknown field(s): {', '.join(sorted(unknown))}")

    @staticmethod
    def _not_found(member_id: UUID | str) -> None:
        raise NotFoundError(f"Member {member_id} was not found")

    @staticmethod
    def _raise_if_unique_email(exc: Exception) -> None:
        """Map PostgreSQL's stable unique-violation SQLSTATE without exposing SQL."""
        if getattr(exc, "sqlstate", None) == "23505":
            raise ConflictError("A member with this email already exists") from exc

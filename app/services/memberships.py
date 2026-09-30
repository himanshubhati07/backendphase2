"""Use cases for membership-plan creation and membership lifecycle changes."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from app.dtos.memberships import membership_dto, membership_plan_dto
from app.errors import ConflictError, NotFoundError, ValidationError
from app.repositories.memberships import MembershipRepository


class MembershipService:
    def __init__(self, transaction_manager: Any, repository: MembershipRepository, event_producer: Any):
        self._transactions = transaction_manager
        self._repository = repository
        self._events = event_producer

    @staticmethod
    def _required_string(payload: dict[str, Any], field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{field} is required", details={field: "must be a non-empty string"})
        return value.strip()

    @staticmethod
    def _date(value: Any, field: str) -> date:
        if not isinstance(value, str):
            raise ValidationError(f"{field} must be an ISO-8601 date")
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError(f"{field} must be an ISO-8601 date") from exc

    @classmethod
    def _optional_date(cls, payload: dict[str, Any], field: str, default: date) -> date:
        return default if field not in payload else cls._date(payload[field], field)

    @staticmethod
    def _uuid(value: Any, field: str) -> UUID:
        if not isinstance(value, (str, UUID)):
            raise ValidationError(f"{field} must be a UUID")
        try:
            return value if isinstance(value, UUID) else UUID(value)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValidationError(f"{field} must be a UUID") from exc

    @classmethod
    def _plan_id(cls, payload: dict[str, Any]) -> UUID:
        return cls._uuid(payload.get("plan_id"), "plan_id")

    @staticmethod
    def _duration_end(start_date: date, plan: dict[str, Any]) -> date:
        # The database requires an exclusive end date, including for one-day plans.
        return start_date + timedelta(days=int(plan["duration_days"]))

    @staticmethod
    def _validate_fields(payload: dict[str, Any], allowed: set[str], message: str) -> None:
        unknown = set(payload) - allowed
        if unknown:
            raise ValidationError(message, details={"fields": sorted(unknown)})

    @staticmethod
    def _validate_chronology(start_date: date, end_date: date) -> None:
        if end_date <= start_date:
            raise ValidationError("end_date must be later than start_date")

    def create_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = self._required_string(payload, "name")
        description = payload.get("description")
        if description is not None and not isinstance(description, str):
            raise ValidationError("description must be a string")
        duration = payload.get("duration_days")
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
            raise ValidationError("duration_days must be a positive integer")
        try:
            price = Decimal(str(payload.get("price")))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError("price must be a non-negative decimal") from exc
        if not price.is_finite() or price < 0:
            raise ValidationError("price must be a non-negative decimal")
        active = payload.get("is_active", True)
        if not isinstance(active, bool):
            raise ValidationError("is_active must be a boolean")
        with self._transactions.transaction() as connection:
            row = self._repository.create_plan(connection, plan_id=uuid4(), name=name, description=description,
                                               duration_days=duration, price=price, is_active=active)
        return membership_plan_dto(row)

    def assign(self, member_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_fields(payload, {"plan_id", "start_date", "end_date"},
                              "only plan_id, start_date, and end_date are accepted")
        member_id = self._uuid(member_id, "member_id")
        plan_id = self._plan_id(payload)
        start_date = self._optional_date(payload, "start_date", date.today())
        with self._transactions.transaction() as connection:
            if not self._repository.get_member(connection, member_id, lock=True):
                raise NotFoundError("member not found")
            plan = self._repository.get_plan(connection, plan_id, active_only=True)
            if not plan:
                raise ValidationError("plan_id must identify an active membership plan")
            end_date = self._optional_date(payload, "end_date", self._duration_end(start_date, plan))
            self._validate_chronology(start_date, end_date)
            if self._repository.find_active_for_member(connection, member_id):
                raise ConflictError("member already has an active membership")
            row = self._repository.create_membership(connection, membership_id=uuid4(), member_id=member_id,
                                                     plan_id=plan_id, start_date=start_date, end_date=end_date)
        result = membership_dto(row)
        self._events.publish("membership.assigned", result)
        return result

    def get(self, membership_id: UUID | str) -> dict[str, Any]:
        membership_id = self._uuid(membership_id, "membership_id")
        with self._transactions.transaction() as connection:
            row = self._repository.get_membership(connection, membership_id)
        if not row:
            raise NotFoundError("membership not found")
        return membership_dto(row)

    def patch(self, membership_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_fields(payload, {"plan_id", "start_date", "end_date"},
                              "only plan_id, start_date, and end_date can be updated")
        if not payload:
            raise ValidationError("at least one updatable field is required")
        membership_id = self._uuid(membership_id, "membership_id")
        with self._transactions.transaction() as connection:
            current = self._repository.get_membership(connection, membership_id, lock=True)
            if not current:
                raise NotFoundError("membership not found")
            if current["status"] != "active":
                raise ConflictError("only active memberships can be updated")
            plan_id = self._plan_id(payload) if "plan_id" in payload else current["plan_id"]
            plan = self._repository.get_plan(connection, plan_id, active_only=True)
            if not plan:
                raise ValidationError("plan_id must identify an active membership plan")
            start = self._optional_date(payload, "start_date", current["start_date"])
            # If either component determining the duration changes, recompute an
            # omitted end date.  An explicitly supplied end date is retained.
            default_end = self._duration_end(start, plan) if ({"plan_id", "start_date"} & set(payload)) else current["end_date"]
            end = self._optional_date(payload, "end_date", default_end)
            self._validate_chronology(start, end)
            row = self._repository.update_active_membership(connection, membership_id=membership_id,
                                                            plan_id=plan_id, start_date=start, end_date=end)
        return membership_dto(row)

    def cancel(self, membership_id: UUID | str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        membership_id = self._uuid(membership_id, "membership_id")
        if payload:
            raise ValidationError("membership cancellation does not accept request fields")
        with self._transactions.transaction() as connection:
            current = self._repository.get_membership(connection, membership_id, lock=True)
            if not current:
                raise NotFoundError("membership not found")
            if current["status"] != "active":
                raise ConflictError("membership is already cancelled")
            row = self._repository.cancel_membership(connection, membership_id=membership_id)
        result = membership_dto(row)
        self._events.publish("membership.cancelled", result)
        return result

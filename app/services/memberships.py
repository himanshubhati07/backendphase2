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
    def _optional_date(payload: dict[str, Any], field: str, default: date) -> date:
        value = payload.get(field)
        if value is None:
            return default
        if not isinstance(value, str):
            raise ValidationError(f"{field} must be an ISO-8601 date")
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError(f"{field} must be an ISO-8601 date") from exc

    @staticmethod
    def _uuid(value: Any, field: str) -> UUID:
        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValidationError(f"{field} must be a UUID") from exc

    @staticmethod
    def _plan_id(payload: dict[str, Any]) -> UUID:
        return MembershipService._uuid(payload.get("membership_plan_id"), "membership_plan_id")

    @staticmethod
    def _duration_end(start_date: date, plan: dict[str, Any]) -> date:
        # A one-day plan ends on its start date; duration is inclusive.
        return start_date + timedelta(days=int(plan["duration_days"]) - 1)

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
            row = self._repository.create_plan(
                connection, plan_id=uuid4(), name=name, description=description,
                duration_days=duration, price=price, is_active=active,
            )
        return membership_plan_dto(row)

    def assign(self, member_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        member_id = self._uuid(member_id, "member_id")
        plan_id = self._plan_id(payload)
        start_date = self._optional_date(payload, "start_date", date.today())
        with self._transactions.transaction() as connection:
            if not self._repository.get_member(connection, member_id, lock=True):
                raise NotFoundError("member not found")
            plan = self._repository.get_plan(connection, plan_id, active_only=True)
            if not plan:
                raise ValidationError("membership_plan_id must identify an active membership plan")
            if self._repository.find_active_for_member(connection, member_id):
                raise ConflictError("member already has an active membership")
            row = self._repository.create_membership(
                connection, membership_id=uuid4(), member_id=member_id, plan_id=plan_id,
                start_date=start_date, end_date=self._duration_end(start_date, plan),
            )
        result = membership_dto(row)
        # Publishing happens only after the context manager successfully commits.
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
        membership_id = self._uuid(membership_id, "membership_id")
        permitted = {"membership_plan_id", "start_date"}
        unknown = set(payload) - permitted
        if unknown:
            raise ValidationError("only membership_plan_id and start_date can be updated", details={"fields": sorted(unknown)})
        if not payload:
            raise ValidationError("at least one updatable field is required")
        with self._transactions.transaction() as connection:
            current = self._repository.get_membership(connection, membership_id, lock=True)
            if not current:
                raise NotFoundError("membership not found")
            if current["status"] != "active":
                raise ConflictError("only active memberships can be updated")
            plan_id = self._plan_id(payload) if "membership_plan_id" in payload else current["membership_plan_id"]
            plan = self._repository.get_plan(connection, plan_id, active_only=True)
            if not plan:
                raise ValidationError("membership_plan_id must identify an active membership plan")
            start = self._optional_date(payload, "start_date", current["start_date"])
            row = self._repository.update_active_membership(
                connection, membership_id=membership_id, plan_id=plan_id, start_date=start,
                end_date=self._duration_end(start, plan),
            )
        return membership_dto(row)

    def cancel(self, membership_id: UUID | str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        membership_id = self._uuid(membership_id, "membership_id")
        payload = payload or {}
        if set(payload) - {"cancellation_reason"}:
            raise ValidationError("only cancellation_reason is accepted when cancelling a membership")
        reason = payload.get("cancellation_reason")
        if reason is not None and (not isinstance(reason, str) or not reason.strip()):
            raise ValidationError("cancellation_reason must be a non-empty string")
        with self._transactions.transaction() as connection:
            current = self._repository.get_membership(connection, membership_id, lock=True)
            if not current:
                raise NotFoundError("membership not found")
            if current["status"] != "active":
                raise ConflictError("membership is already cancelled")
            row = self._repository.cancel_membership(connection, membership_id=membership_id, reason=reason.strip() if reason else None)
        result = membership_dto(row)
        self._events.publish("membership.cancelled", result)
        return result

"""Membership assignment, lifecycle, and history routes."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from bottle import Bottle, abort, request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .auth import can_manage_member, current_user, enforce, require_auth
from .errors import AppError, ValidationError
from .models import Member, Membership, MembershipPlan, MembershipStatus, PaymentStatus, PlanStatus, UserRole
from .responses import success
from .validation import json_body


def _date(value: Any, field: str, *, default: date | None = None) -> date:
    if value is None and default is not None:
        return default
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be an ISO-8601 date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO-8601 date") from exc


def _amount(value: Any, *, default: Decimal) -> Decimal:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValidationError("amount must be a positive amount")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError("amount must be a positive amount") from exc
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2 or amount > Decimal("99999999.99"):
        raise ValidationError("amount must be a positive amount with at most two decimal places")
    return amount.quantize(Decimal("0.01"))


def _enum(value: Any, enum_type: type[PaymentStatus] | type[MembershipStatus], field: str, default: Any) -> Any:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValidationError(f"{field} is invalid")
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(entry.value for entry in enum_type)
        raise ValidationError(f"{field} must be one of: {allowed}") from exc


def _membership_data(item: Membership) -> dict[str, Any]:
    return {"id": item.id, "member_id": item.member_id, "plan_id": item.plan_id,
            "plan": {"id": item.plan.id, "name": item.plan.name, "duration_days": item.plan.duration_days,
                     "price": item.plan.price, "features": item.plan.features, "status": item.plan.status} if item.plan else None,
            "start_date": item.start_date, "end_date": item.end_date, "amount": item.amount,
            "payment_status": item.payment_status, "status": item.status,
            "created_at": item.created_at, "updated_at": item.updated_at}


def _member(session: Session, member_id: int) -> Member:
    member = session.get(Member, member_id)
    if member is None:
        abort(404)
    return member


def _managed_member(session: Session, member_id: int) -> Member:
    member = _member(session, member_id)
    enforce(can_manage_member(member))
    return member


def _staff_can_manage(member: Member) -> None:
    # Membership lifecycle changes are staff operations, while members may read only their own history.
    enforce(current_user().role in {UserRole.ADMIN, UserRole.TRAINER} and can_manage_member(member))


def _expire_elapsed(session: Session, member_id: int) -> None:
    today = date.today()
    for item in session.scalars(select(Membership).where(Membership.member_id == member_id,
                                                         Membership.status == MembershipStatus.ACTIVE,
                                                         Membership.end_date < today)):
        item.status = MembershipStatus.EXPIRED


def _overlaps(session: Session, member_id: int, start: date, end: date, *, ignore_id: int | None = None) -> bool:
    query = select(Membership.id).where(Membership.member_id == member_id,
                                        Membership.status == MembershipStatus.ACTIVE,
                                        Membership.start_date <= end, Membership.end_date >= start)
    if ignore_id is not None:
        query = query.where(Membership.id != ignore_id)
    return session.scalar(query) is not None


def register_membership_routes(app: Bottle) -> None:
    @app.post("/api/members/<member_id:int>/memberships")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def assign_membership(member_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        member = _managed_member(session, member_id)
        _staff_can_manage(member)
        body = json_body()
        plan_id = body.get("plan_id")
        if isinstance(plan_id, bool) or not isinstance(plan_id, int) or plan_id <= 0:
            raise ValidationError("plan_id must be a positive integer")
        plan = session.get(MembershipPlan, plan_id)
        if plan is None:
            abort(404)
        if plan.status is not PlanStatus.ACTIVE:
            raise ValidationError("Membership plan is not active")
        start = _date(body.get("start_date"), "start_date", default=date.today())
        end = _date(body.get("end_date"), "end_date", default=start + timedelta(days=plan.duration_days - 1))
        if end < start:
            raise ValidationError("end_date must not be before start_date")
        _expire_elapsed(session, member.id)
        if _overlaps(session, member.id, start, end):
            raise AppError("Membership dates overlap an active membership", "CONFLICT", 409)
        membership = Membership(
            member_id=member.id, plan_id=plan.id, start_date=start, end_date=end,
            amount=_amount(body.get("amount"), default=plan.price),
            payment_status=_enum(body.get("payment_status"), PaymentStatus, "payment_status", PaymentStatus.PENDING),
            status=_enum(body.get("status"), MembershipStatus, "status", MembershipStatus.ACTIVE),
        )
        session.add(membership)
        session.commit()
        session.refresh(membership, attribute_names=["plan"])
        return success(_membership_data(membership), "Membership assigned", 201)

    @app.get("/api/members/<member_id:int>/memberships/active")
    @require_auth()
    def active_membership(member_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        _managed_member(session, member_id)
        _expire_elapsed(session, member_id)
        session.commit()
        today = date.today()
        item = session.scalar(select(Membership).options(joinedload(Membership.plan)).where(
            Membership.member_id == member_id, Membership.status == MembershipStatus.ACTIVE,
            Membership.start_date <= today, Membership.end_date >= today).order_by(Membership.end_date.desc()))
        return success(None if item is None else _membership_data(item), "Active membership")

    @app.get("/api/members/<member_id:int>/memberships")
    @require_auth()
    def membership_history(member_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        _managed_member(session, member_id)
        _expire_elapsed(session, member_id)
        session.commit()
        records = session.scalars(select(Membership).options(joinedload(Membership.plan)).where(
            Membership.member_id == member_id).order_by(Membership.start_date.desc(), Membership.id.desc()))
        return success([_membership_data(item) for item in records], "Membership history")

    @app.post("/api/memberships/<membership_id:int>/renew")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def renew_membership(membership_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        item = session.scalar(select(Membership).options(joinedload(Membership.plan)).where(Membership.id == membership_id))
        if item is None:
            abort(404)
        member = _managed_member(session, item.member_id)
        _staff_can_manage(member)
        _expire_elapsed(session, member.id)
        if item.status == MembershipStatus.CANCELLED:
            raise ValidationError("Cancelled memberships cannot be renewed")
        if item.plan.status is not PlanStatus.ACTIVE:
            raise ValidationError("Membership plan is not active")
        start = max(date.today(), item.end_date + timedelta(days=1))
        end = start + timedelta(days=item.plan.duration_days - 1)
        if _overlaps(session, member.id, start, end):
            raise AppError("Membership dates overlap an active membership", "CONFLICT", 409)
        renewal = Membership(member_id=member.id, plan_id=item.plan_id, start_date=start, end_date=end,
                             amount=item.plan.price, payment_status=PaymentStatus.PENDING,
                             status=MembershipStatus.ACTIVE)
        session.add(renewal)
        session.commit()
        session.refresh(renewal, attribute_names=["plan"])
        return success(_membership_data(renewal), "Membership renewed", 201)

    @app.post("/api/memberships/<membership_id:int>/cancel")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def cancel_membership(membership_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        item = session.get(Membership, membership_id)
        if item is None:
            abort(404)
        member = _managed_member(session, item.member_id)
        _staff_can_manage(member)
        _expire_elapsed(session, member.id)
        if item.status != MembershipStatus.ACTIVE:
            raise ValidationError("Only active memberships can be cancelled")
        item.status = MembershipStatus.CANCELLED
        session.commit()
        session.refresh(item, attribute_names=["plan"])
        return success(_membership_data(item), "Membership cancelled")

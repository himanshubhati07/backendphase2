"""Payment endpoints with strict sensitive-data and ownership controls."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from bottle import Bottle, request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import can_manage_member, current_user, enforce, require_auth
from .errors import AppError, AuthorizationError, ValidationError
from .models import Member, Membership, Payment, PaymentMethod, PaymentStatus, UserRole
from .responses import success
from .validation import json_body, optional_string, required_string

_CARD_FIELDS = frozenset({"card_number", "cardnumber", "card_no", "card_details", "cvv", "cvc", "security_code", "expiry", "expiration", "expiry_date", "expiration_date", "expiry_month", "expiry_year", "expiration_month", "expiration_year", "exp", "exp_date", "exp_month", "exp_year"})


def _not_found(name: str) -> AppError:
    return AppError(f"{name} not found", "NOT_FOUND", 404)


def _payment_data(payment: Payment) -> dict[str, Any]:
    """Deliberately contains no request-card fields or other payment secrets."""
    return {"id": payment.id, "member_id": payment.member_id, "membership_id": payment.membership_id,
            "amount": payment.amount, "currency": payment.currency, "payment_method": payment.payment_method,
            "transaction_id": payment.transaction_id, "payment_date": payment.payment_date,
            "status": payment.status, "created_at": payment.created_at, "updated_at": payment.updated_at}


def _decimal(body: dict[str, Any], field: str) -> Decimal:
    value = body.get(field)
    if isinstance(value, bool) or value is None:
        raise ValidationError(f"{field} must be a non-negative decimal")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field} must be a non-negative decimal") from exc
    if not result.is_finite() or result < 0 or result.as_tuple().exponent < -2 or result >= Decimal("100000000"):
        raise ValidationError(f"{field} must be a non-negative decimal with at most 2 decimal places")
    return result


def _datetime(body: dict[str, Any], field: str) -> datetime:
    value = body.get(field)
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be an ISO-8601 datetime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _enum(body: dict[str, Any], field: str, enum_type: type[PaymentMethod] | type[PaymentStatus]) -> Any:
    value = body.get(field)
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ValidationError(f"{field} must be one of: {allowed}") from exc


def _reject_sensitive(body: dict[str, Any]) -> None:
    # Normalizing prevents harmless case/spacing variants from bypassing this check.
    forbidden = [key for key in body if key.lower().replace("-", "_").replace(" ", "_") in _CARD_FIELDS]
    if forbidden:
        raise ValidationError("Raw card details are not accepted")


def _member(session: Session, member_id: Any) -> Member:
    if isinstance(member_id, bool) or not isinstance(member_id, int) or member_id < 1:
        raise ValidationError("member_id must be a positive integer")
    member = session.get(Member, member_id)
    if member is None:
        raise _not_found("Member")
    return member


def _visible(payment: Payment) -> None:
    if not can_manage_member(payment.member):
        raise AuthorizationError()


def register_payment_routes(app: Bottle) -> None:
    @app.post("/api/payments")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def create_payment() -> Any:
        body = json_body()
        _reject_sensitive(body)
        session: Session = request.environ["gym.db"]
        member = _member(session, body.get("member_id"))
        enforce(can_manage_member(member))
        membership_id = body.get("membership_id")
        membership: Membership | None = None
        if membership_id is not None:
            if isinstance(membership_id, bool) or not isinstance(membership_id, int) or membership_id < 1:
                raise ValidationError("membership_id must be a positive integer")
            membership = session.get(Membership, membership_id)
            if membership is None:
                raise _not_found("Membership")
            if membership.member_id != member.id:
                raise ValidationError("membership_id must belong to member_id")
        transaction_id = optional_string(body, "transaction_id", max_length=120)
        payment = Payment(member_id=member.id, membership_id=None if membership is None else membership.id,
                          amount=_decimal(body, "amount"), currency=required_string(body, "currency", min_length=3, max_length=3).upper(),
                          payment_method=_enum(body, "payment_method", PaymentMethod),
                          transaction_id=transaction_id, payment_date=_datetime(body, "payment_date"),
                          status=_enum(body, "status", PaymentStatus))
        if not payment.currency.isalpha():
            raise ValidationError("currency must be a three-letter code")
        session.add(payment)
        session.commit()
        return success(_payment_data(payment), "Payment created", 201)

    @app.get("/api/payments/<payment_id:int>")
    @require_auth()
    def get_payment(payment_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        payment = session.get(Payment, payment_id)
        if payment is None:
            raise _not_found("Payment")
        _visible(payment)
        return success(_payment_data(payment), "Payment retrieved")

    @app.get("/api/members/<member_id:int>/payments")
    @require_auth()
    def member_payments(member_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        member = _member(session, member_id)
        enforce(can_manage_member(member))
        payments = session.scalars(select(Payment).where(Payment.member_id == member.id).order_by(Payment.payment_date.desc(), Payment.id.desc())).all()
        return success([_payment_data(item) for item in payments], "Payment history retrieved")

    @app.get("/api/payments")
    @require_auth()
    def list_payments() -> Any:
        session: Session = request.environ["gym.db"]
        user = current_user()
        query = select(Payment).join(Member)
        if user.role is UserRole.MEMBER:
            query = query.where(Member.user_id == user.id)
        elif user.role is UserRole.TRAINER:
            if user.trainer is None:
                return success([], "Payments retrieved")
            query = query.where(Member.trainer_id == user.trainer.id)
        payments = session.scalars(query.order_by(Payment.payment_date.desc(), Payment.id.desc())).all()
        return success([_payment_data(item) for item in payments], "Payments retrieved")

    @app.patch("/api/payments/<payment_id:int>/status")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def update_payment_status(payment_id: int) -> Any:
        body = json_body()
        _reject_sensitive(body)
        session: Session = request.environ["gym.db"]
        payment = session.get(Payment, payment_id)
        if payment is None:
            raise _not_found("Payment")
        _visible(payment)
        payment.status = _enum(body, "status", PaymentStatus)
        session.commit()
        return success(_payment_data(payment), "Payment status updated")

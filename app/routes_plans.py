"""Membership plan administration routes."""
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from bottle import Bottle, abort, request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import require_auth
from .errors import ValidationError
from .models import MembershipPlan, PlanStatus, UserRole
from .responses import success
from .validation import json_body, optional_string, required_string


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{field} must be a positive integer")
    return value


def _price(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValidationError("price must be a positive amount")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError("price must be a positive amount") from exc
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2 or amount > Decimal("99999999.99"):
        raise ValidationError("price must be a positive amount with at most two decimal places")
    return amount.quantize(Decimal("0.01"))


def _features(value: Any) -> list | dict:
    # Plans expose structured JSON features, rather than a lossy text field.
    if not isinstance(value, (list, dict)):
        raise ValidationError("features must be a JSON array or object")
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("features must be JSON serializable") from exc
    return value


def _status(value: Any) -> PlanStatus:
    if not isinstance(value, str):
        raise ValidationError("status must be active or inactive")
    try:
        return PlanStatus(value)
    except ValueError as exc:
        raise ValidationError("status must be active or inactive") from exc


def _plan_data(plan: MembershipPlan) -> dict[str, Any]:
    return {"id": plan.id, "name": plan.name, "description": plan.description,
            "duration_days": plan.duration_days, "price": plan.price, "features": plan.features,
            "status": plan.status, "created_at": plan.created_at, "updated_at": plan.updated_at}


def _plan_input(body: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    values: dict[str, Any] = {}
    if not partial or "name" in body:
        values["name"] = required_string(body, "name", max_length=120)
    if not partial or "description" in body:
        values["description"] = optional_string(body, "description", max_length=5000)
    if not partial or "duration_days" in body:
        values["duration_days"] = _positive_int(body.get("duration_days"), "duration_days")
    if not partial or "price" in body:
        values["price"] = _price(body.get("price"))
    # Existing callers can omit features; every persisted plan still has JSON features.
    if "features" in body:
        values["features"] = _features(body["features"])
    elif not partial:
        values["features"] = []
    if "status" in body:
        values["status"] = _status(body["status"])
    return values


def register_plan_routes(app: Bottle) -> None:
    @app.get("/api/membership-plans")
    @require_auth()
    def list_plans() -> Any:
        session: Session = request.environ["gym.db"]
        include_inactive = request.query.get("include_inactive", "false").lower()
        if include_inactive not in {"true", "false"}:
            raise ValidationError("include_inactive must be true or false")
        query = select(MembershipPlan).order_by(MembershipPlan.id)
        if include_inactive == "false":
            query = query.where(MembershipPlan.status == PlanStatus.ACTIVE)
        return success([_plan_data(item) for item in session.scalars(query)], "Membership plans")

    @app.get("/api/membership-plans/<plan_id:int>")
    @require_auth()
    def get_plan(plan_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        plan = session.get(MembershipPlan, plan_id)
        if plan is None:
            abort(404)
        return success(_plan_data(plan), "Membership plan")

    @app.post("/api/membership-plans")
    @require_auth(UserRole.ADMIN)
    def create_plan() -> Any:
        session: Session = request.environ["gym.db"]
        plan = MembershipPlan(**_plan_input(json_body()))
        session.add(plan)
        session.commit()
        return success(_plan_data(plan), "Membership plan created", 201)

    @app.put("/api/membership-plans/<plan_id:int>")
    @app.patch("/api/membership-plans/<plan_id:int>")
    @require_auth(UserRole.ADMIN)
    def update_plan(plan_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        plan = session.get(MembershipPlan, plan_id)
        if plan is None:
            abort(404)
        for field, value in _plan_input(json_body(), partial=request.method == "PATCH").items():
            setattr(plan, field, value)
        session.commit()
        return success(_plan_data(plan), "Membership plan updated")

    @app.post("/api/membership-plans/<plan_id:int>/deactivate")
    @require_auth(UserRole.ADMIN)
    def deactivate_plan(plan_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        plan = session.get(MembershipPlan, plan_id)
        if plan is None:
            abort(404)
        plan.status = PlanStatus.INACTIVE
        session.commit()
        return success(_plan_data(plan), "Membership plan deactivated")

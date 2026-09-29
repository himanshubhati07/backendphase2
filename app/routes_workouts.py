"""Workout plan and exercise endpoints."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from bottle import Bottle, request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import can_manage_member, current_user, enforce, require_auth
from .errors import AppError, AuthorizationError, ValidationError
from .models import Member, Trainer, UserRole, WorkoutExercise, WorkoutPlan, WorkoutStatus
from .responses import success
from .validation import json_body, optional_string, required_string


def _not_found(name: str) -> AppError:
    return AppError(f"{name} not found", "NOT_FOUND", 404)


def _plan_data(plan: WorkoutPlan) -> dict[str, Any]:
    return {"id": plan.id, "member_id": plan.member_id, "trainer_id": plan.trainer_id, "name": plan.name,
            "description": plan.description, "status": plan.status, "created_at": plan.created_at,
            "updated_at": plan.updated_at, "exercises": [
                {"id": item.id, "exercise_name": item.exercise_name, "muscle_group": item.muscle_group,
                 "sets": item.sets, "repetitions": item.repetitions, "weight": item.weight,
                 "duration": item.duration, "notes": item.notes, "position": item.position}
                for item in plan.exercises]}


def _positive_optional(exercise: dict[str, Any], field: str) -> int | None:
    value = exercise.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError(f"exercise {field} must be a positive integer")
    return value


def _weight(exercise: dict[str, Any]) -> Decimal | None:
    value = exercise.get("weight")
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValidationError("exercise weight must be a non-negative decimal")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError("exercise weight must be a non-negative decimal") from exc
    if not result.is_finite() or result < 0 or result.as_tuple().exponent < -2 or result >= Decimal("100000000"):
        raise ValidationError("exercise weight must be a non-negative decimal with at most 2 decimal places")
    return result


def _exercise_values(body: dict[str, Any]) -> list[dict[str, Any]]:
    items = body.get("exercises", [])
    if not isinstance(items, list):
        raise ValidationError("exercises must be an array")
    result: list[dict[str, Any]] = []
    for position, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValidationError("each exercise must be an object")
        result.append({"exercise_name": required_string(item, "exercise_name", max_length=150),
                       "muscle_group": optional_string(item, "muscle_group", max_length=100),
                       "sets": _positive_optional(item, "sets"), "repetitions": _positive_optional(item, "repetitions"),
                       "weight": _weight(item), "duration": _positive_optional(item, "duration"),
                       "notes": optional_string(item, "notes", max_length=5000), "position": position})
    return result


def _member(session: Session, member_id: Any) -> Member:
    if isinstance(member_id, bool) or not isinstance(member_id, int) or member_id < 1:
        raise ValidationError("member_id must be a positive integer")
    result = session.get(Member, member_id)
    if result is None:
        raise _not_found("Member")
    return result


def _trainer(session: Session, trainer_id: Any) -> Trainer:
    if isinstance(trainer_id, bool) or not isinstance(trainer_id, int) or trainer_id < 1:
        raise ValidationError("trainer_id must be a positive integer")
    result = session.get(Trainer, trainer_id)
    if result is None:
        raise _not_found("Trainer")
    return result


def _plan(session: Session, plan_id: int) -> WorkoutPlan:
    plan = session.scalar(select(WorkoutPlan).options(selectinload(WorkoutPlan.exercises)).where(WorkoutPlan.id == plan_id))
    if plan is None:
        raise _not_found("Workout plan")
    return plan


def _can_manage_plan(plan: WorkoutPlan) -> bool:
    user = current_user()
    if user.role is UserRole.ADMIN:
        return True
    return bool(user.role is UserRole.TRAINER and user.trainer and plan.trainer_id == user.trainer.id)


def _set_exercises(session: Session, plan: WorkoutPlan, values: list[dict[str, Any]]) -> None:
    # Flush removal before insertion so a replacement cannot conflict on position.
    plan.exercises.clear()
    session.flush()
    plan.exercises.extend(WorkoutExercise(**item) for item in values)


def register_workout_routes(app: Bottle) -> None:
    @app.post("/api/workout-plans")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def create_workout_plan() -> Any:
        body = json_body()
        session: Session = request.environ["gym.db"]
        user = current_user()
        member = _member(session, body["member_id"]) if body.get("member_id") is not None else None
        trainer = _trainer(session, body["trainer_id"]) if body.get("trainer_id") is not None else None
        if user.role is UserRole.TRAINER:
            trainer = user.trainer
            if trainer is None:
                raise AuthorizationError()
            if member is not None:
                enforce(can_manage_member(member))
        elif user.role is UserRole.ADMIN:
            # Administrators may build plans for any valid member and trainer.
            pass
        status_value = body.get("status", WorkoutStatus.ACTIVE.value)
        try:
            status = WorkoutStatus(status_value)
        except (TypeError, ValueError) as exc:
            raise ValidationError("status must be active or inactive") from exc
        plan = WorkoutPlan(member_id=None if member is None else member.id, trainer_id=None if trainer is None else trainer.id,
                           name=required_string(body, "name", max_length=150), description=optional_string(body, "description", max_length=5000), status=status)
        plan.exercises.extend(WorkoutExercise(**item) for item in _exercise_values(body))
        session.add(plan)
        session.commit()
        return success(_plan_data(plan), "Workout plan created", 201)

    @app.put("/api/workout-plans/<plan_id:int>/members/<member_id:int>")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def assign_workout_plan(plan_id: int, member_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        plan, member = _plan(session, plan_id), _member(session, member_id)
        if not _can_manage_plan(plan):
            raise AuthorizationError()
        if current_user().role is UserRole.TRAINER:
            enforce(can_manage_member(member))
        plan.member_id = member.id
        session.commit()
        return success(_plan_data(plan), "Workout plan assigned")

    @app.get("/api/members/<member_id:int>/workout-plans")
    @require_auth()
    def member_workout_plans(member_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        member = _member(session, member_id)
        enforce(can_manage_member(member))
        plans = session.scalars(select(WorkoutPlan).options(selectinload(WorkoutPlan.exercises)).where(WorkoutPlan.member_id == member.id).order_by(WorkoutPlan.id.desc())).all()
        return success([_plan_data(item) for item in plans], "Workout plans retrieved")

    @app.put("/api/workout-plans/<plan_id:int>")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def update_workout_plan(plan_id: int) -> Any:
        body = json_body()
        session: Session = request.environ["gym.db"]
        plan = _plan(session, plan_id)
        if not _can_manage_plan(plan):
            raise AuthorizationError()
        if "name" in body:
            plan.name = required_string(body, "name", max_length=150)
        if "description" in body:
            plan.description = optional_string(body, "description", max_length=5000)
        if "status" in body:
            try:
                plan.status = WorkoutStatus(body["status"])
            except (TypeError, ValueError) as exc:
                raise ValidationError("status must be active or inactive") from exc
        if "exercises" in body:
            _set_exercises(session, plan, _exercise_values(body))
        session.commit()
        return success(_plan_data(plan), "Workout plan updated")

    @app.delete("/api/workout-plans/<plan_id:int>")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def deactivate_workout_plan(plan_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        plan = _plan(session, plan_id)
        if not _can_manage_plan(plan):
            raise AuthorizationError()
        plan.status = WorkoutStatus.INACTIVE
        session.commit()
        return success(_plan_data(plan), "Workout plan deactivated")

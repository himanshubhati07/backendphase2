"""Trainer profile lifecycle and member assignment endpoints."""
from __future__ import annotations

from datetime import date
from typing import Any

from bottle import Bottle, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import can_manage_trainer, current_user, enforce, require_auth
from .errors import AppError, ValidationError
from .models import Member, ProfileStatus, Trainer, TrainerStatus, User, UserRole
from .responses import success
from .validation import json_body, optional_string, required_string


def _not_found() -> None:
    raise AppError("Trainer not found", "NOT_FOUND", 404)


def _date(body: dict[str, Any], field: str, *, required: bool = False) -> date | None:
    value = body.get(field)
    if value is None:
        if required: raise ValidationError(f"{field} is required")
        return None
    if not isinstance(value, str): raise ValidationError(f"{field} must be an ISO-8601 date")
    try: return date.fromisoformat(value)
    except ValueError as exc: raise ValidationError(f"{field} must be an ISO-8601 date") from exc


def _email(body: dict[str, Any], *, required: bool) -> str | None:
    value = required_string(body, "email", max_length=254) if required else optional_string(body, "email", max_length=254)
    if value is None: return None
    value = value.lower()
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise ValidationError("email must be a valid email address")
    return value


def _phone(body: dict[str, Any], *, required: bool) -> str | None:
    value = required_string(body, "phone", min_length=7, max_length=32) if required else optional_string(body, "phone", max_length=32)
    if value is None: return None
    if not all(c.isdigit() or c in " +-()" for c in value) or not any(c.isdigit() for c in value):
        raise ValidationError("phone must be a valid phone number")
    return value


def _status(body: dict[str, Any], *, required: bool = False) -> TrainerStatus | None:
    value = body.get("status")
    if value is None:
        if required: raise ValidationError("status is required")
        return None
    if not isinstance(value, str): raise ValidationError("status is invalid")
    try: return TrainerStatus(value)
    except ValueError as exc: raise ValidationError("status is invalid") from exc


def _experience(body: dict[str, Any], *, required: bool = False) -> int | None:
    value = body.get("experience")
    if value is None:
        if required: raise ValidationError("experience is required")
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 100:
        raise ValidationError("experience must be a non-negative integer no greater than 100")
    return value


def _trainer_data(trainer: Trainer) -> dict[str, Any]:
    return {
        "id": trainer.id, "user_id": trainer.user_id, "name": trainer.name,
        "email": trainer.email, "phone": trainer.phone, "joining_date": trainer.joining_date,
        "specialization": trainer.specialization, "experience": trainer.experience,
        "status": trainer.status, "created_at": trainer.created_at, "updated_at": trainer.updated_at,
    }


def _input(body: dict[str, Any], *, creating: bool) -> dict[str, Any]:
    values: dict[str, Any] = {}
    if creating or "name" in body: values["name"] = required_string(body, "name", max_length=160)
    if creating or "email" in body: values["email"] = _email(body, required=creating)
    if creating or "phone" in body: values["phone"] = _phone(body, required=creating)
    if creating or "joining_date" in body: values["joining_date"] = _date(body, "joining_date", required=creating)
    if creating or "specialization" in body: values["specialization"] = optional_string(body, "specialization", max_length=120)
    if creating or "experience" in body: values["experience"] = _experience(body)
    if creating or "status" in body:
        value = _status(body)
        if value is not None: values["status"] = value
    return values


def _contacts_available(session: Session, values: dict[str, Any], trainer_id: int | None = None) -> None:
    for field in ("email", "phone"):
        value = values.get(field)
        if value is None: continue
        stmt = select(Trainer.id).where(getattr(Trainer, field) == value)
        if trainer_id is not None: stmt = stmt.where(Trainer.id != trainer_id)
        if session.scalar(stmt) is not None:
            raise AppError(f"Trainer {field} already exists", "CONFLICT", 409)


def register_trainer_routes(app: Bottle) -> None:
    @app.post("/api/trainers")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def create_trainer() -> Any:
        body, session, actor = json_body(), request.environ["gym.db"], current_user()
        if actor.role is UserRole.TRAINER:
            enforce(actor.trainer is None)
            user_id = actor.id
        else:
            user_id = body.get("user_id")
            if not isinstance(user_id, int) or isinstance(user_id, bool): raise ValidationError("user_id must be an integer")
            user = session.get(User, user_id)
            if user is None or user.role is not UserRole.TRAINER or user.trainer is not None:
                raise ValidationError("user_id must identify a trainer user without a profile")
        values = _input(body, creating=True)
        _contacts_available(session, values)
        trainer = Trainer(user_id=user_id, **values)
        try:
            session.add(trainer); session.commit()
        except IntegrityError as exc:
            session.rollback(); raise AppError("Request conflicts with existing data", "CONFLICT", 409) from exc
        return success(_trainer_data(trainer), "Trainer created", 201)

    @app.get("/api/trainers")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def list_trainers() -> Any:
        session: Session = request.environ["gym.db"]
        actor = current_user()
        stmt = select(Trainer)
        if actor.role is UserRole.TRAINER:
            stmt = stmt.where(Trainer.id == actor.trainer.id) if actor.trainer else stmt.where(False)
        trainers = session.scalars(stmt.order_by(Trainer.id)).all()
        return success([_trainer_data(trainer) for trainer in trainers], "Trainers retrieved")

    @app.get("/api/trainers/<trainer_id:int>")
    @require_auth()
    def get_trainer(trainer_id: int) -> Any:
        trainer = request.environ["gym.db"].get(Trainer, trainer_id)
        if trainer is None: _not_found()
        enforce(can_manage_trainer(trainer))
        return success(_trainer_data(trainer), "Trainer retrieved")

    @app.put("/api/trainers/<trainer_id:int>")
    @require_auth()
    def update_trainer(trainer_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        trainer = session.get(Trainer, trainer_id)
        if trainer is None: _not_found()
        enforce(can_manage_trainer(trainer))
        body = json_body()
        if current_user().role is UserRole.TRAINER: enforce("status" not in body)
        values = _input(body, creating=False)
        _contacts_available(session, values, trainer.id)
        for field, value in values.items(): setattr(trainer, field, value)
        try: session.commit()
        except IntegrityError as exc:
            session.rollback(); raise AppError("Request conflicts with existing data", "CONFLICT", 409) from exc
        return success(_trainer_data(trainer), "Trainer updated")

    @app.delete("/api/trainers/<trainer_id:int>")
    @require_auth(UserRole.ADMIN)
    def deactivate_trainer(trainer_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        trainer = session.get(Trainer, trainer_id)
        if trainer is None: _not_found()
        trainer.status = TrainerStatus.INACTIVE
        session.commit()
        return success(_trainer_data(trainer), "Trainer deactivated")

    @app.put("/api/trainers/<trainer_id:int>/members/<member_id:int>")
    @require_auth(UserRole.ADMIN)
    def assign_member(trainer_id: int, member_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        trainer, member = session.get(Trainer, trainer_id), session.get(Member, member_id)
        if trainer is None: _not_found()
        if member is None: raise AppError("Member not found", "NOT_FOUND", 404)
        if trainer.status is not TrainerStatus.ACTIVE or member.profile_status is not ProfileStatus.ACTIVE:
            raise ValidationError("Trainer and member must both be active")
        member.trainer_id = trainer.id
        session.commit()
        return success({"trainer": _trainer_data(trainer), "member_id": member.id, "trainer_id": trainer.id}, "Trainer assigned to member")

"""Member profile lifecycle endpoints."""
from __future__ import annotations

from datetime import date
from typing import Any

from bottle import Bottle, request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import can_manage_member, current_user, enforce, require_auth
from .errors import AppError, ValidationError
from .models import Member, MemberMembershipStatus, ProfileStatus, Trainer, User, UserRole
from .responses import success
from .validation import json_body, optional_string, required_string


def _not_found() -> None:
    raise AppError("Member not found", "NOT_FOUND", 404)


def _date(body: dict[str, Any], field: str, *, required: bool = False) -> date | None:
    value = body.get(field)
    if value is None:
        if required:
            raise ValidationError(f"{field} is required")
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be an ISO-8601 date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO-8601 date") from exc


def _email(body: dict[str, Any], field: str = "email", *, required: bool = True) -> str | None:
    value = required_string(body, field, max_length=254) if required else optional_string(body, field, max_length=254)
    if value is None:
        return None
    value = value.lower()
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise ValidationError(f"{field} must be a valid email address")
    return value


def _phone(body: dict[str, Any], field: str = "phone", *, required: bool = True) -> str | None:
    value = required_string(body, field, min_length=7, max_length=32) if required else optional_string(body, field, max_length=32)
    if value is None:
        return None
    if not all(character.isdigit() or character in " +-()" for character in value) or not any(character.isdigit() for character in value):
        raise ValidationError(f"{field} must be a valid phone number")
    return value


def _enum(body: dict[str, Any], field: str, allowed: type[Any], *, required: bool = False) -> Any:
    value = body.get(field)
    if value is None:
        if required:
            raise ValidationError(f"{field} is required")
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} is invalid")
    try:
        return allowed(value)
    except ValueError as exc:
        raise ValidationError(f"{field} is invalid") from exc


def _member_data(member: Member) -> dict[str, Any]:
    return {
        "id": member.id, "user_id": member.user_id, "trainer_id": member.trainer_id,
        "full_name": member.full_name, "email": member.email, "phone": member.phone,
        "date_of_birth": member.date_of_birth, "gender": member.gender, "address": member.address,
        "emergency_contact": member.emergency_contact, "joining_date": member.joining_date,
        "membership_status": member.membership_status, "profile_status": member.profile_status,
        "created_at": member.created_at, "updated_at": member.updated_at,
    }


def _input(body: dict[str, Any], *, creating: bool) -> dict[str, Any]:
    values: dict[str, Any] = {}
    if creating or "full_name" in body:
        values["full_name"] = required_string(body, "full_name", max_length=160)
    if creating or "email" in body:
        values["email"] = _email(body, required=creating)
    if creating or "phone" in body:
        values["phone"] = _phone(body, required=creating)
    if creating or "joining_date" in body:
        values["joining_date"] = _date(body, "joining_date", required=creating)
    for field, length in (("gender", 32), ("address", 2000), ("emergency_contact", 120)):
        if creating or field in body:
            values[field] = optional_string(body, field, max_length=length)
    if creating or "date_of_birth" in body:
        values["date_of_birth"] = _date(body, "date_of_birth")
    for field, enum_type in (("membership_status", MemberMembershipStatus), ("profile_status", ProfileStatus)):
        if creating or field in body:
            value = _enum(body, field, enum_type, required=False)
            if value is not None:
                values[field] = value
    return values


def _contacts_available(session: Session, values: dict[str, Any], member_id: int | None = None) -> None:
    for field in ("email", "phone"):
        value = values.get(field)
        if value is None:
            continue
        statement = select(Member.id).where(getattr(Member, field) == value)
        if member_id is not None:
            statement = statement.where(Member.id != member_id)
        if session.scalar(statement) is not None:
            raise AppError(f"Member {field} already exists", "CONFLICT", 409)


def register_member_routes(app: Bottle) -> None:
    @app.post("/api/members")
    @require_auth(UserRole.ADMIN, UserRole.MEMBER)
    def create_member() -> Any:
        body, session, actor = json_body(), request.environ["gym.db"], current_user()
        if actor.role is UserRole.MEMBER:
            enforce(actor.member is None)
            user_id = actor.id
        else:
            user_id = body.get("user_id")
            if not isinstance(user_id, int) or isinstance(user_id, bool):
                raise ValidationError("user_id must be an integer")
            user = session.get(User, user_id)
            if user is None or user.role is not UserRole.MEMBER or user.member is not None:
                raise ValidationError("user_id must identify a member user without a profile")
        values = _input(body, creating=True)
        trainer_id = body.get("trainer_id")
        if trainer_id is not None:
            if not isinstance(trainer_id, int) or isinstance(trainer_id, bool):
                raise ValidationError("trainer_id must be an integer")
            trainer = session.get(Trainer, trainer_id)
            if trainer is None or trainer.status.value != "active":
                raise ValidationError("trainer_id must identify an active trainer")
            values["trainer_id"] = trainer_id
        _contacts_available(session, values)
        member = Member(user_id=user_id, **values)
        try:
            session.add(member); session.commit()
        except IntegrityError as exc:
            session.rollback(); raise AppError("Request conflicts with existing data", "CONFLICT", 409) from exc
        return success(_member_data(member), "Member created", 201)

    @app.get("/api/members")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def list_members() -> Any:
        session: Session = request.environ["gym.db"]
        actor = current_user()
        statement = select(Member)
        if actor.role is UserRole.TRAINER:
            statement = statement.where(Member.trainer_id == actor.trainer.id) if actor.trainer else statement.where(False)
        q = request.query.get("q")
        if q:
            if len(q.strip()) > 160:
                raise ValidationError("q must be at most 160 characters")
            pattern = f"%{q.strip()}%"
            statement = statement.where(or_(Member.full_name.ilike(pattern), Member.email.ilike(pattern), Member.phone.ilike(pattern)))
        members = session.scalars(statement.order_by(Member.id)).all()
        return success([_member_data(member) for member in members], "Members retrieved")

    @app.get("/api/members/<member_id:int>")
    @require_auth()
    def get_member(member_id: int) -> Any:
        member = request.environ["gym.db"].get(Member, member_id)
        if member is None: _not_found()
        enforce(can_manage_member(member))
        return success(_member_data(member), "Member retrieved")

    @app.put("/api/members/<member_id:int>")
    @require_auth()
    def update_member(member_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        member = session.get(Member, member_id)
        if member is None: _not_found()
        enforce(can_manage_member(member))
        values = _input(json_body(), creating=False)
        # Trainers may only edit their assigned member's profile, not reassignment/status controls.
        if current_user().role is UserRole.TRAINER:
            forbidden = {"membership_status", "profile_status", "trainer_id"}.intersection(request.json)
            enforce(not forbidden)
        _contacts_available(session, values, member.id)
        for field, value in values.items(): setattr(member, field, value)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback(); raise AppError("Request conflicts with existing data", "CONFLICT", 409) from exc
        return success(_member_data(member), "Member updated")

    @app.delete("/api/members/<member_id:int>")
    @require_auth(UserRole.ADMIN)
    def deactivate_member(member_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        member = session.get(Member, member_id)
        if member is None: _not_found()
        member.profile_status = ProfileStatus.INACTIVE
        session.commit()
        return success(_member_data(member), "Member deactivated")

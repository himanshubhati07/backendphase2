"""Public authentication endpoints and the authenticated identity endpoint."""
from __future__ import annotations

from datetime import date
from typing import Any

from bottle import Bottle, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .auth import current_user, decode_token, hash_password, issue_token, require_auth, validate_password_strength, verify_password
from .errors import ConflictError
from .config import Settings
from .errors import AuthenticationError, ValidationError
from .models import Member, Trainer, User, UserRole
from .responses import success
from .validation import json_body, optional_string, required_string


def _user_data(user: User) -> dict[str, Any]:
    profile: Member | Trainer | None = user.member if user.role is UserRole.MEMBER else user.trainer
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role.value,
        "is_active": user.is_active,
        "profile": None if profile is None else {
            "id": profile.id,
            "name": profile.full_name if user.role is UserRole.MEMBER else profile.name,
            "email": profile.email,
            "phone": profile.phone,
        },
    }


def _tokens(user: User, settings: Settings) -> dict[str, Any]:
    return {
        "access_token": issue_token(user, "access", settings),
        "refresh_token": issue_token(user, "refresh", settings),
        "token_type": "Bearer",
        "expires_in": settings.access_token_ttl_seconds,
        "user": _user_data(user),
    }


def _profile_input(body: dict[str, Any]) -> dict[str, Any]:
    profile = body.get("profile", body)
    if not isinstance(profile, dict):
        raise ValidationError("profile must be an object")
    return profile


def register_auth_routes(app: Bottle) -> None:
    @app.post("/api/auth/register")
    def register() -> Any:
        body = json_body()
        email = required_string(body, "email", max_length=254).lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValidationError("email must be a valid email address")
        password = required_string(body, "password", min_length=8, max_length=128)
        validate_password_strength(password)
        role_name = body.get("role", UserRole.MEMBER.value)
        if role_name not in (UserRole.MEMBER.value, UserRole.TRAINER.value):
            raise ValidationError("role must be member or trainer")
        profile = _profile_input(body)
        # full_name/name is the current contract; retain first/last-name input support for clients
        # using the original public registration shape.
        name = optional_string(profile, "full_name", max_length=160) or optional_string(profile, "name", max_length=160)
        if name is None:
            first_name = required_string(profile, "first_name", max_length=80)
            last_name = required_string(profile, "last_name", max_length=80)
            name = f"{first_name} {last_name}"
        phone = required_string(profile, "phone", min_length=7, max_length=32)
        if not all(character.isdigit() or character in " +-()" for character in phone) or not any(character.isdigit() for character in phone):
            raise ValidationError("phone must be a valid phone number")
        contact_email = optional_string(profile, "contact_email", max_length=254) or optional_string(profile, "profile_email", max_length=254) or email
        contact_email = contact_email.lower()
        if "@" not in contact_email or contact_email.startswith("@") or contact_email.endswith("@"):
            raise ValidationError("contact email must be a valid email address")
        session: Session = request.environ["gym.db"]
        settings: Settings = app.config["settings"]
        user = User(email=email, password_hash=hash_password(password), role=UserRole(role_name))
        if user.role is UserRole.MEMBER:
            user.member = Member(full_name=name, email=contact_email, phone=phone, joining_date=date.today())
        else:
            user.trainer = Trainer(
                name=name, email=contact_email, phone=phone, joining_date=date.today(),
                specialization=optional_string(profile, "specialization", max_length=120),
            )
        try:
            session.add(user)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ConflictError("An account with this email already exists") from exc
        except SQLAlchemyError:
            # The request plugin also protects every route, but rolling back here
            # keeps this session usable if registration logic is reused.
            session.rollback()
            raise
        return success(_tokens(user, settings), "Registration successful", 201)

    @app.post("/api/auth/login")
    def login() -> Any:
        body = json_body()
        email = required_string(body, "email", max_length=254).lower()
        password = required_string(body, "password", min_length=1, max_length=128)
        session: Session = request.environ["gym.db"]
        user = session.scalar(select(User).where(User.email == email))
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        return success(_tokens(user, app.config["settings"]), "Login successful")

    @app.post("/api/auth/refresh")
    def refresh() -> Any:
        body = json_body()
        token = required_string(body, "refresh_token", min_length=1, max_length=4096)
        settings: Settings = app.config["settings"]
        claims = decode_token(token, "refresh", settings)
        try:
            user_id = int(claims["sub"])
        except (TypeError, ValueError) as exc:
            raise AuthenticationError("Invalid token subject") from exc
        session: Session = request.environ["gym.db"]
        user = session.get(User, user_id)
        if user is None or not user.is_active or user.role.value != claims.get("role"):
            raise AuthenticationError("Account is unavailable")
        return success(_tokens(user, settings), "Token refreshed")

    @app.get("/api/auth/me")
    @require_auth()
    def me() -> Any:
        return success(_user_data(current_user()), "Authenticated user")

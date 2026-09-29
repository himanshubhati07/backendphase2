"""Password, JWT, RBAC, and ownership helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

import bcrypt
import jwt
from bottle import request
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from .config import Settings
from .errors import AuthenticationError, AuthorizationError
from .models import Member, Trainer, User, UserRole

P = ParamSpec("P")
R = TypeVar("R")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def issue_token(user: User, token_type: str, settings: Settings) -> str:
    if token_type not in {"access", "refresh"}:
        raise ValueError("unsupported token type")
    lifetime = timedelta(minutes=settings.access_token_minutes) if token_type == "access" else timedelta(days=settings.refresh_token_days)
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "role": user.role.value, "type": token_type, "iat": now, "exp": now + lifetime, "iss": settings.jwt_issuer}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, expected_type: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], issuer=settings.jwt_issuer, options={"require": ["sub", "role", "type", "exp", "iss"]})
    except InvalidTokenError as exc:
        raise AuthenticationError("Invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise AuthenticationError("Invalid token type")
    return payload


def _bearer_token() -> str:
    header = request.get_header("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError()
    return token


def current_user() -> User:
    user = request.environ.get("gym.auth_user")
    if not isinstance(user, User):
        raise AuthenticationError()
    return user


def require_auth(*roles: UserRole) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Require a valid access JWT, optionally constrained to roles."""
    def decorator(handler: Callable[P, R]) -> Callable[P, R]:
        @wraps(handler)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            settings: Settings = request.app.config["settings"]
            session: Session = request.environ["gym.db"]
            claims = decode_token(_bearer_token(), "access", settings)
            try:
                user_id = int(claims["sub"])
            except (TypeError, ValueError) as exc:
                raise AuthenticationError("Invalid token subject") from exc
            user = session.get(User, user_id)
            if user is None or not user.is_active:
                raise AuthenticationError("Account is unavailable")
            if claims.get("role") != user.role.value:
                raise AuthenticationError("Token is no longer valid")
            if roles and user.role not in roles and user.role is not UserRole.ADMIN:
                raise AuthorizationError()
            request.environ["gym.auth_user"] = user
            return handler(*args, **kwargs)
        return wrapped
    return decorator


def can_access_user(target_user_id: int) -> bool:
    user = current_user()
    return user.role is UserRole.ADMIN or user.id == target_user_id


def can_manage_member(member: Member) -> bool:
    user = current_user()
    if user.role is UserRole.ADMIN or member.user_id == user.id:
        return True
    return bool(user.role is UserRole.TRAINER and user.trainer and member.trainer_id == user.trainer.id)


def can_manage_trainer(trainer: Trainer) -> bool:
    user = current_user()
    return user.role is UserRole.ADMIN or (user.role is UserRole.TRAINER and trainer.user_id == user.id)


def enforce(condition: bool) -> None:
    if not condition:
        raise AuthorizationError()

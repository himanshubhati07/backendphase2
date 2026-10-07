"""Password hashing and JWT helpers for authentication."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

from app.config import Settings, get_settings
from app.exceptions import AuthenticationError

_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Validated claims carried by an access token."""

    user_id: int
    email: str
    issued_at: datetime
    expires_at: datetime


def hash_password(password: str) -> str:
    """Return a bcrypt hash suitable for persistence."""
    return _password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without exposing hashing implementation details."""
    return _password_context.verify(password, password_hash)


def create_access_token(user_id: int, email: str, settings: Settings | None = None) -> str:
    """Create a signed, thirty-minute (by default) bearer token for a user."""
    runtime_settings = settings or get_settings()
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=runtime_settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, runtime_settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str, settings: Settings | None = None) -> TokenClaims:
    """Decode and validate a bearer token, returning typed claims.

    All token parsing failures deliberately use the same authentication error so
    callers cannot distinguish expiry, signature, or claim-shape failures.
    """
    runtime_settings = settings or get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            runtime_settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "email", "iat", "exp"]},
        )
        subject = payload["sub"]
        email = payload["email"]
        issued_at = payload["iat"]
        expires_at = payload["exp"]
        if not isinstance(subject, str) or not isinstance(email, str) or not email:
            raise ValueError("Invalid token claim type")
        user_id = int(subject)
        if user_id < 1 or str(user_id) != subject:
            raise ValueError("Invalid token subject")
        if isinstance(issued_at, bool) or isinstance(expires_at, bool):
            raise ValueError("Invalid token timestamps")
        issued = datetime.fromtimestamp(issued_at, UTC)
        expires = datetime.fromtimestamp(expires_at, UTC)
    except (InvalidTokenError, KeyError, TypeError, ValueError, OverflowError, OSError):
        raise AuthenticationError("Invalid or expired authentication token.") from None

    return TokenClaims(user_id=user_id, email=email, issued_at=issued, expires_at=expires)

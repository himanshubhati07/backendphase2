"""Application services for account registration and authentication."""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction
from rest_framework_simplejwt.tokens import AccessToken

from accounts.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from accounts.models import User, UserManager
from accounts.serializers import UserSerializer


def register_user(*, email: str, password: str) -> User:
    """Create a user, translating uniqueness races into a domain error."""
    try:
        with transaction.atomic():
            return User.objects.create_user(email=email, password=password)
    except IntegrityError as exc:
        raise EmailAlreadyRegisteredError("An account already uses this email address.") from exc


def authenticate_user(*, email: str, password: str) -> User:
    """Return the active user matching credentials, without leaking which failed."""
    canonical_email = UserManager.normalize_email_address(email)
    try:
        user = User.objects.get(email=canonical_email)
    except User.DoesNotExist as exc:
        raise InvalidCredentialsError("Invalid email or password.") from exc

    if not user.is_active or not user.check_password(password):
        raise InvalidCredentialsError("Invalid email or password.")
    return user


def token_data_for_user(user: User) -> dict[str, Any]:
    """Issue the access token payload returned by auth endpoints."""
    access = AccessToken.for_user(user)
    return {
        "access": str(access),
        "token_type": "Bearer",
        "expires_in": int(access["exp"]) - int(access["iat"]),
        "user": UserSerializer(user).data,
    }

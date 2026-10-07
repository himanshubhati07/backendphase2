"""Business operations behind the public authentication routes."""
from __future__ import annotations

from psycopg import Connection
from psycopg.errors import UniqueViolation

from app.config import Settings, get_settings
from app.exceptions import AuthenticationError, ConflictError
from app.repositories_users import create_user, find_by_email
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.security import create_access_token, hash_password, verify_password


def normalize_email(email: str) -> str:
    """Apply the application's canonical email representation."""
    return email.strip().lower()


class AuthService:
    """Coordinates user persistence and credential/token security."""

    def __init__(self, connection: Connection, settings: Settings | None = None) -> None:
        self.connection = connection
        self.settings = settings or get_settings()

    def register(self, request: RegisterRequest) -> UserResponse:
        email = normalize_email(str(request.email))
        if find_by_email(self.connection, email) is not None:
            raise ConflictError("An account with this email already exists.")

        try:
            user = create_user(self.connection, email, hash_password(request.password))
        except UniqueViolation:
            # Clear PostgreSQL's failed transaction state before the connection
            # dependency attempts its normal final commit.
            self.connection.rollback()
            raise ConflictError("An account with this email already exists.") from None
        return UserResponse(id=user.id, email=user.email, created_at=user.created_at)

    def login(self, request: LoginRequest) -> TokenResponse:
        email = normalize_email(str(request.email))
        user = find_by_email(self.connection, email)
        if user is None or not verify_password(request.password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        return TokenResponse(
            access_token=create_access_token(user.id, user.email, self.settings),
            expires_in=self.settings.access_token_expire_minutes * 60,
        )

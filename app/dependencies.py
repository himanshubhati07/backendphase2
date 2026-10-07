"""Reusable FastAPI authentication dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import Connection

from app.database import get_connection
from app.exceptions import AuthenticationError
from app.repositories_users import find_by_id
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: int
    email: str


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    connection: Annotated[Connection, Depends(get_connection)],
) -> CurrentUser:
    """Resolve a valid bearer token to an extant user account."""
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AuthenticationError("Authentication credentials are required.")

    claims = decode_access_token(credentials.credentials)
    user = find_by_id(connection, claims.user_id)
    if user is None:
        raise AuthenticationError("Invalid or expired authentication token.")
    return CurrentUser(id=user.id, email=user.email)


AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]

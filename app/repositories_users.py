"""Persistence operations for users."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from psycopg import Connection


@dataclass(frozen=True, slots=True)
class User:
    id: int
    email: str
    password_hash: str
    created_at: datetime


def _to_user(row: tuple[object, ...] | None) -> User | None:
    if row is None:
        return None
    user_id, email, password_hash, created_at = row
    return User(id=int(user_id), email=str(email), password_hash=str(password_hash), created_at=created_at)  # type: ignore[arg-type]


def find_by_email(connection: Connection, email: str) -> User | None:
    """Find one user by their normalized email address."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = %s",
            (email,),
        )
        return _to_user(cursor.fetchone())


def find_by_id(connection: Connection, user_id: int) -> User | None:
    """Find one user by primary key."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        return _to_user(cursor.fetchone())


def create_user(connection: Connection, email: str, password_hash: str) -> User:
    """Insert a user and return its database-generated fields."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, password_hash)
            VALUES (%s, %s)
            RETURNING id, email, password_hash, created_at
            """,
            (email, password_hash),
        )
        user = _to_user(cursor.fetchone())
    if user is None:  # Defensive: INSERT ... RETURNING must return a row.
        raise RuntimeError("User insert did not return a user")
    return user

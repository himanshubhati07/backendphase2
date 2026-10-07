"""Backward-compatible function wrappers for :mod:`app.repositories` users.

New application code should depend on ``UserRepository`` directly.
"""
from __future__ import annotations

from psycopg import Connection

from app.repositories import User, UserRepository

__all__ = ["User", "UserRepository", "create_user", "find_by_email", "find_by_id"]


def find_by_email(connection: Connection, email: str) -> User | None:
    """Compatibility wrapper for ``UserRepository.find_by_email``."""
    return UserRepository(connection).find_by_email(email)


def find_by_id(connection: Connection, user_id: int) -> User | None:
    """Compatibility wrapper for ``UserRepository.find_by_id``."""
    return UserRepository(connection).find_by_id(user_id)


def create_user(connection: Connection, email: str, password_hash: str) -> User:
    """Compatibility wrapper for ``UserRepository.create_user``."""
    return UserRepository(connection).create_user(email, password_hash)

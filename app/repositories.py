"""Class-based PostgreSQL repositories for the user and task domains.

Repositories are constructed with the request-scoped psycopg connection.  All
queries keep values separate from SQL text so the database driver binds them as
parameters.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row

from app.schemas import Priority, TaskCreate, TaskStatus, TaskUpdate


@dataclass(frozen=True, slots=True)
class User:
    """Persisted user domain record."""

    id: int
    email: str
    password_hash: str
    created_at: datetime


def _to_user(row: tuple[object, ...] | None) -> User | None:
    if row is None:
        return None
    user_id, email, password_hash, created_at = row
    return User(
        id=int(user_id),
        email=str(email),
        password_hash=str(password_hash),
        created_at=created_at,  # type: ignore[arg-type]
    )


class UserRepository:
    """Persistence operations for :class:`User` records."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def find_by_email(self, email: str) -> User | None:
        """Find one user by their normalized email address."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE email = %s",
                (email,),
            )
            return _to_user(cursor.fetchone())

    def find_by_id(self, user_id: int) -> User | None:
        """Find one user by primary key."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE id = %s",
                (user_id,),
            )
            return _to_user(cursor.fetchone())

    def create_user(self, email: str, password_hash: str) -> User:
        """Insert a user and return its database-generated fields."""
        with self.connection.cursor() as cursor:
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


_TASK_COLUMNS = """
    id, user_id, title, description, priority, due_date, status, created_at, updated_at
"""


class TaskRepository:
    """Owner-scoped persistence operations for task records."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    @staticmethod
    def _task_filters(
        user_id: int,
        search: str | None = None,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
    ) -> tuple[str, list[Any]]:
        """Build the fixed owner filter plus optional parameterized filters."""
        clauses = ["user_id = %s"]
        parameters: list[Any] = [user_id]
        if search is not None:
            clauses.append("title ILIKE %s")
            parameters.append(f"%{search}%")
        if status is not None:
            clauses.append("status = %s")
            parameters.append(status.value)
        if priority is not None:
            clauses.append("priority = %s")
            parameters.append(priority.value)
        return " AND ".join(clauses), parameters

    def create_task(self, user_id: int, task: TaskCreate) -> dict[str, Any]:
        """Insert a task for its owner and return its persisted representation."""
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                INSERT INTO tasks (user_id, title, description, priority, due_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING {_TASK_COLUMNS}
                """,
                (user_id, task.title, task.description, task.priority.value, task.due_date, task.status.value),
            )
            return cursor.fetchone()

    def list_tasks(
        self,
        user_id: int,
        offset: int,
        limit: int,
        search: str | None = None,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
    ) -> tuple[Sequence[dict[str, Any]], int]:
        """Return one owner-scoped page and the separate matching-row count."""
        where_clause, parameters = self._task_filters(user_id, search, status, priority)
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM tasks WHERE {where_clause}", parameters)
            total = cursor.fetchone()["total"]
            cursor.execute(
                f"""
                SELECT {_TASK_COLUMNS}
                FROM tasks
                WHERE {where_clause}
                ORDER BY id ASC
                OFFSET %s LIMIT %s
                """,
                [*parameters, offset, limit],
            )
            return cursor.fetchall(), total

    def get_task(self, task_id: int, user_id: int) -> dict[str, Any] | None:
        """Return a task only when it belongs to the requesting user."""
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"SELECT {_TASK_COLUMNS} FROM tasks WHERE id = %s AND user_id = %s",
                (task_id, user_id),
            )
            return cursor.fetchone()

    def replace_task(self, task_id: int, user_id: int, task: TaskUpdate) -> dict[str, Any] | None:
        """Replace a task, constrained by both its id and owner."""
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                UPDATE tasks
                SET title = %s, description = %s, priority = %s, due_date = %s,
                    status = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
                RETURNING {_TASK_COLUMNS}
                """,
                (
                    task.title, task.description, task.priority.value, task.due_date,
                    task.status.value, task_id, user_id,
                ),
            )
            return cursor.fetchone()

    def complete_task(self, task_id: int, user_id: int) -> dict[str, Any] | None:
        """Mark an owner-scoped task completed."""
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                UPDATE tasks
                SET status = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
                RETURNING {_TASK_COLUMNS}
                """,
                (TaskStatus.COMPLETED.value, task_id, user_id),
            )
            return cursor.fetchone()

    def delete_task(self, task_id: int, user_id: int) -> bool:
        """Delete a task only when it belongs to the requesting user."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM tasks WHERE id = %s AND user_id = %s RETURNING id",
                (task_id, user_id),
            )
            return cursor.fetchone() is not None

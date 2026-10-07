"""Owner-scoped PostgreSQL persistence operations for tasks."""
from collections.abc import Sequence
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row

from app.schemas import Priority, TaskCreate, TaskStatus, TaskUpdate

_TASK_COLUMNS = """
    id, user_id, title, description, priority, due_date, status, created_at, updated_at
"""


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


def create_task(connection: Connection, user_id: int, task: TaskCreate) -> dict[str, Any]:
    """Insert a task for its owner and return its persisted representation."""
    with connection.cursor(row_factory=dict_row) as cursor:
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
    connection: Connection,
    user_id: int,
    offset: int,
    limit: int,
    search: str | None = None,
    status: TaskStatus | None = None,
    priority: Priority | None = None,
) -> tuple[Sequence[dict[str, Any]], int]:
    """Return one owner-scoped page and the separate matching-row count."""
    where_clause, parameters = _task_filters(user_id, search, status, priority)
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM tasks WHERE {where_clause}", parameters
        )
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


def get_task(connection: Connection, task_id: int, user_id: int) -> dict[str, Any] | None:
    """Return a task only when it belongs to the requesting user."""
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            f"SELECT {_TASK_COLUMNS} FROM tasks WHERE id = %s AND user_id = %s",
            (task_id, user_id),
        )
        return cursor.fetchone()


def replace_task(connection: Connection, task_id: int, user_id: int, task: TaskUpdate) -> dict[str, Any] | None:
    """Replace a task, constrained by both its id and owner."""
    with connection.cursor(row_factory=dict_row) as cursor:
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


def complete_task(connection: Connection, task_id: int, user_id: int) -> dict[str, Any] | None:
    """Mark an owner-scoped task completed."""
    with connection.cursor(row_factory=dict_row) as cursor:
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


def delete_task(connection: Connection, task_id: int, user_id: int) -> bool:
    """Delete a task only when it belongs to the requesting user."""
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM tasks WHERE id = %s AND user_id = %s RETURNING id",
            (task_id, user_id),
        )
        return cursor.fetchone() is not None

"""Backward-compatible function wrappers for :mod:`app.repositories` tasks.

New application code should depend on ``TaskRepository`` directly.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from psycopg import Connection

from app.repositories import TaskRepository
from app.schemas import Priority, TaskCreate, TaskStatus, TaskUpdate

__all__ = [
    "TaskRepository",
    "complete_task",
    "create_task",
    "delete_task",
    "get_task",
    "list_tasks",
    "replace_task",
]


def create_task(connection: Connection, user_id: int, task: TaskCreate) -> dict[str, Any]:
    """Compatibility wrapper for ``TaskRepository.create_task``."""
    return TaskRepository(connection).create_task(user_id, task)


def list_tasks(
    connection: Connection,
    user_id: int,
    offset: int,
    limit: int,
    search: str | None = None,
    status: TaskStatus | None = None,
    priority: Priority | None = None,
) -> tuple[Sequence[dict[str, Any]], int]:
    """Compatibility wrapper for ``TaskRepository.list_tasks``."""
    return TaskRepository(connection).list_tasks(user_id, offset, limit, search, status, priority)


def get_task(connection: Connection, task_id: int, user_id: int) -> dict[str, Any] | None:
    """Compatibility wrapper for ``TaskRepository.get_task``."""
    return TaskRepository(connection).get_task(task_id, user_id)


def replace_task(
    connection: Connection, task_id: int, user_id: int, task: TaskUpdate
) -> dict[str, Any] | None:
    """Compatibility wrapper for ``TaskRepository.replace_task``."""
    return TaskRepository(connection).replace_task(task_id, user_id, task)


def complete_task(connection: Connection, task_id: int, user_id: int) -> dict[str, Any] | None:
    """Compatibility wrapper for ``TaskRepository.complete_task``."""
    return TaskRepository(connection).complete_task(task_id, user_id)


def delete_task(connection: Connection, task_id: int, user_id: int) -> bool:
    """Compatibility wrapper for ``TaskRepository.delete_task``."""
    return TaskRepository(connection).delete_task(task_id, user_id)

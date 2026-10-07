"""Task application service: validation boundary and domain error handling."""
from psycopg import Connection

from app.repositories import TaskRepository
from app.exceptions import NotFoundError
from app.schemas import Priority, TaskCreate, TaskListResponse, TaskResponse, TaskStatus, TaskUpdate

_TASK_NOT_FOUND = "Task not found."


def create_task(connection: Connection, user_id: int, task: TaskCreate) -> TaskResponse:
    return TaskResponse.model_validate(TaskRepository(connection).create_task(user_id, task))


def list_tasks(
    connection: Connection,
    user_id: int,
    offset: int,
    limit: int,
    search: str | None = None,
    status: TaskStatus | None = None,
    priority: Priority | None = None,
) -> TaskListResponse:
    rows, total = TaskRepository(connection).list_tasks(
        user_id, offset, limit, search, status, priority
    )
    return TaskListResponse(
        items=[TaskResponse.model_validate(row) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


def get_task(connection: Connection, task_id: int, user_id: int) -> TaskResponse:
    task = TaskRepository(connection).get_task(task_id, user_id)
    if task is None:
        raise NotFoundError(_TASK_NOT_FOUND)
    return TaskResponse.model_validate(task)


def replace_task(connection: Connection, task_id: int, user_id: int, task: TaskUpdate) -> TaskResponse:
    updated_task = TaskRepository(connection).replace_task(task_id, user_id, task)
    if updated_task is None:
        raise NotFoundError(_TASK_NOT_FOUND)
    return TaskResponse.model_validate(updated_task)


def complete_task(connection: Connection, task_id: int, user_id: int) -> TaskResponse:
    completed_task = TaskRepository(connection).complete_task(task_id, user_id)
    if completed_task is None:
        raise NotFoundError(_TASK_NOT_FOUND)
    return TaskResponse.model_validate(completed_task)


def delete_task(connection: Connection, task_id: int, user_id: int) -> None:
    if not TaskRepository(connection).delete_task(task_id, user_id):
        raise NotFoundError(_TASK_NOT_FOUND)

"""Task application service: validation boundary and domain error handling."""
from psycopg import Connection

from app import repositories_tasks
from app.exceptions import NotFoundError
from app.schemas import Priority, TaskCreate, TaskListResponse, TaskResponse, TaskStatus, TaskUpdate

_TASK_NOT_FOUND = "Task not found."


def create_task(connection: Connection, user_id: int, task: TaskCreate) -> TaskResponse:
    return TaskResponse.model_validate(repositories_tasks.create_task(connection, user_id, task))


def list_tasks(
    connection: Connection,
    user_id: int,
    offset: int,
    limit: int,
    search: str | None = None,
    status: TaskStatus | None = None,
    priority: Priority | None = None,
) -> TaskListResponse:
    rows, total = repositories_tasks.list_tasks(
        connection, user_id, offset, limit, search, status, priority
    )
    return TaskListResponse(
        items=[TaskResponse.model_validate(row) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


def get_task(connection: Connection, task_id: int, user_id: int) -> TaskResponse:
    task = repositories_tasks.get_task(connection, task_id, user_id)
    if task is None:
        raise NotFoundError(_TASK_NOT_FOUND)
    return TaskResponse.model_validate(task)


def replace_task(connection: Connection, task_id: int, user_id: int, task: TaskUpdate) -> TaskResponse:
    updated_task = repositories_tasks.replace_task(connection, task_id, user_id, task)
    if updated_task is None:
        raise NotFoundError(_TASK_NOT_FOUND)
    return TaskResponse.model_validate(updated_task)


def complete_task(connection: Connection, task_id: int, user_id: int) -> TaskResponse:
    completed_task = repositories_tasks.complete_task(connection, task_id, user_id)
    if completed_task is None:
        raise NotFoundError(_TASK_NOT_FOUND)
    return TaskResponse.model_validate(completed_task)


def delete_task(connection: Connection, task_id: int, user_id: int) -> None:
    if not repositories_tasks.delete_task(connection, task_id, user_id):
        raise NotFoundError(_TASK_NOT_FOUND)

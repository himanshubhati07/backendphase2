"""Authenticated HTTP routes for the task resource."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from psycopg import Connection

from app.config import get_settings
from app.database import get_connection
from app.dependencies import CurrentUser, get_current_user
from app.schemas import (
    MessageResponse,
    Priority,
    SuccessResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)
from app import services_tasks

_settings = get_settings()
router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("", response_model=SuccessResponse[TaskResponse], status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    connection: Annotated[Connection, Depends(get_connection)],
) -> SuccessResponse[TaskResponse]:
    created = services_tasks.create_task(connection, current_user.id, task)
    return SuccessResponse(message="Task created.", data=created)


@router.get("", response_model=SuccessResponse[TaskListResponse])
def list_tasks(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    connection: Annotated[Connection, Depends(get_connection)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=_settings.max_task_limit)] = _settings.default_task_limit,
    search: Annotated[str | None, Query(min_length=1, pattern=r".*\S.*")] = None,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: Annotated[Priority | None, Query()] = None,
) -> SuccessResponse[TaskListResponse]:
    tasks = services_tasks.list_tasks(
        connection,
        current_user.id,
        offset,
        limit,
        search,
        status_filter,
        priority,
    )
    return SuccessResponse(message="Tasks retrieved.", data=tasks)


@router.get("/{task_id}", response_model=SuccessResponse[TaskResponse])
def get_task(
    task_id: Annotated[int, Path(ge=1)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    connection: Annotated[Connection, Depends(get_connection)],
) -> SuccessResponse[TaskResponse]:
    task = services_tasks.get_task(connection, task_id, current_user.id)
    return SuccessResponse(message="Task retrieved.", data=task)


@router.put("/{task_id}", response_model=SuccessResponse[TaskResponse])
def replace_task(
    task_id: Annotated[int, Path(ge=1)],
    task: TaskUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    connection: Annotated[Connection, Depends(get_connection)],
) -> SuccessResponse[TaskResponse]:
    updated = services_tasks.replace_task(connection, task_id, current_user.id, task)
    return SuccessResponse(message="Task updated.", data=updated)


@router.patch("/{task_id}/complete", response_model=SuccessResponse[TaskResponse])
def complete_task(
    task_id: Annotated[int, Path(ge=1)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    connection: Annotated[Connection, Depends(get_connection)],
) -> SuccessResponse[TaskResponse]:
    completed = services_tasks.complete_task(connection, task_id, current_user.id)
    return SuccessResponse(message="Task completed.", data=completed)


@router.delete("/{task_id}", response_model=SuccessResponse[MessageResponse])
def delete_task(
    task_id: Annotated[int, Path(ge=1)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    connection: Annotated[Connection, Depends(get_connection)],
) -> SuccessResponse[MessageResponse]:
    services_tasks.delete_task(connection, task_id, current_user.id)
    return SuccessResponse(message="Task deleted.", data=MessageResponse(message="Task deleted."))

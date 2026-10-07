"""Pydantic DTOs defining the public API wire contract."""
from datetime import date, datetime
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

DataT = TypeVar("DataT")


class Priority(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class TaskStatus(StrEnum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(RegisterRequest):
    pass


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TaskFields(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    priority: Priority
    due_date: date
    status: TaskStatus


class TaskCreate(TaskFields):
    pass


class TaskUpdate(TaskFields):
    pass


class TaskResponse(TaskFields):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    offset: int
    limit: int


class SuccessResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: str
    data: DataT


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str
    timestamp: datetime
    correlation_id: str
    details: object | None = None


class MessageResponse(BaseModel):
    message: str


class ORMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

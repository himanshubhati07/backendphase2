"""Public registration and login API routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from psycopg import Connection

from app.database import get_connection
from app.schemas import (
    ErrorResponse,
    LoginRequest,
    RegisterRequest,
    SuccessResponse,
    TokenResponse,
    UserResponse,
)
from app.services_auth import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "An account with this email already exists.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Request validation failed.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "An unexpected server error occurred.",
        },
    },
)
def register(
    request: RegisterRequest,
    connection: Annotated[Connection, Depends(get_connection)],
) -> SuccessResponse[UserResponse]:
    """Create a new account."""
    user = AuthService(connection).register(request)
    return SuccessResponse(message="Registration successful.", data=user)


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Invalid email or password.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Request validation failed.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "An unexpected server error occurred.",
        },
    },
)
def login(
    request: LoginRequest,
    connection: Annotated[Connection, Depends(get_connection)],
) -> SuccessResponse[TokenResponse]:
    """Authenticate a user and issue a bearer access token."""
    token = AuthService(connection).login(request)
    return SuccessResponse(message="Login successful.", data=token)

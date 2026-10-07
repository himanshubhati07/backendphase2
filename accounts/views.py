"""Thin HTTP adapters for account authentication."""

from __future__ import annotations

from typing import Any

from config.responses import success_response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from accounts.serializers import LoginSerializer, RegistrationSerializer
from accounts.services import authenticate_user, register_user, token_data_for_user


class RegistrationView(APIView):
    """Register an account and issue its access token."""

    serializer_class = RegistrationSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes: list[Any] = []

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Validate a registration request and delegate user creation."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = register_user(**serializer.validated_data)
        except EmailAlreadyRegisteredError as exc:
            raise ValidationError({"email": [str(exc)]}, code="email_already_registered") from exc

        return success_response(
            data=token_data_for_user(user),
            message="Registration successful.",
            status_code=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Authenticate an account and issue an access token."""

    serializer_class = LoginSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes: list[Any] = []

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Validate credentials and delegate authentication."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = authenticate_user(**serializer.validated_data)
        except InvalidCredentialsError as exc:
            raise AuthenticationFailed(str(exc), code="invalid_credentials") from exc

        return success_response(
            data=token_data_for_user(user),
            message="Login successful.",
            status_code=status.HTTP_200_OK,
        )

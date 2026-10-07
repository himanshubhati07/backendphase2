"""Focused integration tests for registration and login."""

from __future__ import annotations

import pytest
from django.urls import include, path
from rest_framework.test import APIClient

from accounts.models import User

urlpatterns = [path("api/v1/", include("accounts.urls"))]

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> APIClient:
    """Provide an unauthenticated API client."""
    return APIClient()


@pytest.mark.urls("accounts.tests.test_auth")
def test_registration_creates_normalized_user_and_returns_safe_token_data(client: APIClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        {"email": "  USER@Example.COM ", "password": "safe-password-123"},
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["access"]
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 1800
    assert data["user"]["email"] == "user@example.com"
    assert "password" not in data["user"]

    user = User.objects.get(email="user@example.com")
    assert user.check_password("safe-password-123")
    assert str(user.pk) == data["user"]["id"]


@pytest.mark.urls("accounts.tests.test_auth")
def test_registration_rejects_duplicate_normalized_email(client: APIClient) -> None:
    User.objects.create_user(email="user@example.com", password="safe-password-123")

    response = client.post(
        "/api/v1/auth/register",
        {"email": "USER@EXAMPLE.COM", "password": "safe-password-123"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["success"] is False


@pytest.mark.urls("accounts.tests.test_auth")
def test_login_returns_access_token_and_never_returns_password(client: APIClient) -> None:
    User.objects.create_user(email="user@example.com", password="safe-password-123")

    response = client.post(
        "/api/v1/auth/login",
        {"email": "USER@EXAMPLE.COM", "password": "safe-password-123"},
        format="json",
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access"]
    assert data["expires_in"] == 1800
    assert data["user"]["email"] == "user@example.com"
    assert "password" not in data["user"]


@pytest.mark.urls("accounts.tests.test_auth")
def test_login_rejects_invalid_credentials(client: APIClient) -> None:
    User.objects.create_user(email="user@example.com", password="safe-password-123")

    response = client.post(
        "/api/v1/auth/login",
        {"email": "user@example.com", "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["success"] is False

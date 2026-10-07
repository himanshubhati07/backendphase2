"""End-to-end authentication and authentication-boundary coverage."""
from fastapi.testclient import TestClient
import pytest


def assert_error_envelope(response, status_code: int, error_code: str) -> dict:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == error_code
    assert body["message"]
    assert body["timestamp"]
    assert body["correlation_id"]
    return body


def test_register_returns_standard_envelope_and_persists_normalized_user(
    client: TestClient, db_connection
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "  New.User@Example.COM  ", "password": "CorrectHorse1"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Registration successful."
    assert body["data"]["id"] == 1
    assert body["data"]["email"] == "new.user@example.com"
    assert body["data"]["created_at"]

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT email, password_hash FROM users WHERE id = %s", (body["data"]["id"],))
        email, password_hash = cursor.fetchone()
    assert email == "new.user@example.com"
    assert password_hash != "CorrectHorse1"


def test_login_issues_bearer_token_for_registered_user(client: TestClient) -> None:
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "CorrectHorse1"},
    )
    assert registration.status_code == 201

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "LOGIN@example.com", "password": "CorrectHorse1"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Login successful."
    assert isinstance(body["data"]["access_token"], str) and body["data"]["access_token"]
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["expires_in"] == 1800


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/auth/register", {"email": "not-an-email", "password": "CorrectHorse1"}),
        ("/api/v1/auth/register", {"email": "valid@example.com", "password": "short"}),
        ("/api/v1/auth/login", {"email": "valid@example.com"}),
    ],
)
def test_auth_request_validation_errors_use_standard_error_envelope(
    client: TestClient, path: str, payload: dict[str, str]
) -> None:
    response = client.post(path, json=payload, headers={"X-Request-ID": "auth-validation-id"})
    body = assert_error_envelope(response, 422, "validation_error")
    assert body["message"] == "Request validation failed."
    assert body["correlation_id"] == "auth-validation-id"
    assert body["details"]


def test_duplicate_registration_is_conflict_and_email_is_normalized(client: TestClient) -> None:
    payload = {"email": "duplicate@example.com", "password": "CorrectHorse1"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "DUPLICATE@EXAMPLE.COM", "password": "AnotherPass1"},
    )
    body = assert_error_envelope(response, 409, "conflict")
    assert body["message"] == "An account with this email already exists."


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "missing@example.com", "password": "CorrectHorse1"},
        {"email": "known@example.com", "password": "WrongPassword1"},
    ],
)
def test_login_rejects_unknown_or_incorrect_credentials(client: TestClient, payload: dict[str, str]) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "known@example.com", "password": "CorrectHorse1"},
    )

    response = client.post("/api/v1/auth/login", json=payload)
    body = assert_error_envelope(response, 401, "authentication_error")
    assert body["message"] == "Invalid email or password."
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer malformed.token.value"}, {"Authorization": "Basic abc"}],
)
def test_protected_routes_require_valid_bearer_authentication(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get("/api/v1/tasks", headers=headers)
    body = assert_error_envelope(response, 401, "authentication_error")
    assert response.headers["www-authenticate"] == "Bearer"
    assert body["message"] in {
        "Authentication credentials are required.",
        "Invalid or expired authentication token.",
    }

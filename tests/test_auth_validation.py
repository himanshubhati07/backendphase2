from __future__ import annotations

from flask import Flask

from app import create_app
from app.auth import require_api_key
from app.errors import AuthenticationError
from app.kafka import NullEventProducer
from app.settings import Settings
from app.validation import parse_pagination


def _settings() -> Settings:
    return Settings(
        app_env="test",
        host="127.0.0.1",
        port=8000,
        database_url="postgresql://unused:unused@127.0.0.1:1/unused",
        api_keys=("test-key",),
        kafka_bootstrap_servers="127.0.0.1:1",
        kafka_client_id="tests",
        kafka_topic="gym.events",
        log_level="CRITICAL",
        flask_secret_key="test-secret",
    )


def _client():
    return create_app(_settings(), NullEventProducer()).test_client()


def test_api_key_http_rejections_use_json_error_shape() -> None:
    client = _client()
    for headers in ({}, {"X-API-Key": "wrong-key"}):
        response = client.get("/api/v1/members", headers=headers)
        assert response.status_code == 401
        error = response.get_json()["error"]
        assert error["code"] == "authentication_failed"
        assert error["message"] == "Missing or invalid API key"
        assert error["timestamp"]
        assert "correlation_id" in error


def test_valid_api_key_reaches_validation_not_authentication() -> None:
    response = _client().post("/api/v1/members", headers={"X-API-Key": "test-key"}, json=["not", "an", "object"])
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_invalid_uuid_date_and_unknown_member_fields_return_json_400() -> None:
    client = _client()
    headers = {"X-API-Key": "test-key"}
    cases = [
        ("get", "/api/v1/members/not-a-uuid", None),
        ("post", "/api/v1/members", {"first_name": "A", "last_name": "B", "email": "a@example.test", "date_of_birth": "not-a-date"}),
        ("post", "/api/v1/members", {"first_name": "A", "last_name": "B", "email": "a@example.test", "unexpected": True}),
    ]
    for method, path, body in cases:
        response = getattr(client, method)(path, headers=headers, json=body)
        assert response.status_code == 400
        assert response.is_json
        assert response.get_json()["error"]["code"] == "validation_error"


def test_membership_and_attendance_query_validation_returns_json_400() -> None:
    client = _client()
    headers = {"X-API-Key": "test-key"}
    membership = client.post("/api/v1/membership-plans", headers=headers, json={"name": "x"})
    assert membership.status_code == 400
    attendance = client.get("/api/v1/attendance?date=2025-01-01&date_from=2025-01-01", headers=headers)
    assert attendance.status_code == 400
    assert attendance.get_json()["error"]["code"] == "validation_error"


def test_api_key_missing_raises_for_direct_decorator_use() -> None:
    app = Flask(__name__)

    @app.get("/protected")
    @require_api_key(("test-key",))
    def protected():
        return {"ok": True}

    with app.test_request_context("/protected"):
        try:
            protected()
        except AuthenticationError as error:
            assert error.message == "Missing or invalid API key"
        else:
            raise AssertionError("authentication was not enforced")


def test_pagination_defaults_and_cap() -> None:
    assert parse_pagination({}) == (1, 20)
    try:
        parse_pagination({"per_page": "101"})
    except Exception:
        pass
    else:
        raise AssertionError("cap was not enforced")


def test_docs_and_openapi_are_public_and_complete() -> None:
    client = _client()
    assert client.get("/docs").status_code == 200
    response = client.get("/openapi.json")
    assert response.status_code == 200
    specification = response.get_json()
    assert "/api/v1/members/{member_id}/memberships" in specification["paths"]
    assert "Membership" in specification["components"]["schemas"]

"""HTTP contract tests for membership and trainer identifier validation."""
from __future__ import annotations

from uuid import uuid4

import pytest

from app import create_app
from app.kafka import NullEventProducer
from app.settings import Settings


def _client():
    settings = Settings(
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
    return create_app(settings, NullEventProducer()).test_client()


@pytest.mark.parametrize(
    ("method", "path", "body", "field"),
    [
        ("get", "/api/v1/trainers/not-a-uuid", None, "trainer_id"),
        ("patch", "/api/v1/trainers/not-a-uuid", {}, "trainer_id"),
        ("delete", "/api/v1/trainers/not-a-uuid", None, "trainer_id"),
        ("post", "/api/v1/members/not-a-uuid/memberships", {"plan_id": str(uuid4())}, "member_id"),
        ("get", "/api/v1/memberships/not-a-uuid", None, "membership_id"),
        ("patch", "/api/v1/memberships/not-a-uuid", {}, "membership_id"),
        ("delete", "/api/v1/memberships/not-a-uuid", None, "membership_id"),
    ],
)
def test_malformed_resource_ids_use_standard_validation_error(method, path, body, field):
    response = getattr(_client(), method)(path, headers={"X-API-Key": "test-key"}, json=body)

    assert response.status_code == 400
    assert response.is_json
    error = response.get_json()["error"]
    assert error["code"] == "validation_error"
    assert error["message"] == f"{field} must be a UUID"
    assert error["timestamp"]
    assert "correlation_id" in error

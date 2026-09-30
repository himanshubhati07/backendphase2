"""End-to-end PostgreSQL API flow with recorded post-commit events."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not (os.getenv("TEST_DATABASE_URL") and os.getenv("TEST_API_KEY")),
    reason="TEST_DATABASE_URL and TEST_API_KEY are required for PostgreSQL integration tests",
)

from app import create_app
from app.database.connection import TransactionManager
from app.settings import Settings


class RecordingProducer:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def publish(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))

    def close(self) -> None:
        pass


def _apply_migrations(database_url: str) -> None:
    manager = TransactionManager(database_url)
    with manager.transaction() as connection:
        with connection.cursor() as cursor:
            for migration in sorted(Path("migrations").glob("*.sql")):
                cursor.execute(migration.read_text())


@pytest.fixture
def client_and_events():
    database_url = os.environ["TEST_DATABASE_URL"]
    _apply_migrations(database_url)
    manager = TransactionManager(database_url)
    with manager.transaction() as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE attendance, memberships, membership_plans, trainers, members CASCADE")
    producer = RecordingProducer()
    settings = Settings(
        app_env="test", host="127.0.0.1", port=8000, database_url=database_url,
        api_keys=(os.environ["TEST_API_KEY"],), kafka_bootstrap_servers="unused:9092",
        kafka_client_id="integration-tests", kafka_topic="gym.events", log_level="CRITICAL",
        flask_secret_key="test-secret",
    )
    return create_app(settings, producer).test_client(), producer


def test_member_plan_membership_attendance_and_cancellation_flow(client_and_events) -> None:
    client, events = client_and_events
    headers = {"X-API-Key": os.environ["TEST_API_KEY"]}
    suffix = uuid4().hex

    created_member = client.post("/api/v1/members", headers=headers, json={
        "first_name": "Integration", "last_name": "Member", "email": f"member-{suffix}@example.test",
    })
    assert created_member.status_code == 201
    member = created_member.get_json()
    assert {"id", "email", "created_at"}.issubset(member)

    listed_members = client.get("/api/v1/members?page=1&per_page=20", headers=headers)
    assert listed_members.status_code == 200
    assert any(item["id"] == member["id"] for item in listed_members.get_json()["items"])

    created_plan = client.post("/api/v1/membership-plans", headers=headers, json={
        "name": f"Plan {suffix}", "duration_days": 1, "price": 10.00, "is_active": True,
    })
    assert created_plan.status_code == 201
    plan = created_plan.get_json()

    assigned = client.post(f"/api/v1/members/{member['id']}/memberships", headers=headers, json={"plan_id": plan["id"], "start_date": "2030-01-01"})
    assert assigned.status_code == 201
    membership = assigned.get_json()
    assert membership["plan_id"] == plan["id"]
    assert membership["end_date"] == "2030-01-02"

    patched = client.patch(f"/api/v1/memberships/{membership['id']}", headers=headers, json={"end_date": "2030-01-03"})
    assert patched.status_code == 200
    assert patched.get_json()["end_date"] == "2030-01-03"

    check_in = client.post(f"/api/v1/members/{member['id']}/attendance/check-in", headers=headers)
    assert check_in.status_code == 201
    attendance = check_in.get_json()
    check_out = client.patch(f"/api/v1/attendance/{attendance['id']}/check-out", headers=headers)
    assert check_out.status_code == 200
    assert check_out.get_json()["checked_out_at"] is not None

    history = client.get(f"/api/v1/members/{member['id']}/attendance?page=1&per_page=20", headers=headers)
    assert history.status_code == 200
    assert history.get_json()["total"] == 1
    checked_date = attendance["checked_in_at"][:10]
    filtered = client.get(f"/api/v1/attendance?member_id={member['id']}&date={checked_date}", headers=headers)
    assert filtered.status_code == 200
    assert filtered.get_json()["items"][0]["id"] == attendance["id"]

    cancelled = client.delete(f"/api/v1/memberships/{membership['id']}", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.get_json()["status"] == "cancelled"

    event_types = [event_type for event_type, _ in events.events]
    assert event_types == ["member.created", "membership.assigned", "attendance.marked", "attendance.marked", "membership.cancelled"]
    assert [payload["action"] for event_type, payload in events.events if event_type == "attendance.marked"] == ["check_in", "check_out"]

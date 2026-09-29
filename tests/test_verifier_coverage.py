"""Focused regression coverage for verifier-mandated API contracts."""
from __future__ import annotations

import logging
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from webtest import TestApp

from app.auth import hash_password
from app.config import ConfigurationError, Settings
from app.database import initialize_schema
from app.main import create_app
from app.models import Member, MemberMembershipStatus, User, UserRole


@pytest.fixture
def api(tmp_path, monkeypatch):
    """A fresh file database makes each API scenario independent."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "test-only-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'verifier.db'}")
    monkeypatch.setenv("CORS_ORIGINS", "https://allowed.example")
    application = create_app(Settings.from_environment())
    initialize_schema(application.config["engine"])
    session = application.config["session_factory"]()
    try:
        session.add(User(email="admin@example.test", password_hash=hash_password("AdminPass123!"), role=UserRole.ADMIN))
        session.commit()
    finally:
        session.close()
    yield TestApp(application)
    application.config["engine"].dispose()


def data(response):
    assert response.json["success"] is True, response.text
    return response.json["data"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def login(api):
    return data(api.post_json("/api/auth/login", {"email": "admin@example.test", "password": "AdminPass123!"}))["access_token"]


def register(api, email, *, role="member", phone="+15550100001"):
    return data(api.post_json("/api/auth/register", {
        "email": email, "password": "Password123!", "role": role,
        "profile": {"full_name": email.split("@")[0], "phone": phone},
    }, status=201))


def plan(api, token, **overrides):
    payload = {"name": "Zero-capable", "duration_days": 30, "price": "10.00", "features": ["gym"]}
    payload.update(overrides)
    return data(api.post_json("/api/membership-plans", payload, headers=headers(token), status=201))


def test_zero_and_negative_money_and_delete_deactivation(api):
    admin = login(api)
    member = register(api, "money-member@example.test", phone="+15550100002")
    member_id = member["user"]["profile"]["id"]
    free = plan(api, admin, name="Free", price=0)
    assert free["price"] == "0.00"
    membership = data(api.post_json(f"/api/members/{member_id}/memberships", {
        "plan_id": free["id"], "amount": 0,
    }, headers=headers(admin), status=201))
    assert membership["amount"] == "0.00"
    api.post_json("/api/membership-plans", {"name": "Bad plan", "duration_days": 1, "price": -0.01}, headers=headers(admin), status=422)
    api.post_json(f"/api/members/{member_id}/memberships", {"plan_id": free["id"], "amount": -1}, headers=headers(admin), status=422)
    deactivated = data(api.delete(f"/api/membership-plans/{free['id']}", headers=headers(admin)))
    assert deactivated["status"] == "inactive"
    assert free["id"] not in [item["id"] for item in data(api.get("/api/membership-plans", headers=headers(admin)))]


def test_pending_member_status_blocks_attendance_despite_active_membership(api):
    admin = login(api)
    member = register(api, "pending-member@example.test", phone="+15550100003")
    member_id = member["user"]["profile"]["id"]
    active_plan = plan(api, admin, name="Attendance")
    data(api.post_json(f"/api/members/{member_id}/memberships", {"plan_id": active_plan["id"]}, headers=headers(admin), status=201))
    session = api.app.config["session_factory"]()
    try:
        profile = session.get(Member, member_id)
        profile.membership_status = MemberMembershipStatus.PENDING
        session.commit()
    finally:
        session.close()
    denied = api.post_json("/api/attendance/check-in", {"member_id": member_id}, headers=headers(member["access_token"]), status=422)
    assert denied.json["error_code"] == "VALIDATION_ERROR"


def test_payment_card_fields_are_rejected_and_response_never_contains_them(api):
    admin = login(api)
    member = register(api, "card-member@example.test", phone="+15550100004")
    payload = {"member_id": member["user"]["profile"]["id"], "amount": "0", "currency": "USD",
               "payment_method": "card", "status": "pending", "payment_date": "2025-01-01T00:00:00Z",
               "transaction_id": "card-safe-transaction"}
    unsafe = dict(payload, card_number="4111111111111111", cvv="123")
    rejected = api.post_json("/api/payments", unsafe, headers=headers(admin), status=422)
    assert rejected.json["error_code"] == "VALIDATION_ERROR"
    created = data(api.post_json("/api/payments", payload, headers=headers(admin), status=201))
    rendered = api.get(f"/api/payments/{created['id']}", headers=headers(admin)).text.lower()
    assert "card_number" not in rendered and "4111111111111111" not in rendered and "cvv" not in rendered


def test_cors_security_headers_and_database_logs_are_redacted(api, monkeypatch, caplog):
    response = api.options("/api/health", headers={"Origin": "https://allowed.example"})
    assert response.headers["Access-Control-Allow-Origin"] == "https://allowed.example"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    for name, expected in {"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"}.items():
        assert response.headers[name] == expected

    token = login(api)

    def unavailable(*_args, **_kwargs):
        raise OperationalError("SELECT card_number FROM private_host", {}, RuntimeError("4111111111111111"))

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(Session, "get", unavailable)
    api.get("/api/auth/me", headers=headers(token), status=500)
    captured = "\n".join(record.getMessage() for record in caplog.records)
    assert "database_error_redacted" in captured
    for secret in ("SELECT", "private_host", "card_number", "4111111111111111", "Traceback"):
        assert secret not in captured


def test_trainer_workout_assignment_replacement_restriction_and_deactivation(api):
    admin = login(api)
    trainer = register(api, "workout-trainer@example.test", role="trainer", phone="+15550100005")
    member = register(api, "workout-member@example.test", phone="+15550100006")
    unrelated = register(api, "other-workout-member@example.test", phone="+15550100007")
    trainer_id, member_id = trainer["user"]["profile"]["id"], member["user"]["profile"]["id"]
    data(api.put(f"/api/trainers/{trainer_id}/members/{member_id}", {}, headers=headers(admin)))
    admin_created = data(api.post_json("/api/workout-plans", {
        "member_id": member_id, "trainer_id": trainer_id, "name": "Admin-created",
        "exercises": [{"exercise_name": "Press", "sets": 2, "weight": 5}],
    }, headers=headers(admin), status=201))
    assert admin_created["member_id"] == member_id
    invalid = api.post_json("/api/workout-plans", {"name": "Invalid", "exercises": [{"exercise_name": "Squat", "sets": 0}]}, headers=headers(trainer["access_token"]), status=422)
    assert invalid.json["error_code"] == "VALIDATION_ERROR"
    workout = data(api.post_json("/api/workout-plans", {
        "name": "Strength", "exercises": [{"exercise_name": "Squat", "sets": 3, "repetitions": 8, "weight": "0.00"}],
    }, headers=headers(trainer["access_token"]), status=201))
    assigned = data(api.put(f"/api/workout-plans/{workout['id']}/members/{member_id}", {}, headers=headers(trainer["access_token"])))
    assert assigned["member_id"] == member_id and assigned["trainer_id"] == trainer_id
    visible = data(api.get(f"/api/members/{member_id}/workout-plans", headers=headers(member["access_token"])))
    assert visible[0]["exercises"][0]["exercise_name"] == "Squat"
    api.get(f"/api/members/{member_id}/workout-plans", headers=headers(unrelated["access_token"]), status=403)
    updated = data(api.put_json(f"/api/workout-plans/{workout['id']}", {"exercises": [{"exercise_name": "Row", "duration": 20}]}, headers=headers(trainer["access_token"])))
    assert [exercise["exercise_name"] for exercise in updated["exercises"]] == ["Row"]
    deactivated = data(api.delete(f"/api/workout-plans/{workout['id']}", headers=headers(trainer["access_token"])))
    assert deactivated["status"] == "inactive"


def test_settings_requires_database_outside_test_and_reads_host_port(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "settings-secret")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        Settings.from_environment()
    monkeypatch.setenv("DATABASE_URL", "sqlite:///configured.db")
    monkeypatch.setenv("HOST", "127.0.0.9")
    monkeypatch.setenv("PORT", "9123")
    settings = Settings.from_environment()
    assert (settings.host, settings.port) == ("127.0.0.9", 9123)


def test_openapi_delete_nested_phone_oneof_and_method_not_allowed_contract(api):
    document = data(api.get("/api/openapi.json"))
    schemas, paths = document["components"]["schemas"], document["paths"]
    assert "delete" in paths["/api/membership-plans/{plan_id}"]
    assert "/api/membership-plans/{plan_id}/deactivate" not in paths
    registration = schemas["RegistrationRequest"]
    assert "phone" not in registration["properties"]
    assert registration["properties"]["profile"]["properties"]["phone"]["type"] == "string"
    assert len(schemas["CreateMembershipPlanRequest"]["properties"]["features"]["oneOf"]) == 2
    assert "METHOD_NOT_ALLOWED" in schemas["Error"]["properties"]["error_code"]["enum"]
    assert "405" in paths["/api/membership-plans/{plan_id}"]["delete"]["responses"]


def test_pending_status_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    """Exercise the real Alembic revision, including its pending-to-cancelled downgrade."""
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    monkeypatch.setenv("DATABASE_URL", database_url)
    command.upgrade(config, "20250103_0003")
    engine = sa.create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(sa.text("INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount, payment_status, status) VALUES (1, 1, '2025-01-01', '2025-01-31', 0, 'PENDING', 'PENDING')"))
            assert connection.scalar(sa.text("SELECT status FROM memberships")) == "PENDING"
        command.downgrade(config, "20250102_0002")
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT status FROM memberships")) == "CANCELLED"
    finally:
        engine.dispose()

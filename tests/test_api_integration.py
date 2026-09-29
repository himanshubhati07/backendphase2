"""API-level integration coverage against an isolated SQLite schema."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from webtest import TestApp

from app.auth import hash_password
from app.config import Settings
from app.database import initialize_schema
from app.main import create_app
from app.models import User, UserRole


@pytest.fixture
def api(tmp_path, monkeypatch):
    """Build a fresh application and file-backed SQLite database for each test."""
    monkeypatch.setenv("JWT_SECRET", "test-only-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'gym-test.db'}")
    monkeypatch.setenv("APP_ENV", "test")
    settings = Settings.from_environment()
    application = create_app(settings)
    initialize_schema(application.config["engine"])

    # Public registration deliberately cannot create administrators; seed only that
    # bootstrap identity through the ORM, while exercising all domain flows over HTTP.
    session = application.config["session_factory"]()
    try:
        session.add(User(email="admin@example.test", password_hash=hash_password("AdminPass123"), role=UserRole.ADMIN))
        session.commit()
    finally:
        session.close()
    yield TestApp(application)
    application.config["engine"].dispose()


def body(response):
    assert response.json["success"] is True, response.text
    return response.json["data"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def register(api, *, email, role="member", name="Test Person", phone="+15550000001"):
    response = api.post_json("/api/auth/register", {
        "email": email, "password": "Password123", "role": role,
        "profile": {"full_name": name, "phone": phone},
    }, status=201)
    return body(response)


def login(api, email="admin@example.test", password="AdminPass123"):
    return body(api.post_json("/api/auth/login", {"email": email, "password": password}))["access_token"]


def create_plan(api, admin_token):
    return body(api.post_json("/api/plans", {
        "name": "Monthly", "description": "30 day access", "duration_days": 30, "price": "49.99",
    }, headers=auth(admin_token), status=201))


def test_auth_registration_login_refresh_me_and_rejects_refresh_as_access(api):
    registered = register(api, email="member@example.test", phone="+15550000011")
    assert registered["user"]["role"] == "member"
    assert registered["user"]["profile"]["email"] == "member@example.test"

    api.post_json("/api/auth/register", {
        "email": "admin-attempt@example.test", "password": "Password123", "role": "admin",
        "profile": {"full_name": "No Admin", "phone": "+15550000012"},
    }, status=422)
    api.post_json("/api/auth/login", {"email": "member@example.test", "password": "wrong"}, status=401)

    tokens = body(api.post_json("/api/auth/login", {"email": "member@example.test", "password": "Password123"}))
    me = body(api.get("/api/auth/me", headers=auth(tokens["access_token"])))
    assert me["email"] == "member@example.test"
    refreshed = body(api.post_json("/api/auth/refresh", {"refresh_token": tokens["refresh_token"]}))
    assert refreshed["access_token"] != tokens["access_token"]
    api.get("/api/auth/me", headers=auth(tokens["refresh_token"]), status=401)


def test_member_trainer_assignment_membership_and_attendance_lifecycle(api):
    admin = login(api)
    member_tokens = register(api, email="member@example.test", name="Member One", phone="+15550000021")
    trainer_tokens = register(api, email="trainer@example.test", role="trainer", name="Trainer One", phone="+15550000022")
    member_id = member_tokens["user"]["profile"]["id"]
    trainer_id = trainer_tokens["user"]["profile"]["id"]

    assigned = body(api.put(f"/api/trainers/{trainer_id}/members/{member_id}", {}, headers=auth(admin)))
    assert assigned["trainer_id"] == trainer_id
    trainer_members = body(api.get("/api/members", headers=auth(trainer_tokens["access_token"])))
    assert [item["id"] for item in trainer_members] == [member_id]

    plan = create_plan(api, admin)
    membership = body(api.post_json(f"/api/members/{member_id}/memberships", {"plan_id": plan["id"]}, headers=auth(admin), status=201))
    assert membership["status"] == "active"
    active = body(api.get(f"/api/members/{member_id}/memberships/active", headers=auth(member_tokens["access_token"])))
    assert active["id"] == membership["id"]

    attendance = body(api.post_json("/api/attendance/check-in", {"member_id": member_id, "notes": "morning"}, headers=auth(trainer_tokens["access_token"]), status=201))
    assert attendance["trainer_id"] == trainer_id
    api.post_json("/api/attendance/check-in", {"member_id": member_id}, headers=auth(trainer_tokens["access_token"]), status=409)
    checked_out = body(api.post(f"/api/attendance/{attendance['id']}/check-out", headers=auth(member_tokens["access_token"])))
    assert checked_out["checked_out_at"] is not None
    history = body(api.get(f"/api/members/{member_id}/attendance", headers=auth(member_tokens["access_token"])))
    assert len(history) == 1


def test_payment_rejects_card_data_scopes_visibility_and_maps_unique_db_failure(api):
    admin = login(api)
    member_one = register(api, email="one@example.test", phone="+15550000031")
    member_two = register(api, email="two@example.test", phone="+15550000032")
    member_id = member_one["user"]["profile"]["id"]
    base = {"member_id": member_id, "amount": "19.99", "currency": "usd", "payment_method": "card", "status": "paid", "payment_date": "2025-01-01T09:00:00Z", "transaction_id": "txn-unique"}

    api.post_json("/api/payments", {**base, "card_number": "4111111111111111"}, headers=auth(admin), status=422)
    payment = body(api.post_json("/api/payments", base, headers=auth(admin), status=201))
    assert "card_number" not in payment
    assert payment["currency"] == "USD"
    # This exercises the database IntegrityError path without exposing driver details.
    duplicate = api.post_json("/api/payments", base, headers=auth(admin), status=409)
    assert duplicate.json["error_code"] == "CONFLICT"
    api.get(f"/api/payments/{payment['id']}", headers=auth(member_two["access_token"]), status=403)
    visible = body(api.get("/api/payments", headers=auth(member_one["access_token"])))
    assert [item["id"] for item in visible] == [payment["id"]]


def test_workout_validation_and_trainer_ownership_boundaries(api):
    admin = login(api)
    first_member = register(api, email="first@example.test", phone="+15550000041")
    second_member = register(api, email="second@example.test", phone="+15550000042")
    trainer = register(api, email="trainer@example.test", role="trainer", phone="+15550000043")
    first_id = first_member["user"]["profile"]["id"]
    second_id = second_member["user"]["profile"]["id"]
    trainer_id = trainer["user"]["profile"]["id"]
    api.put(f"/api/trainers/{trainer_id}/members/{first_id}", {}, headers=auth(admin))

    invalid = api.post_json("/api/workout-plans", {"member_id": first_id, "name": "Bad", "exercises": [{"exercise_name": "Squat", "sets": 0}]}, headers=auth(trainer["access_token"]), status=422)
    assert invalid.json["error_code"] == "VALIDATION_ERROR"
    plan = body(api.post_json("/api/workout-plans", {"member_id": first_id, "name": "Strength", "exercises": [{"exercise_name": "Squat", "sets": 3, "repetitions": 8, "weight": "50.00"}]}, headers=auth(trainer["access_token"]), status=201))
    assert plan["trainer_id"] == trainer_id
    api.put_json(f"/api/workout-plans/{plan['id']}/members/{second_id}", {}, headers=auth(trainer["access_token"]), status=403)
    updated = body(api.put_json(f"/api/workout-plans/{plan['id']}", {"exercises": [{"exercise_name": "Deadlift", "sets": 4, "repetitions": 5}]}, headers=auth(trainer["access_token"])))
    assert [exercise["exercise_name"] for exercise in updated["exercises"]] == ["Deadlift"]
    own_plans = body(api.get(f"/api/members/{first_id}/workout-plans", headers=auth(first_member["access_token"])))
    assert own_plans[0]["id"] == plan["id"]
    api.get(f"/api/members/{first_id}/workout-plans", headers=auth(second_member["access_token"]), status=403)

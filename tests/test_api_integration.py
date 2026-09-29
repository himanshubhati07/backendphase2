"""API-level integration coverage against an isolated SQLite schema."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
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
    session = application.config["session_factory"]()
    try:
        session.add(User(email="admin@example.test", password_hash=hash_password("AdminPass123!"), role=UserRole.ADMIN))
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
        "email": email, "password": "Password123!", "role": role,
        "profile": {"full_name": name, "phone": phone},
    }, status=201)
    return body(response)


def login(api, email="admin@example.test", password="AdminPass123!"):
    return body(api.post_json("/api/auth/login", {"email": email, "password": password}))["access_token"]


def create_plan(api, admin_token, **overrides):
    payload = {"name": "Monthly", "description": "30 day access", "duration_days": 30,
               "price": "49.99", "features": ["weights", "classes"]}
    payload.update(overrides)
    return body(api.post_json("/api/membership-plans", payload, headers=auth(admin_token), status=201))


def assign_active_membership(api, admin_token, member_id, plan=None):
    plan = plan or create_plan(api, admin_token)
    return body(api.post_json(f"/api/members/{member_id}/memberships", {"plan_id": plan["id"]},
                              headers=auth(admin_token), status=201))


def seed_profileless_user(api, email, role):
    session = api.app.config["session_factory"]()
    try:
        user = User(email=email, password_hash=hash_password("Profileless123!"), role=role)
        session.add(user)
        session.commit()
        return user.id
    finally:
        session.close()


def test_auth_password_policy_expiry_refresh_and_me(api):
    weak = api.post_json("/api/auth/register", {
        "email": "weak@example.test", "password": "password123", "role": "member",
        "profile": {"full_name": "Weak Password", "phone": "+15550000010"},
    }, status=422)
    assert weak.json["error_code"] == "VALIDATION_ERROR"

    registered = register(api, email="member@example.test", phone="+15550000011")
    tokens = body(api.post_json("/api/auth/login", {"email": "member@example.test", "password": "Password123!"}))
    assert body(api.get("/api/auth/me", headers=auth(tokens["access_token"])))["email"] == "member@example.test"
    assert body(api.post_json("/api/auth/refresh", {"refresh_token": tokens["refresh_token"]}))["access_token"] != tokens["access_token"]
    api.get("/api/auth/me", headers=auth(tokens["refresh_token"]), status=401)

    settings = api.app.config["settings"]
    expired = jwt.encode({"sub": "1", "role": "admin", "type": "access", "iss": settings.jwt_issuer,
                          "iat": datetime.now(timezone.utc) - timedelta(minutes=2),
                          "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, settings.jwt_secret, algorithm="HS256")
    rejected = api.get("/api/auth/me", headers=auth(expired), status=401)
    assert rejected.json["error_code"] == "UNAUTHENTICATED"
    assert registered["user"]["role"] == "member"


def test_member_and_trainer_crud_search_deactivation_duplicate_and_rbac(api):
    admin = login(api)
    profileless_member = seed_profileless_user(api, "member-without-profile@example.test", UserRole.MEMBER)
    profileless_trainer = seed_profileless_user(api, "trainer-without-profile@example.test", UserRole.TRAINER)
    created_member = body(api.post_json("/api/members", {"user_id": profileless_member, "full_name": "Created Member",
        "email": "created-member@example.test", "phone": "+15550000020", "joining_date": "2025-01-01"}, headers=auth(admin), status=201))
    created_trainer = body(api.post_json("/api/trainers", {"user_id": profileless_trainer, "name": "Created Trainer",
        "email": "created-trainer@example.test", "phone": "+15550000024", "joining_date": "2025-01-01"}, headers=auth(admin), status=201))
    assert created_member["full_name"] == "Created Member" and created_trainer["name"] == "Created Trainer"
    member = register(api, email="member@example.test", name="Member One", phone="+15550000021")
    other = register(api, email="other@example.test", name="Other Member", phone="+15550000022")
    trainer = register(api, email="trainer@example.test", role="trainer", name="Trainer One", phone="+15550000023")
    member_id, trainer_id = member["user"]["profile"]["id"], trainer["user"]["profile"]["id"]

    api.get("/api/members", headers=auth(member["access_token"]), status=403)
    assigned = body(api.put(f"/api/trainers/{trainer_id}/members/{member_id}", {}, headers=auth(admin)))
    assert assigned["trainer_id"] == trainer_id
    assert body(api.get(f"/api/members/{member_id}", headers=auth(member["access_token"])))["id"] == member_id
    assert body(api.get(f"/api/trainers/{trainer_id}", headers=auth(trainer["access_token"])))["id"] == trainer_id
    assert [row["id"] for row in body(api.get("/api/members?q=Member%20One", headers=auth(admin)))] == [member_id]
    updated = body(api.put_json(f"/api/members/{member_id}", {"address": "1 Fitness Way"}, headers=auth(member["access_token"])))
    assert updated["address"] == "1 Fitness Way"
    api.put_json(f"/api/members/{member_id}", {"email": "other@example.test"}, headers=auth(admin), status=409)
    trainer_update = body(api.put_json(f"/api/trainers/{trainer_id}", {"experience": 5}, headers=auth(trainer["access_token"])))
    assert trainer_update["experience"] == 5
    api.delete(f"/api/trainers/{trainer_id}", headers=auth(member["access_token"]), status=403)
    assert body(api.delete(f"/api/trainers/{trainer_id}", headers=auth(admin)))["status"] == "inactive"
    assert other["user"]["profile"]["id"] != member_id


def test_membership_plan_canonical_features_status_and_lifecycle(api):
    admin = login(api)
    member = register(api, email="member@example.test", phone="+15550000031")
    plan = create_plan(api, admin)
    assert plan["features"] == ["weights", "classes"] and plan["status"] == "active"
    # Bottle's catch-all OPTIONS route makes a request to an unregistered path
    # resolve as method-not-allowed; either outcome proves no legacy GET handler exists.
    assert api.get("/api/plans", headers=auth(admin), status=(404, 405)).status_int in {404, 405}
    assert body(api.patch_json(f"/api/membership-plans/{plan['id']}", {"features": {"pool": True}}, headers=auth(admin)))["features"] == {"pool": True}

    membership = body(api.post_json(f"/api/members/{member['user']['profile']['id']}/memberships", {
        "plan_id": plan["id"], "amount": "39.50", "payment_status": "pending", "status": "active",
    }, headers=auth(admin), status=201))
    assert membership["amount"] == "39.50" and membership["payment_status"] == "pending"
    history = body(api.get(f"/api/members/{membership['member_id']}/memberships", headers=auth(member["access_token"])))
    assert [row["id"] for row in history] == [membership["id"]]
    renewed = body(api.post(f"/api/memberships/{membership['id']}/renew", headers=auth(admin), status=201))
    assert renewed["payment_status"] == "pending" and renewed["amount"] == "49.99"
    assert body(api.post(f"/api/memberships/{membership['id']}/cancel", headers=auth(admin)))["status"] == "cancelled"
    assert body(api.post(f"/api/membership-plans/{plan['id']}/deactivate", headers=auth(admin)))["status"] == "inactive"


def test_attendance_checkout_reports_and_inactive_rejection(api):
    admin = login(api)
    member = register(api, email="member@example.test", phone="+15550000041")
    member_id = member["user"]["profile"]["id"]
    assign_active_membership(api, admin, member_id)
    attendance = body(api.post_json("/api/attendance/check-in", {"member_id": member_id}, headers=auth(member["access_token"]), status=201))
    assert attendance["check_in_at"] is not None
    checked_out = body(api.post_json("/api/attendance/check-out", {"attendance_id": attendance["id"]}, headers=auth(member["access_token"])))
    assert checked_out["checked_out_at"] is not None
    today = date.today().isoformat()
    assert [row["id"] for row in body(api.get(f"/api/attendance/daily?date={today}", headers=auth(admin)))] == [attendance["id"]]
    assert [row["id"] for row in body(api.get(f"/api/attendance?start_date={today}&end_date={today}", headers=auth(admin)))] == [attendance["id"]]
    body(api.delete(f"/api/members/{member_id}", headers=auth(admin)))
    rejected = api.post_json("/api/attendance/check-in", {"member_id": member_id, "attended_on": (date.today() + timedelta(days=1)).isoformat()}, headers=auth(member["access_token"]), status=422)
    assert rejected.json["error_code"] == "VALIDATION_ERROR"


def test_payment_status_update_duplicate_transaction_and_visibility(api):
    admin = login(api)
    member = register(api, email="one@example.test", phone="+15550000051")
    other = register(api, email="two@example.test", phone="+15550000052")
    payload = {"member_id": member["user"]["profile"]["id"], "amount": "19.99", "currency": "usd",
               "payment_method": "card", "status": "pending", "payment_date": "2025-01-01T09:00:00Z", "transaction_id": "txn-unique"}
    payment = body(api.post_json("/api/payments", payload, headers=auth(admin), status=201))
    assert body(api.patch_json(f"/api/payments/{payment['id']}/status", {"status": "paid"}, headers=auth(admin)))["status"] == "paid"
    duplicate = api.post_json("/api/payments", payload, headers=auth(admin), status=409)
    assert duplicate.json["error_code"] == "CONFLICT"
    api.get(f"/api/payments/{payment['id']}", headers=auth(other["access_token"]), status=403)
    assert [row["id"] for row in body(api.get("/api/payments", headers=auth(member["access_token"]))) ] == [payment["id"]]


def test_sqlalchemy_failure_is_safe_database_error(api, monkeypatch):
    token = login(api)

    def unavailable(*_args, **_kwargs):
        raise OperationalError("SELECT secret_column FROM private_host", {}, RuntimeError("driver secret"))

    monkeypatch.setattr(Session, "get", unavailable)
    response = api.get("/api/auth/me", headers=auth(token), status=500)
    assert response.json == {"success": False, "message": "A database error occurred", "error_code": "DATABASE_ERROR"}
    assert "secret" not in response.text.lower() and "private_host" not in response.text


def test_openapi_matches_canonical_routes_and_typed_parameters(api):
    document = body(api.get("/api/openapi.json"))
    paths = document["paths"]
    assert "/api/membership-plans" in paths
    assert "/api/plans" not in paths and "/api/attendance/{attendance_id}/check-out" not in paths
    assert "post" in paths["/api/membership-plans/{plan_id}/deactivate"]
    assert "delete" not in paths["/api/membership-plans/{plan_id}"]
    attendance_parameters = paths["/api/attendance"]["get"]["parameters"]
    assert {item["name"]: item["schema"]["format"] for item in attendance_parameters} == {"start_date": "date", "end_date": "date"}
    checkout = document["components"]["schemas"]["CheckOutRequest"]
    assert checkout["required"] == ["attendance_id"] and checkout["properties"]["attendance_id"]["type"] == "integer"

"""Unit coverage for the attendance verifier remediation."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from flask import Flask

from app.controllers.attendance import create_attendance_blueprint
from app.dtos.attendance import AttendanceDTO
from app.services.attendance import AttendanceMemberNotFoundError, AttendanceService


class RouteService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.attendance = AttendanceDTO(uuid4(), uuid4(), datetime.now(UTC), None)

    def check_in(self, member_id):
        self.calls.append(("check_in", member_id))
        return self.attendance

    def check_out(self, attendance_id):
        self.calls.append(("check_out", attendance_id))
        return self.attendance

    def member_history(self, member_id, **kwargs):
        self.calls.append(("member_history", member_id))
        if member_id == self.attendance.member_id:
            raise AttendanceMemberNotFoundError(f"Member {member_id} was not found")
        return [], 0

    def search(self, **kwargs):
        self.calls.append(("search", kwargs))
        return [], 0


@pytest.fixture
def route_client():
    service = RouteService()
    app = Flask(__name__)
    app.register_blueprint(create_attendance_blueprint(service), url_prefix="/api/v1")
    return app.test_client(), service


@pytest.mark.parametrize("body", [b"{}", b"null", b"not-json", b" "])
def test_timestamp_mutations_reject_every_nonempty_body(route_client, body: bytes) -> None:
    client, service = route_client
    member_id = uuid4()
    attendance_id = uuid4()

    checked_in = client.post(f"/api/v1/members/{member_id}/attendance/check-in", data=body)
    checked_out = client.patch(f"/api/v1/attendance/{attendance_id}/check-out", data=body)

    assert checked_in.status_code == checked_out.status_code == 400
    assert checked_in.get_json()["error"]["code"] == "validation_error"
    assert checked_out.get_json()["error"]["code"] == "validation_error"
    assert service.calls == []


def test_timestamp_mutations_accept_an_absent_or_empty_body(route_client) -> None:
    client, service = route_client
    member_id = uuid4()
    attendance_id = uuid4()

    assert client.post(f"/api/v1/members/{member_id}/attendance/check-in").status_code == 201
    assert client.patch(f"/api/v1/attendance/{attendance_id}/check-out", data=b"").status_code == 200
    assert [call[0] for call in service.calls] == ["check_in", "check_out"]


def test_member_history_missing_member_is_404_and_uuid_stays_a_400(route_client) -> None:
    client, service = route_client

    missing = client.get(f"/api/v1/members/{service.attendance.member_id}/attendance")
    malformed = client.get("/api/v1/members/not-a-uuid/attendance")

    assert missing.status_code == 404
    assert missing.get_json()["error"]["code"] == "member_not_found"
    assert malformed.status_code == 400
    assert malformed.get_json()["error"]["code"] == "validation_error"


def test_attendance_filters_allow_only_member_date_and_pagination(route_client) -> None:
    client, service = route_client

    accepted = client.get(f"/api/v1/attendance?member_id={uuid4()}&date=2025-01-01&page=1&per_page=2")
    retired_range = client.get("/api/v1/attendance?date_from=2025-01-01")

    assert accepted.status_code == 200
    assert retired_range.status_code == 400
    assert retired_range.get_json()["error"]["code"] == "validation_error"
    assert service.calls[0][0] == "search"


class TransactionRecorder:
    def __init__(self) -> None:
        self.committed = False

    @contextmanager
    def transaction(self):
        yield object()
        self.committed = True


class ServiceRepository:
    def __init__(self, exists: bool) -> None:
        self.exists = exists
        self.check_in_called = False

    def member_exists(self, connection, member_id):
        return self.exists

    def check_in(self, connection, member_id):
        self.check_in_called = True
        return AttendanceDTO(uuid4(), member_id, datetime.now(UTC), None)


def test_check_in_missing_member_rolls_back_and_does_not_publish() -> None:
    transactions = TransactionRecorder()
    repository = ServiceRepository(exists=False)
    events: list[tuple[str, dict]] = []
    service = AttendanceService(transactions, repository, type("Producer", (), {"publish": lambda _, kind, payload: events.append((kind, payload))})())

    with pytest.raises(AttendanceMemberNotFoundError):
        service.check_in(uuid4())

    assert not repository.check_in_called
    assert not transactions.committed
    assert events == []

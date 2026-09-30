"""PostgreSQL integration coverage for the attendance lifecycle.

These tests intentionally exercise the repository through the service's real
TransactionManager. They require an explicitly configured test database and
API key, and never run against an implicit local database.
"""
from __future__ import annotations

import os
from datetime import date
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not (os.getenv("TEST_DATABASE_URL") and os.getenv("TEST_API_KEY")),
    reason="TEST_DATABASE_URL and TEST_API_KEY are required for PostgreSQL integration tests",
)

from app.database.connection import TransactionManager
from app.repositories.attendance import AttendanceRepository
from app.services.attendance import AttendanceService


class RecordingProducer:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def publish(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))


@pytest.fixture
def attendance_service():
    transactions = TransactionManager(os.environ["TEST_DATABASE_URL"])
    producer = RecordingProducer()
    return AttendanceService(transactions, AttendanceRepository(), producer), transactions, producer


@pytest.fixture
def member_id(attendance_service):
    _, transactions, _ = attendance_service
    member = uuid4()
    with transactions.transaction() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO members (id, first_name, last_name, email)
                   VALUES (%s, %s, %s, %s)""",
                (member, "Attendance", "Integration", f"attendance-{member}@example.test"),
            )
    try:
        yield member
    finally:
        # The schema deliberately uses RESTRICT, so delete dependent rows first.
        with transactions.transaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM attendance WHERE member_id = %s", (member,))
                cursor.execute("DELETE FROM members WHERE id = %s", (member,))


def test_check_in_and_check_out_publish_after_commit(attendance_service, member_id: UUID) -> None:
    service, _, producer = attendance_service

    checked_in = service.check_in(member_id)
    checked_out = service.check_out(checked_in.id)

    assert checked_in.member_id == member_id
    assert checked_out.checked_out_at is not None
    assert producer.events == [
        ("attendance.marked", {"action": "check_in", "attendance": checked_in.to_dict()}),
        ("attendance.marked", {"action": "check_out", "attendance": checked_out.to_dict()}),
    ]


def test_history_and_exact_date_filtering(attendance_service, member_id: UUID) -> None:
    service, _, _ = attendance_service
    checked_in = service.check_in(member_id)
    service.check_out(checked_in.id)

    history, history_total = service.member_history(member_id, page=1, per_page=20, checked_in_on=date.today())
    global_items, global_total = service.search(page=1, per_page=20, member_id=member_id, checked_in_on=date.today())
    missing_items, missing_total = service.search(page=1, per_page=20, member_id=member_id, checked_in_on=date(1999, 1, 1))

    assert history_total == global_total == 1
    assert [item.id for item in history] == [checked_in.id]
    assert [item.id for item in global_items] == [checked_in.id]
    assert missing_items == []
    assert missing_total == 0

    # A range remains supported and includes the entire supplied end date.
    ranged, ranged_total = service.member_history(member_id, page=1, per_page=20, checked_in_from=date.today(), checked_in_to=date.today())
    assert ranged_total == 1
    assert ranged[0].id == checked_in.id

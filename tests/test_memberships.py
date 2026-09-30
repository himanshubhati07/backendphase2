from contextlib import contextmanager
from datetime import date
from uuid import uuid4

import pytest

from app.errors import ValidationError
from app.services.memberships import MembershipService


class Transactions:
    @contextmanager
    def transaction(self):
        yield object()


class Events:
    def __init__(self):
        self.published = []

    def publish(self, event_type, payload):
        self.published.append((event_type, payload))


class Repository:
    def __init__(self):
        self.plan = {"id": uuid4(), "duration_days": 30, "is_active": True}
        self.created = None
        self.current = {
            "id": uuid4(), "member_id": uuid4(), "plan_id": self.plan["id"],
            "start_date": date(2030, 1, 1), "end_date": date(2030, 1, 31), "status": "active",
        }

    def get_member(self, connection, member_id, lock=False):
        return {"id": member_id}

    def get_plan(self, connection, plan_id, active_only=False):
        return self.plan if plan_id == self.plan["id"] else None

    def find_active_for_member(self, connection, member_id):
        return None

    def create_membership(self, connection, **kwargs):
        self.created = kwargs
        return {"id": kwargs["membership_id"], **kwargs, "status": "active"}

    def get_membership(self, connection, membership_id, lock=False):
        return self.current

    def update_active_membership(self, connection, **kwargs):
        self.updated = kwargs
        return {**self.current, **kwargs}


def service():
    repository, events = Repository(), Events()
    return MembershipService(Transactions(), repository, events), repository


def test_assignment_uses_plan_id_and_exclusive_duration_end():
    subject, repository = service()
    member_id = uuid4()

    result = subject.assign(member_id, {"plan_id": str(repository.plan["id"]), "start_date": "2030-01-01"})

    assert result["plan_id"] == str(repository.plan["id"])
    assert repository.created["end_date"] == date(2030, 1, 31)


@pytest.mark.parametrize("payload", [
    {"membership_plan_id": str(uuid4())},
    {"plan_id": "not-a-uuid"},
    {"plan_id": str(uuid4()), "start_date": "2030-02-30"},
])
def test_assignment_rejects_legacy_unknown_uuid_and_date(payload):
    subject, _ = service()
    with pytest.raises(ValidationError):
        subject.assign(uuid4(), payload)


def test_assignment_requires_strictly_later_explicit_end_date():
    subject, repository = service()
    with pytest.raises(ValidationError, match="end_date must be later"):
        subject.assign(uuid4(), {"plan_id": str(repository.plan["id"]), "start_date": "2030-01-02", "end_date": "2030-01-02"})


def test_patch_recomputes_omitted_end_when_start_changes():
    subject, repository = service()
    subject.patch(repository.current["id"], {"start_date": "2030-02-01"})
    assert repository.updated["start_date"] == date(2030, 2, 1)
    assert repository.updated["end_date"] == date(2030, 3, 3)


def test_membership_blueprint_routes_are_relative_to_api_prefix_and_parse_string_ids():
    from flask import Flask
    from app.controllers.memberships import create_memberships_blueprint

    app = Flask(__name__)
    app.register_blueprint(create_memberships_blueprint(service()[0]), url_prefix="/api/v1")
    paths = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/members/<member_id>/memberships" in paths
    assert "/api/v1/memberships/<membership_id>" in paths
    assert not any("<uuid:" in path for path in paths)
    assert "/api/v1/api/v1/members/<member_id>/memberships" not in paths


def test_plan_creation_rejects_unknown_fields():
    subject, _ = service()

    with pytest.raises(ValidationError, match="only name"):
        subject.create_plan({
            "name": "Monthly", "duration_days": 30, "price": 25,
            "unexpected": True,
        })


def test_membership_plan_openapi_price_is_a_number():
    from app.openapi import openapi_document

    plan = openapi_document()["components"]["schemas"]["MembershipPlan"]
    assert plan["properties"]["price"] == {"type": "number", "minimum": 0}
    assert openapi_document()["components"]["schemas"]["MembershipPlanWrite"]["additionalProperties"] is False


def test_assignment_route_requires_json_object():
    from flask import Flask
    from app.controllers.memberships import create_memberships_blueprint

    app = Flask(__name__)
    app.register_error_handler(ValidationError, lambda error: ({"error": error.code}, 400))
    app.register_blueprint(create_memberships_blueprint(service()[0]), url_prefix="/api/v1")
    response = app.test_client().post(f"/api/v1/members/{uuid4()}/memberships", json=["not", "an", "object"])
    assert response.status_code == 400

"""Flask routes for membership plans and membership lifecycle operations."""
from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from app.errors import ValidationError
from app.services.memberships import MembershipService
from app.validation import require_uuid


def _json_object(*, allow_empty: bool = False) -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if payload is None and allow_empty:
        return {}
    if not isinstance(payload, dict):
        raise ValidationError("request body must be a JSON object")
    return payload


def create_memberships_blueprint(service: MembershipService) -> Blueprint:
    """Create the injectable membership blueprint.

    Application wiring owns construction of the transaction manager, repository,
    event producer, and registration of this blueprint.
    """
    # The application registers this resource beneath /api/v1; keeping route
    # declarations relative prevents an accidental /api/v1/api/v1 prefix.
    blueprint = Blueprint("memberships", __name__)

    @blueprint.post("/membership-plans")
    def create_membership_plan():
        result = service.create_plan(_json_object())
        return jsonify(result), 201

    @blueprint.post("/members/<member_id>/memberships")
    def assign_membership(member_id: str):
        result = service.assign(require_uuid(member_id, "member_id"), _json_object())
        return jsonify(result), 201

    @blueprint.get("/memberships/<membership_id>")
    def get_membership(membership_id: str):
        return jsonify(service.get(require_uuid(membership_id, "membership_id"))), 200

    @blueprint.patch("/memberships/<membership_id>")
    def patch_membership(membership_id: str):
        return jsonify(service.patch(require_uuid(membership_id, "membership_id"), _json_object())), 200

    @blueprint.delete("/memberships/<membership_id>")
    def cancel_membership(membership_id: str):
        return jsonify(service.cancel(require_uuid(membership_id, "membership_id"), _json_object(allow_empty=True))), 200

    return blueprint

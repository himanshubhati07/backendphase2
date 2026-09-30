"""Flask route registration for the member resource."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import Blueprint, jsonify, request

from app.services.members import MemberService
from app.validation import optional_date, parse_pagination, require_json_object, require_uuid


def register_routes(blueprint: Blueprint, service: MemberService) -> None:
    """Attach member CRUD routes to a preconfigured versioned blueprint."""

    def create_member() -> tuple[Any, int]:
        payload = _member_payload(require_json_object())
        return jsonify(service.create(payload)), 201

    def get_member(member_id: str) -> Any:
        return jsonify(service.get(require_uuid(member_id, "member_id")))

    def update_member(member_id: str) -> Any:
        payload = _member_payload(require_json_object())
        return jsonify(service.update(require_uuid(member_id, "member_id"), payload))

    def delete_member(member_id: str) -> tuple[str, int]:
        service.delete(require_uuid(member_id, "member_id"))
        return "", 204

    def list_members() -> Any:
        page, per_page = parse_pagination(request.args)
        return jsonify(service.list(page, per_page))

    _register(blueprint, "/members", "members_create", ["POST"], create_member)
    _register(blueprint, "/members", "members_list", ["GET"], list_members)
    _register(blueprint, "/members/<member_id>", "members_get", ["GET"], get_member)
    _register(blueprint, "/members/<member_id>", "members_update", ["PATCH"], update_member)
    _register(blueprint, "/members/<member_id>", "members_delete", ["DELETE"], delete_member)


def _register(
    blueprint: Blueprint,
    rule: str,
    endpoint: str,
    methods: list[str],
    view_func: Callable[..., Any],
) -> None:
    blueprint.add_url_rule(rule, endpoint=endpoint, view_func=view_func, methods=methods)


def _member_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse member-specific wire values before they reach the service layer."""
    if "date_of_birth" in payload:
        payload = dict(payload)
        payload["date_of_birth"] = optional_date(payload, "date_of_birth")
    return payload

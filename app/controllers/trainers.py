"""Flask route registration for the trainer resource group.

Authentication is intentionally not attached here: the application-level API
blueprint applies its shared API-key policy to every registered business route.
"""
from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from app.services.trainers import TrainerService
from app.validation import (
    optional_string,
    parse_pagination,
    reject_unknown_fields,
    require_uuid,
    require_json_object,
    required_string,
)

_CREATE_FIELDS = frozenset({"first_name", "last_name", "email", "phone", "specialization"})
_REQUIRED_FIELDS = ("first_name", "last_name", "email")


def _payload(*, partial: bool) -> dict[str, Any]:
    payload = require_json_object()
    reject_unknown_fields(payload, _CREATE_FIELDS)
    if partial and not payload:
        # ValidationError is deliberately supplied by the shared validation
        # contract; a blank PATCH is never a meaningful profile update.
        required_string({}, "at_least_one_field")

    result: dict[str, Any] = {}
    for name in _REQUIRED_FIELDS:
        if not partial or name in payload:
            result[name] = required_string(payload, name)
    for name in ("phone", "specialization"):
        if name in payload:
            result[name] = optional_string(payload, name)
    return result


def register_routes(blueprint: Blueprint, service: TrainerService) -> None:
    """Attach the exact ``/api/v1/trainers`` routes to an API blueprint.

    The supplied blueprint is expected to have the ``/api/v1`` prefix.  Keeping
    the service in this closure avoids Flask global state and makes route tests
    able to inject a small service fake.
    """

    @blueprint.post("/trainers")
    def create_trainer():
        return jsonify(service.create(_payload(partial=False))), 201

    @blueprint.get("/trainers")
    def list_trainers():
        page, per_page = parse_pagination(request.args)
        return jsonify(service.list(page=page, per_page=per_page))

    @blueprint.get("/trainers/<trainer_id>")
    def get_trainer(trainer_id: str):
        return jsonify(service.get(require_uuid(trainer_id, "trainer_id")))

    @blueprint.patch("/trainers/<trainer_id>")
    def update_trainer(trainer_id: str):
        return jsonify(service.update(require_uuid(trainer_id, "trainer_id"), _payload(partial=True)))

    @blueprint.delete("/trainers/<trainer_id>")
    def delete_trainer(trainer_id: str):
        service.delete(require_uuid(trainer_id, "trainer_id"))
        return "", 204

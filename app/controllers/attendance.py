"""Injectable Flask blueprint for the attendance resource."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from flask import Blueprint, Response, g, jsonify, request

from app.services.attendance import AttendanceError, AttendanceService

_MAX_PER_PAGE = 100


def _error(code: str, message: str, status: int, details: dict[str, Any] | None = None) -> tuple[Response, int]:
    payload: dict[str, Any] = {"error": {"code": code, "message": message, "timestamp": datetime.now(timezone.utc).isoformat(), "correlation_id": getattr(g, "correlation_id", None)}}
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status


def _uuid(value: str, field: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError(f"{field} must be a UUID") from error


def _date_argument(name: str) -> date | None:
    value = request.args.get(name)
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO-8601 date (YYYY-MM-DD)") from error


def _pagination_and_filters(*, allow_member_filter: bool) -> tuple[int, int, UUID | None, date | None]:
    # Attendance searching has deliberately small, stable filter semantics:
    # an optional member and/or the local checked-in calendar date.
    allowed = {"page", "per_page", "date"}
    if allow_member_filter:
        allowed.add("member_id")
    unknown = set(request.args) - allowed
    if unknown:
        raise ValueError("Unsupported query parameter: " + sorted(unknown)[0])
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
    except ValueError as error:
        raise ValueError("page and per_page must be integers") from error
    if page < 1:
        raise ValueError("page must be at least 1")
    if not 1 <= per_page <= _MAX_PER_PAGE:
        raise ValueError(f"per_page must be between 1 and {_MAX_PER_PAGE}")
    member_id = _uuid(request.args["member_id"], "member_id") if "member_id" in request.args else None
    return page, per_page, member_id, _date_argument("date")


def _require_empty_body() -> None:
    """Enforce the server-timestamp workflow used by attendance mutations."""
    # Reading raw bytes makes every nonempty representation invalid, including
    # malformed JSON and a JSON/null/object body. An absent or zero-length body
    # remains valid regardless of its content type.
    if request.get_data(cache=False):
        raise ValueError("Request body must be empty")


def _page(items: list[Any], page: int, per_page: int, total: int) -> Response:
    return jsonify({"items": [item.to_dict() for item in items], "page": page, "per_page": per_page, "total": total})


def create_attendance_blueprint(service: AttendanceService) -> Blueprint:
    """Create routes relative to the API version prefix selected by the app."""
    blueprint = Blueprint("attendance", __name__)

    @blueprint.errorhandler(AttendanceError)
    def handle_attendance_error(error: AttendanceError):
        return _error(error.code, error.message, error.status_code, error.details)

    @blueprint.post("/members/<member_id>/attendance/check-in")
    def check_in(member_id: str):
        try:
            _require_empty_body()
            attendance = service.check_in(_uuid(member_id, "member_id"))
        except ValueError as error:
            return _error("validation_error", str(error), 400)
        return jsonify(attendance.to_dict()), 201

    @blueprint.patch("/attendance/<attendance_id>/check-out")
    def check_out(attendance_id: str):
        try:
            _require_empty_body()
            attendance = service.check_out(_uuid(attendance_id, "attendance_id"))
        except ValueError as error:
            return _error("validation_error", str(error), 400)
        return jsonify(attendance.to_dict())

    @blueprint.get("/members/<member_id>/attendance")
    def member_history(member_id: str):
        try:
            parsed_member_id = _uuid(member_id, "member_id")
            page, per_page, _, checked_in_on = _pagination_and_filters(allow_member_filter=False)
        except ValueError as error:
            return _error("validation_error", str(error), 400)
        items, total = service.member_history(parsed_member_id, page=page, per_page=per_page, checked_in_on=checked_in_on)
        return _page(items, page, per_page, total)

    @blueprint.get("/attendance")
    def list_attendance():
        try:
            page, per_page, member_id, checked_in_on = _pagination_and_filters(allow_member_filter=True)
        except ValueError as error:
            return _error("validation_error", str(error), 400)
        items, total = service.search(page=page, per_page=per_page, member_id=member_id, checked_in_on=checked_in_on)
        return _page(items, page, per_page, total)

    return blueprint

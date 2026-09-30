from __future__ import annotations

from flask import Response


_ERROR = {"$ref": "#/components/schemas/Error"}
_UUID = {"type": "string", "format": "uuid"}
_DATE = {"type": "string", "format": "date"}
_DATE_TIME = {"type": "string", "format": "date-time"}


def _response(description: str, schema: dict | None = None) -> dict:
    response = {"description": description}
    if schema is not None:
        response["content"] = {"application/json": {"schema": schema}}
    return response


def _error_responses(*codes: str) -> dict:
    descriptions = {"400": "Validation error", "401": "Missing or invalid API key", "404": "Resource not found", "409": "Conflict"}
    return {code: _response(descriptions[code], _ERROR) for code in codes}


def _body(schema: str, *, required: bool = True) -> dict:
    return {"required": required, "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema}"}}}}


def _path_id(name: str) -> list[dict]:
    return [{"name": name, "in": "path", "required": True, "schema": _UUID}]


def _pagination(*, member_filter: bool = False, attendance_filters: bool = False) -> list[dict]:
    parameters = [
        {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1, "default": 1}},
        {"name": "per_page", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}},
    ]
    if member_filter:
        parameters.append({"name": "member_id", "in": "query", "schema": _UUID})
    if attendance_filters:
        parameters.extend([
            {"name": "date", "in": "query", "description": "Exact checked-in calendar date; cannot be combined with date_from/date_to.", "schema": _DATE},
            {"name": "date_from", "in": "query", "schema": _DATE},
            {"name": "date_to", "in": "query", "schema": _DATE},
        ])
    return parameters


def _secured(operation: dict) -> dict:
    operation["security"] = [{"ApiKeyAuth": []}]
    return operation


def openapi_document() -> dict:
    schemas = {
        "Error": {"type": "object", "required": ["error"], "properties": {"error": {"type": "object", "required": ["code", "message", "timestamp", "correlation_id"], "properties": {"code": {"type": "string"}, "message": {"type": "string"}, "timestamp": _DATE_TIME, "correlation_id": {"type": "string"}, "details": {"type": "object", "additionalProperties": True}}}}},
        "Member": {"type": "object", "required": ["id", "first_name", "last_name", "email", "created_at", "updated_at"], "properties": {"id": _UUID, "first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string", "format": "email"}, "phone": {"type": ["string", "null"]}, "date_of_birth": {**_DATE, "nullable": True}, "created_at": _DATE_TIME, "updated_at": _DATE_TIME}},
        "MemberWrite": {"type": "object", "properties": {"first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string", "format": "email"}, "phone": {"type": ["string", "null"]}, "date_of_birth": {**_DATE, "nullable": True}}, "additionalProperties": False},
        "Trainer": {"type": "object", "required": ["id", "first_name", "last_name", "email", "created_at", "updated_at"], "properties": {"id": _UUID, "first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string", "format": "email"}, "phone": {"type": ["string", "null"]}, "specialization": {"type": ["string", "null"]}, "created_at": _DATE_TIME, "updated_at": _DATE_TIME}},
        "TrainerWrite": {"type": "object", "properties": {"first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string", "format": "email"}, "phone": {"type": ["string", "null"]}, "specialization": {"type": ["string", "null"]}}, "additionalProperties": False},
        "MembershipPlan": {"type": "object", "required": ["id", "name", "duration_days", "price", "is_active", "created_at", "updated_at"], "properties": {"id": _UUID, "name": {"type": "string"}, "description": {"type": ["string", "null"]}, "duration_days": {"type": "integer", "minimum": 1}, "price": {"type": "string"}, "is_active": {"type": "boolean"}, "created_at": _DATE_TIME, "updated_at": _DATE_TIME}},
        "MembershipPlanWrite": {"type": "object", "required": ["name", "duration_days", "price"], "properties": {"name": {"type": "string"}, "description": {"type": ["string", "null"]}, "duration_days": {"type": "integer", "minimum": 1}, "price": {"oneOf": [{"type": "number", "minimum": 0}, {"type": "string"}]}, "is_active": {"type": "boolean", "default": True}}, "additionalProperties": False},
        "Membership": {"type": "object", "required": ["id", "member_id", "plan_id", "start_date", "end_date", "status", "created_at", "updated_at"], "properties": {"id": _UUID, "member_id": _UUID, "plan_id": _UUID, "start_date": _DATE, "end_date": _DATE, "status": {"type": "string", "enum": ["active", "cancelled"]}, "cancelled_at": {**_DATE_TIME, "nullable": True}, "created_at": _DATE_TIME, "updated_at": _DATE_TIME}},
        "MembershipAssign": {"type": "object", "required": ["plan_id"], "properties": {"plan_id": _UUID, "start_date": _DATE, "end_date": _DATE}, "additionalProperties": False},
        "MembershipPatch": {"type": "object", "minProperties": 1, "properties": {"plan_id": _UUID, "start_date": _DATE, "end_date": _DATE}, "additionalProperties": False},
        "Attendance": {"type": "object", "required": ["id", "member_id", "checked_in_at"], "properties": {"id": _UUID, "member_id": _UUID, "checked_in_at": _DATE_TIME, "checked_out_at": {**_DATE_TIME, "nullable": True}}},
        "MemberPage": {"type": "object", "required": ["items", "page", "per_page", "total"], "properties": {"items": {"type": "array", "items": {"$ref": "#/components/schemas/Member"}}, "page": {"type": "integer"}, "per_page": {"type": "integer"}, "total": {"type": "integer"}}},
        "TrainerPage": {"type": "object", "required": ["items", "page", "per_page", "total"], "properties": {"items": {"type": "array", "items": {"$ref": "#/components/schemas/Trainer"}}, "page": {"type": "integer"}, "per_page": {"type": "integer"}, "total": {"type": "integer"}}},
        "AttendancePage": {"type": "object", "required": ["items", "page", "per_page", "total"], "properties": {"items": {"type": "array", "items": {"$ref": "#/components/schemas/Attendance"}}, "page": {"type": "integer"}, "per_page": {"type": "integer"}, "total": {"type": "integer"}}},
    }
    paths = {
        "/health": {"get": {"summary": "Health check", "responses": {"200": _response("Healthy")}}},
        "/docs": {"get": {"summary": "Swagger UI", "responses": {"200": _response("Swagger UI")}}},
        "/openapi.json": {"get": {"summary": "OpenAPI document", "responses": {"200": _response("OpenAPI document")}}},
        "/api/v1/members": {
            "get": _secured({"parameters": _pagination(), "responses": {"200": _response("Member page", {"$ref": "#/components/schemas/MemberPage"}), **_error_responses("400", "401")}}),
            "post": _secured({"requestBody": _body("MemberWrite"), "responses": {"201": _response("Member created", {"$ref": "#/components/schemas/Member"}), **_error_responses("400", "401", "409")}}),
        },
        "/api/v1/members/{member_id}": {
            "get": _secured({"parameters": _path_id("member_id"), "responses": {"200": _response("Member", {"$ref": "#/components/schemas/Member"}), **_error_responses("400", "401", "404")}}),
            "patch": _secured({"parameters": _path_id("member_id"), "requestBody": _body("MemberWrite"), "responses": {"200": _response("Member updated", {"$ref": "#/components/schemas/Member"}), **_error_responses("400", "401", "404", "409")}}),
            "delete": _secured({"parameters": _path_id("member_id"), "responses": {"204": _response("Member deleted"), **_error_responses("400", "401", "404")}}),
        },
        "/api/v1/trainers": {
            "get": _secured({"parameters": _pagination(), "responses": {"200": _response("Trainer page", {"$ref": "#/components/schemas/TrainerPage"}), **_error_responses("400", "401")}}),
            "post": _secured({"requestBody": _body("TrainerWrite"), "responses": {"201": _response("Trainer created", {"$ref": "#/components/schemas/Trainer"}), **_error_responses("400", "401", "409")}}),
        },
        "/api/v1/trainers/{trainer_id}": {
            "get": _secured({"parameters": _path_id("trainer_id"), "responses": {"200": _response("Trainer", {"$ref": "#/components/schemas/Trainer"}), **_error_responses("401", "404")}}),
            "patch": _secured({"parameters": _path_id("trainer_id"), "requestBody": _body("TrainerWrite"), "responses": {"200": _response("Trainer updated", {"$ref": "#/components/schemas/Trainer"}), **_error_responses("400", "401", "404", "409")}}),
            "delete": _secured({"parameters": _path_id("trainer_id"), "responses": {"204": _response("Trainer deleted"), **_error_responses("401", "404")}}),
        },
        "/api/v1/membership-plans": {"post": _secured({"requestBody": _body("MembershipPlanWrite"), "responses": {"201": _response("Plan created", {"$ref": "#/components/schemas/MembershipPlan"}), **_error_responses("400", "401", "409")}})},
        "/api/v1/members/{member_id}/memberships": {"post": _secured({"parameters": _path_id("member_id"), "requestBody": _body("MembershipAssign"), "responses": {"201": _response("Membership assigned", {"$ref": "#/components/schemas/Membership"}), **_error_responses("400", "401", "404", "409")}})},
        "/api/v1/memberships/{membership_id}": {
            "get": _secured({"parameters": _path_id("membership_id"), "responses": {"200": _response("Membership", {"$ref": "#/components/schemas/Membership"}), **_error_responses("400", "401", "404")}}),
            "patch": _secured({"parameters": _path_id("membership_id"), "requestBody": _body("MembershipPatch"), "responses": {"200": _response("Membership updated", {"$ref": "#/components/schemas/Membership"}), **_error_responses("400", "401", "404", "409")}}),
            "delete": _secured({"parameters": _path_id("membership_id"), "responses": {"200": _response("Membership cancelled", {"$ref": "#/components/schemas/Membership"}), **_error_responses("400", "401", "404", "409")}}),
        },
        "/api/v1/members/{member_id}/attendance/check-in": {"post": _secured({"parameters": _path_id("member_id"), "responses": {"201": _response("Checked in", {"$ref": "#/components/schemas/Attendance"}), **_error_responses("400", "401", "409")}})},
        "/api/v1/attendance/{attendance_id}/check-out": {"patch": _secured({"parameters": _path_id("attendance_id"), "responses": {"200": _response("Checked out", {"$ref": "#/components/schemas/Attendance"}), **_error_responses("400", "401", "404", "409")}})},
        "/api/v1/members/{member_id}/attendance": {"get": _secured({"parameters": _path_id("member_id") + _pagination(attendance_filters=True), "responses": {"200": _response("Attendance history", {"$ref": "#/components/schemas/AttendancePage"}), **_error_responses("400", "401")}})},
        "/api/v1/attendance": {"get": _secured({"parameters": _pagination(member_filter=True, attendance_filters=True), "responses": {"200": _response("Attendance page", {"$ref": "#/components/schemas/AttendancePage"}), **_error_responses("400", "401")}})},
    }
    return {"openapi": "3.0.3", "info": {"title": "Gym Management API", "version": "1.0.0"}, "components": {"securitySchemes": {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}}, "schemas": schemas}, "paths": paths}


def docs_html() -> Response:
    return Response('<!doctype html><html><body><div id="swagger-ui"></div><script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script><script>SwaggerUIBundle({url:"/openapi.json",dom_id:"#swagger-ui"})</script></body></html>', mimetype="text/html")

"""Endpoint-specific OpenAPI description for the registered HTTP API."""
from __future__ import annotations

from typing import Any

_JSON = {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}


def _response(schema: str, description: str = "Successful response") -> dict[str, Any]:
    return {"description": description, "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema}"}}}}


def _operation(summary: str, response: str, *, request: str | None = None,
               status: str = "200", auth: bool = True, parameters: list[dict[str, Any]] | None = None,
               errors: tuple[str, ...] = ("401", "403", "404", "409", "422", "500")) -> dict[str, Any]:
    result: dict[str, Any] = {"summary": summary, "responses": {status: _response(response)}}
    if auth:
        result["security"] = [{"bearerAuth": []}]
    if parameters:
        result["parameters"] = parameters
    if request:
        result["requestBody"] = {"required": True, "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{request}"}}}}
    for code in errors:
        result["responses"][code] = {"$ref": "#/components/responses/Error"}
    return result


def _path_id(name: str) -> dict[str, Any]:
    return {"name": name, "in": "path", "required": True, "schema": {"type": "integer", "minimum": 1}}


def _query(name: str, schema: dict[str, Any], description: str) -> dict[str, Any]:
    return {"name": name, "in": "query", "required": False, "description": description, "schema": schema}


def build_openapi_document() -> dict[str, Any]:
    """Describe only routes registered by this application and their real inputs."""
    member_id, trainer_id, plan_id = _path_id("member_id"), _path_id("trainer_id"), _path_id("plan_id")
    membership_id, attendance_id = _path_id("membership_id"), _path_id("attendance_id")
    payment_id, workout_plan_id = _path_id("payment_id"), _path_id("workout_plan_id")
    date_range = [_query("start_date", {"type": "string", "format": "date"}, "Inclusive ISO-8601 start date"),
                  _query("end_date", {"type": "string", "format": "date"}, "Inclusive ISO-8601 end date")]
    paths: dict[str, Any] = {
        "/health": {"get": _operation("Health check", "HealthResponse", auth=False, errors=())},
        "/api/health": {"get": _operation("API health check", "HealthResponse", auth=False, errors=())},
        "/api/openapi.json": {"get": _operation("OpenAPI document", "OpenApiResponse", auth=False, errors=())},
        "/api/auth/register": {"post": _operation("Register a member or trainer", "TokenResponse", request="RegistrationRequest", status="201", auth=False, errors=("409", "422", "500"))},
        "/api/auth/login": {"post": _operation("Authenticate", "TokenResponse", request="LoginRequest", auth=False, errors=("401", "422", "500"))},
        "/api/auth/refresh": {"post": _operation("Refresh access token", "TokenResponse", request="RefreshRequest", auth=False, errors=("401", "422", "500"))},
        "/api/auth/me": {"get": _operation("Get authenticated identity", "UserResponse")},
        "/api/members": {
            "post": _operation("Create member profile", "MemberResponse", request="CreateMemberRequest", status="201"),
            "get": _operation("List or search members", "MemberListResponse", parameters=[_query("q", {"type": "string", "maxLength": 160}, "Name, email, or phone search text")]),
        },
        "/api/members/{member_id}": {
            "get": _operation("Get member", "MemberResponse", parameters=[member_id]),
            "put": _operation("Update member", "MemberResponse", request="UpdateMemberRequest", parameters=[member_id]),
            "delete": _operation("Deactivate member", "MemberResponse", parameters=[member_id]),
        },
        "/api/trainers": {
            "post": _operation("Create trainer profile", "TrainerResponse", request="CreateTrainerRequest", status="201"),
            "get": _operation("List trainers", "TrainerListResponse"),
        },
        "/api/trainers/{trainer_id}": {
            "get": _operation("Get trainer", "TrainerResponse", parameters=[trainer_id]),
            "put": _operation("Update trainer", "TrainerResponse", request="UpdateTrainerRequest", parameters=[trainer_id]),
            "delete": _operation("Deactivate trainer", "TrainerResponse", parameters=[trainer_id]),
        },
        "/api/trainers/{trainer_id}/members/{member_id}": {"put": _operation("Assign trainer to member", "AssignmentResponse", parameters=[trainer_id, member_id])},
        "/api/membership-plans": {
            "get": _operation("List membership plans", "MembershipPlanListResponse", parameters=[_query("include_inactive", {"type": "boolean", "default": False}, "Include inactive plans")]),
            "post": _operation("Create membership plan", "MembershipPlanResponse", request="CreateMembershipPlanRequest", status="201"),
        },
        "/api/membership-plans/{plan_id}": {
            "get": _operation("Get membership plan", "MembershipPlanResponse", parameters=[plan_id]),
            "put": _operation("Update membership plan", "MembershipPlanResponse", request="UpdateMembershipPlanRequest", parameters=[plan_id]),
            "patch": _operation("Partially update membership plan", "MembershipPlanResponse", request="PatchMembershipPlanRequest", parameters=[plan_id]),
        },
        "/api/membership-plans/{plan_id}/deactivate": {
            "post": _operation("Deactivate membership plan", "MembershipPlanResponse", parameters=[plan_id]),
        },
        "/api/members/{member_id}/memberships": {
            "post": _operation("Assign membership", "MembershipResponse", request="AssignMembershipRequest", status="201", parameters=[member_id]),
            "get": _operation("Get membership history", "MembershipListResponse", parameters=[member_id]),
        },
        "/api/members/{member_id}/memberships/active": {"get": _operation("Get active membership", "MembershipResponse", parameters=[member_id])},
        "/api/memberships/{membership_id}/renew": {"post": _operation("Renew membership", "MembershipResponse", status="201", parameters=[membership_id])},
        "/api/memberships/{membership_id}/cancel": {"post": _operation("Cancel membership", "MembershipResponse", parameters=[membership_id])},
        "/api/attendance/check-in": {"post": _operation("Check in member", "AttendanceResponse", request="CheckInRequest", status="201")},
        "/api/attendance/check-out": {"post": _operation("Check out attendance", "AttendanceResponse", request="CheckOutRequest")},
        "/api/members/{member_id}/attendance": {"get": _operation("Get member attendance history", "AttendanceListResponse", parameters=[member_id, *date_range])},
        "/api/attendance/daily": {"get": _operation("Get daily attendance report", "AttendanceListResponse", parameters=[_query("date", {"type": "string", "format": "date"}, "Report date; defaults to today")])},
        "/api/attendance": {"get": _operation("Get attendance date-range report", "AttendanceListResponse", parameters=date_range)},
        "/api/payments": {"post": _operation("Create payment", "PaymentResponse", request="CreatePaymentRequest", status="201"), "get": _operation("List visible payments", "PaymentListResponse")},
        "/api/payments/{payment_id}": {"get": _operation("Get payment", "PaymentResponse", parameters=[payment_id])},
        "/api/payments/{payment_id}/status": {"patch": _operation("Update payment status", "PaymentResponse", request="PaymentStatusRequest", parameters=[payment_id])},
        "/api/members/{member_id}/payments": {"get": _operation("Get member payment history", "PaymentListResponse", parameters=[member_id])},
        "/api/workout-plans": {"post": _operation("Create workout plan", "WorkoutPlanResponse", request="CreateWorkoutPlanRequest", status="201")},
        "/api/workout-plans/{workout_plan_id}": {"put": _operation("Update workout plan", "WorkoutPlanResponse", request="UpdateWorkoutPlanRequest", parameters=[workout_plan_id]), "delete": _operation("Deactivate workout plan", "WorkoutPlanResponse", parameters=[workout_plan_id])},
        "/api/workout-plans/{workout_plan_id}/members/{member_id}": {"put": _operation("Assign workout plan", "WorkoutPlanResponse", parameters=[workout_plan_id, member_id])},
        "/api/members/{member_id}/workout-plans": {"get": _operation("Get member workout plans", "WorkoutPlanListResponse", parameters=[member_id])},
    }
    scalar = {"type": "object", "additionalProperties": True}
    envelope = lambda data: {"type": "object", "required": ["success", "message", "data"], "properties": {"success": {"type": "boolean", "enum": [True]}, "message": {"type": "string"}, "data": data}}
    resource = {"type": "object", "additionalProperties": True}
    schemas: dict[str, Any] = {
        "Error": {"type": "object", "required": ["success", "message", "error_code"], "properties": {"success": {"type": "boolean", "enum": [False]}, "message": {"type": "string"}, "error_code": {"type": "string", "enum": ["BAD_REQUEST", "VALIDATION_ERROR", "UNAUTHENTICATED", "FORBIDDEN", "NOT_FOUND", "CONFLICT", "DATABASE_ERROR", "INTERNAL_ERROR"]}}},
        "HealthResponse": envelope({"type": "object", "required": ["status"], "properties": {"status": {"type": "string", "example": "healthy"}}}),
        "OpenApiResponse": envelope(scalar),
        "UserResponse": envelope(resource), "TokenResponse": envelope(resource),
        "MemberResponse": envelope(resource), "MemberListResponse": envelope({"type": "array", "items": resource}),
        "TrainerResponse": envelope(resource), "TrainerListResponse": envelope({"type": "array", "items": resource}),
        "MembershipPlanResponse": envelope(resource), "MembershipPlanListResponse": envelope({"type": "array", "items": resource}),
        "MembershipResponse": envelope({"nullable": True, **resource}), "MembershipListResponse": envelope({"type": "array", "items": resource}),
        "AttendanceResponse": envelope(resource), "AttendanceListResponse": envelope({"type": "array", "items": resource}),
        "PaymentResponse": envelope(resource), "PaymentListResponse": envelope({"type": "array", "items": resource}),
        "WorkoutPlanResponse": envelope(resource), "WorkoutPlanListResponse": envelope({"type": "array", "items": resource}), "AssignmentResponse": envelope(resource),
        "RegistrationRequest": {"type": "object", "required": ["email", "password", "phone"], "properties": {"email": {"type": "string", "format": "email"}, "password": {"type": "string", "format": "password", "minLength": 8, "description": "Must include uppercase, lowercase, digit, and special character."}, "role": {"type": "string", "enum": ["member", "trainer"], "default": "member"}, "profile": {"type": "object", "properties": {"full_name": {"type": "string"}, "name": {"type": "string"}, "first_name": {"type": "string"}, "last_name": {"type": "string"}, "phone": {"type": "string"}, "contact_email": {"type": "string", "format": "email"}, "specialization": {"type": "string"}}}, "phone": {"type": "string"}}},
        "LoginRequest": {"type": "object", "required": ["email", "password"], "properties": {"email": {"type": "string", "format": "email"}, "password": {"type": "string", "format": "password"}}}, "RefreshRequest": {"type": "object", "required": ["refresh_token"], "properties": {"refresh_token": {"type": "string"}}},
        "CreateMemberRequest": {"type": "object", "required": ["full_name", "email", "phone", "joining_date"], "properties": {"user_id": {"type": "integer"}, "trainer_id": {"type": "integer"}, "full_name": {"type": "string"}, "email": {"type": "string", "format": "email"}, "phone": {"type": "string"}, "joining_date": {"type": "string", "format": "date"}}}, "UpdateMemberRequest": {"type": "object", "properties": {"full_name": {"type": "string"}, "email": {"type": "string", "format": "email"}, "phone": {"type": "string"}, "joining_date": {"type": "string", "format": "date"}, "date_of_birth": {"type": "string", "format": "date"}, "gender": {"type": "string"}, "address": {"type": "string"}, "emergency_contact": {"type": "string"}, "membership_status": {"type": "string"}, "profile_status": {"type": "string"}}},
        "CreateTrainerRequest": {"type": "object", "required": ["name", "email", "phone", "joining_date"], "properties": {"user_id": {"type": "integer"}, "name": {"type": "string"}, "email": {"type": "string", "format": "email"}, "phone": {"type": "string"}, "joining_date": {"type": "string", "format": "date"}, "specialization": {"type": "string"}, "experience": {"type": "integer", "minimum": 0}, "status": {"type": "string", "enum": ["active", "inactive"]}}}, "UpdateTrainerRequest": {"type": "object", "properties": {"name": {"type": "string"}, "email": {"type": "string", "format": "email"}, "phone": {"type": "string"}, "joining_date": {"type": "string", "format": "date"}, "specialization": {"type": "string"}, "experience": {"type": "integer", "minimum": 0}, "status": {"type": "string", "enum": ["active", "inactive"]}}},
        "CreateMembershipPlanRequest": {"type": "object", "required": ["name", "duration_days", "price"], "properties": {"name": {"type": "string"}, "description": {"type": "string", "nullable": True}, "duration_days": {"type": "integer", "minimum": 1}, "price": {"type": "number", "minimum": 0}, "features": {"type": "array", "items": {"type": "string"}}, "status": {"type": "string", "enum": ["active", "inactive"]}}}, "UpdateMembershipPlanRequest": {"type": "object", "required": ["name", "duration_days", "price"], "properties": {"name": {"type": "string"}, "description": {"type": "string", "nullable": True}, "duration_days": {"type": "integer", "minimum": 1}, "price": {"type": "number", "minimum": 0}, "features": {"type": "array", "items": {"type": "string"}}, "status": {"type": "string", "enum": ["active", "inactive"]}}}, "PatchMembershipPlanRequest": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string", "nullable": True}, "duration_days": {"type": "integer", "minimum": 1}, "price": {"type": "number", "minimum": 0}, "features": {"type": "array", "items": {"type": "string"}}, "status": {"type": "string", "enum": ["active", "inactive"]}}},
        "AssignMembershipRequest": {"type": "object", "required": ["plan_id"], "properties": {"plan_id": {"type": "integer", "minimum": 1}, "start_date": {"type": "string", "format": "date"}, "end_date": {"type": "string", "format": "date"}, "amount": {"type": "number", "exclusiveMinimum": 0}, "payment_status": {"type": "string", "enum": ["pending", "paid", "failed", "refunded"]}, "status": {"type": "string", "enum": ["pending", "active", "expired", "cancelled"]}}}, "CheckInRequest": {"type": "object", "required": ["member_id"], "properties": {"member_id": {"type": "integer", "minimum": 1}, "attended_on": {"type": "string", "format": "date"}}}, "CheckOutRequest": {"type": "object", "required": ["attendance_id"], "properties": {"attendance_id": {"type": "integer", "minimum": 1}}},
        "CreatePaymentRequest": {"type": "object", "required": ["member_id", "amount", "currency", "payment_method", "payment_date", "status"], "properties": {"member_id": {"type": "integer"}, "membership_id": {"type": "integer"}, "amount": {"type": "number", "minimum": 0}, "currency": {"type": "string", "minLength": 3, "maxLength": 3}, "payment_method": {"type": "string"}, "transaction_id": {"type": "string"}, "payment_date": {"type": "string", "format": "date-time"}, "status": {"type": "string"}}}, "PaymentStatusRequest": {"type": "object", "required": ["status"], "properties": {"status": {"type": "string"}}},
        "CreateWorkoutPlanRequest": {"type": "object", "required": ["name"], "properties": {"member_id": {"type": "integer"}, "trainer_id": {"type": "integer"}, "name": {"type": "string"}, "description": {"type": "string"}, "status": {"type": "string", "enum": ["active", "inactive"]}, "exercises": {"type": "array", "items": {"$ref": "#/components/schemas/ExerciseInput"}}}}, "UpdateWorkoutPlanRequest": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "status": {"type": "string", "enum": ["active", "inactive"]}, "exercises": {"type": "array", "items": {"$ref": "#/components/schemas/ExerciseInput"}}}}, "ExerciseInput": {"type": "object", "required": ["exercise_name"], "properties": {"exercise_name": {"type": "string"}, "muscle_group": {"type": "string"}, "sets": {"type": "integer", "minimum": 1}, "repetitions": {"type": "integer", "minimum": 1}, "weight": {"type": "number", "minimum": 0}, "duration": {"type": "integer", "minimum": 1}, "notes": {"type": "string"}}},
    }
    return {"openapi": "3.0.3", "info": {"title": "Gym Management REST API", "version": "1.0.0"}, "paths": paths, "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}, "schemas": schemas, "responses": {"Error": {"description": "Safe API error", **_JSON}}}}

"""Unauthenticated deployment health endpoint."""
from config.openapi import PUBLIC_SECURITY, responses, success_envelope
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    responses=responses(200, success_envelope("HealthSuccess", inline_serializer("HealthData", {"status": serializers.CharField()})), 401, 500),
    auth=PUBLIC_SECURITY,
    operation_id="healthCheck",
    description="Unauthenticated web process readiness check.",
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health(_: object) -> Response:
    """Report that the web process is ready to receive traffic."""
    return Response({"success": True, "message": "Healthy.", "data": {"status": "ok"}})

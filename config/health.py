"""Unauthenticated deployment health endpoint."""
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(responses={200: OpenApiTypes.OBJECT}, description="Unauthenticated web process readiness check.")
@api_view(["GET"])
@permission_classes([AllowAny])
def health(_: object) -> Response:
    """Report that the web process is ready to receive traffic."""
    return Response({"success": True, "message": "Healthy.", "data": {"status": "ok"}})

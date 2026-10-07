"""Reusable drf-spectacular schemas for the API's explicit response contract.

Views return manually constructed envelopes, so DRF cannot infer their shapes from
serializer_class.  These helpers keep the generated OpenAPI document aligned with
that wire contract without changing response behaviour.
"""
from __future__ import annotations

from typing import Type

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, inline_serializer
from rest_framework import serializers


class ErrorEnvelopeSerializer(serializers.Serializer):
    """The error object emitted by ``config.exceptions.api_exception_handler``."""

    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
    error_code = serializers.CharField()
    details = serializers.JSONField(allow_null=True)
    timestamp = serializers.DateTimeField()
    request_id = serializers.CharField()


# SimpleJWT's drf-spectacular extension registers this HTTP bearer scheme.
JWT_SECURITY = [{"jwtAuth": []}]
PUBLIC_SECURITY: list[dict[str, list[str]]] = []

LIMIT_PARAMETER = OpenApiParameter("limit", int, OpenApiParameter.QUERY, description="Maximum number of results to return (default 20; maximum 100).")
OFFSET_PARAMETER = OpenApiParameter("offset", int, OpenApiParameter.QUERY, description="Number of results to skip (default 0).")


def success_envelope(name: str, data: serializers.Field | serializers.BaseSerializer) -> Type[serializers.Serializer]:
    """Return a named schema for ``{success, message, data}``."""
    return inline_serializer(
        name=name,
        fields={
            "success": serializers.BooleanField(default=True),
            "message": serializers.CharField(),
            "data": data,
        },
    )


def empty_success_envelope(name: str) -> Type[serializers.Serializer]:
    """A successful envelope whose data is explicitly JSON null."""
    return success_envelope(name, serializers.JSONField(allow_null=True))


def offset_success_envelope(name: str, item: serializers.BaseSerializer) -> Type[serializers.Serializer]:
    """Envelope used by the catalogue paginator (``items/count/limit/offset``)."""
    page = inline_serializer(
        name=f"{name}Page",
        fields={
            "items": item.__class__(many=True),
            "count": serializers.IntegerField(min_value=0),
            "limit": serializers.IntegerField(min_value=0),
            "offset": serializers.IntegerField(min_value=0),
        },
    )
    return success_envelope(name, page)


def paginated_success_envelope(name: str, item: serializers.BaseSerializer) -> Type[serializers.Serializer]:
    """Envelope used by engagement pagination (``count/next/previous/results``)."""
    page = inline_serializer(
        name=f"{name}Page",
        fields={
            "count": serializers.IntegerField(min_value=0),
            "next": serializers.URLField(allow_null=True),
            "previous": serializers.URLField(allow_null=True),
            "results": item.__class__(many=True),
        },
    )
    return success_envelope(name, page)


def error_responses(*codes: int) -> dict[int, OpenApiResponse]:
    """Build documented error responses using the centralized error envelope."""
    descriptions = {
        400: "Malformed request or validation failure.",
        401: "Missing, expired, or invalid JWT bearer token.",
        403: "Authenticated caller is not permitted to perform this operation.",
        404: "The requested resource does not exist or is not publicly available.",
        409: "The requested state conflicts with an existing resource.",
        500: "Unexpected server error.",
    }
    return {
        code: OpenApiResponse(response=ErrorEnvelopeSerializer, description=descriptions.get(code, "Request failed."))
        for code in codes
    }


def responses(success_status: int, success_schema: Type[serializers.Serializer], *error_codes: int) -> dict[int, object]:
    """Combine one success envelope with the applicable documented failures."""
    return {success_status: success_schema, **error_responses(*error_codes)}

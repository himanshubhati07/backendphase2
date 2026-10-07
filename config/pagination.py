"""Native DRF offset pagination configured for the public API."""
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class ApiLimitOffsetPagination(LimitOffsetPagination):
    """Offset pagination with documented defaults while views own the envelope."""

    default_limit = 20
    max_limit = 100

    def get_paginated_response(self, data: list[object]) -> Response:
        return Response({"items": data, "count": self.count, "limit": self.limit, "offset": self.offset})

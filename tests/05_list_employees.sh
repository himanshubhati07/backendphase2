#!/usr/bin/env bash
# Example: list employees with offset pagination. Requires TOKEN.
BASE_URL="${BASE_URL:-http://localhost:8080}"
: "${TOKEN:?Set TOKEN to a valid JWT access token first}"
PAGE="${1:-0}"
LIMIT="${2:-20}"

curl -i -G "$BASE_URL/api/v1/employees" \
	--data-urlencode "page=$PAGE" \
	--data-urlencode "limit=$LIMIT" \
	-H "Authorization: Bearer $TOKEN"

#!/usr/bin/env bash
# Example: requesting a nonexistent employee returns 404. Requires TOKEN.
BASE_URL="${BASE_URL:-http://localhost:8080}"
: "${TOKEN:?Set TOKEN to a valid JWT access token first}"

curl -i -X GET "$BASE_URL/api/v1/employees/999999999" \
	-H "Authorization: Bearer $TOKEN"

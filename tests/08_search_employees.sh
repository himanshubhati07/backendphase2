#!/usr/bin/env bash
# Example: search employees by name, email, or department. Requires TOKEN.
BASE_URL="${BASE_URL:-http://localhost:8080}"
: "${TOKEN:?Set TOKEN to a valid JWT access token first}"

curl -i -G "$BASE_URL/api/v1/employees/search" \
	--data-urlencode "department=Engineering" \
	--data-urlencode "page=0" \
	--data-urlencode "limit=20" \
	-H "Authorization: Bearer $TOKEN"

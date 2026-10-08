#!/usr/bin/env bash
# Example: delete an employee (204 No Content on success). Requires TOKEN and ID.
BASE_URL="${BASE_URL:-http://localhost:8080}"
: "${TOKEN:?Set TOKEN to a valid JWT access token first}"
ID="${1:?Usage: $0 <employee-id>}"

curl -i -X DELETE "$BASE_URL/api/v1/employees/$ID" \
	-H "Authorization: Bearer $TOKEN"

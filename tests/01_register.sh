#!/usr/bin/env bash
# Example: register a new user account.
BASE_URL="${BASE_URL:-http://localhost:8080}"

curl -i -X POST "$BASE_URL/api/v1/auth/register" \
	-H "Content-Type: application/json" \
	-d '{"email":"alice@example.com","password":"SuperSecret123"}'

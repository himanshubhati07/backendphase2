#!/usr/bin/env bash
# Example: log in and capture the JWT access token.
BASE_URL="${BASE_URL:-http://localhost:8080}"

curl -s -X POST "$BASE_URL/api/v1/auth/login" \
	-H "Content-Type: application/json" \
	-d '{"email":"alice@example.com","password":"SuperSecret123"}' | tee /tmp/ems_login_response.json

echo
echo "Extract the token with:"
echo "  TOKEN=\$(grep -o '\"accessToken\":\"[^\"]*\"' /tmp/ems_login_response.json | cut -d'\"' -f4)"

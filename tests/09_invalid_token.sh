#!/usr/bin/env bash
# Example: calling a protected endpoint with a missing/invalid token returns 401.
BASE_URL="${BASE_URL:-http://localhost:8080}"

echo "-- no Authorization header --"
curl -i -X GET "$BASE_URL/api/v1/employees"

echo
echo "-- garbage token --"
curl -i -X GET "$BASE_URL/api/v1/employees" -H "Authorization: Bearer not-a-real-token"

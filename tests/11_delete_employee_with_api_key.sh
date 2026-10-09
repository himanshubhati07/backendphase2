#!/usr/bin/env bash
# End-to-end test for the optional API key validation layer on
# DELETE /api/v1/employees/{id}?api-key=...
#
# Usage: BASE_URL=http://localhost:8080 bash tests/11_delete_employee_with_api_key.sh
#
# Flow: register a user, log in, create an employee, then delete it supplying
# a valid api-key query parameter. Expects 204 No Content when the key is
# valid (or when no API keys are configured on the server, in which case
# validation is a no-op and the delete still succeeds with 204).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

TS=$(date +%s)
EMAIL="apikey.user.${TS}@example.com"
PASSWORD="SuperSecret123"
EMP_EMAIL="api.key.employee.${TS}@example.com"
API_KEY="${API_KEY:-test-key-1}"

echo "== Auth: register =="
REGISTER_BODY=$(mktemp)
REGISTER_STATUS=$(curl -s -o "$REGISTER_BODY" -w "%{http_code}" -X POST "$BASE_URL/api/v1/auth/register" \
	-H "Content-Type: application/json" \
	-d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
assert_status "register new user" 201 "$REGISTER_STATUS"

echo "== Auth: login =="
LOGIN_BODY=$(mktemp)
LOGIN_STATUS=$(curl -s -o "$LOGIN_BODY" -w "%{http_code}" -X POST "$BASE_URL/api/v1/auth/login" \
	-H "Content-Type: application/json" \
	-d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
assert_status "login with valid credentials" 200 "$LOGIN_STATUS"
TOKEN=$(grep -o '"accessToken":"[^"]*"' "$LOGIN_BODY" | head -1 | cut -d'"' -f4)
if [[ -z "$TOKEN" ]]; then
	echo "FAIL - could not extract accessToken from login response"
	FAIL_COUNT=$((FAIL_COUNT + 1))
fi
AUTH_HEADER="Authorization: Bearer $TOKEN"

echo "== Employees: create =="
CREATE_BODY=$(mktemp)
CREATE_STATUS=$(curl -s -o "$CREATE_BODY" -w "%{http_code}" -X POST "$BASE_URL/api/v1/employees" \
	-H "Content-Type: application/json" -H "$AUTH_HEADER" \
	-d "{\"firstName\":\"Api\",\"lastName\":\"Key\",\"email\":\"$EMP_EMAIL\",\"phone\":\"555-0199\",\"department\":\"Security\",\"designation\":\"Engineer\",\"salary\":90000.00,\"joiningDate\":\"2024-01-15\",\"status\":\"ACTIVE\"}")
assert_status "create employee" 201 "$CREATE_STATUS"
EMP_ID=$(grep -o '"id":[0-9]*' "$CREATE_BODY" | head -1 | cut -d':' -f2)

echo "== Employees: delete with valid api-key -> 204 =="
DELETE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
	"$BASE_URL/api/v1/employees/$EMP_ID?api-key=$API_KEY" \
	-H "$AUTH_HEADER")
assert_status "delete employee with valid api-key" 204 "$DELETE_STATUS"

echo "== Employees: get deleted employee -> 404 =="
GET_DELETED_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/employees/$EMP_ID" \
	-H "$AUTH_HEADER")
assert_status "get deleted employee returns 404" 404 "$GET_DELETED_STATUS"

echo "== Employees: create second employee for invalid-key check =="
EMP_EMAIL_2="api.key.employee.2.${TS}@example.com"
CREATE_BODY_2=$(mktemp)
CREATE_STATUS_2=$(curl -s -o "$CREATE_BODY_2" -w "%{http_code}" -X POST "$BASE_URL/api/v1/employees" \
	-H "Content-Type: application/json" -H "$AUTH_HEADER" \
	-d "{\"firstName\":\"Api\",\"lastName\":\"Key2\",\"email\":\"$EMP_EMAIL_2\",\"phone\":\"555-0200\",\"department\":\"Security\",\"designation\":\"Engineer\",\"salary\":90000.00,\"joiningDate\":\"2024-01-15\",\"status\":\"ACTIVE\"}")
assert_status "create second employee" 201 "$CREATE_STATUS_2"
EMP_ID_2=$(grep -o '"id":[0-9]*' "$CREATE_BODY_2" | head -1 | cut -d':' -f2)

echo "== Employees: delete with invalid api-key -> 401 (or 204 if validation disabled) =="
BAD_KEY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
	"$BASE_URL/api/v1/employees/$EMP_ID_2?api-key=not-a-real-key" \
	-H "$AUTH_HEADER")
if [[ "$BAD_KEY_STATUS" == "401" ]]; then
	echo "PASS - delete employee with invalid api-key rejected (status=401, validation enabled)"
	PASS_COUNT=$((PASS_COUNT + 1))
elif [[ "$BAD_KEY_STATUS" == "204" ]]; then
	echo "PASS - delete employee with invalid api-key succeeded (status=204, no API keys configured - validation disabled)"
	PASS_COUNT=$((PASS_COUNT + 1))
else
	echo "FAIL - delete employee with invalid api-key (expected 401 or 204, actual=$BAD_KEY_STATUS)"
	FAIL_COUNT=$((FAIL_COUNT + 1))
fi

rm -f "$REGISTER_BODY" "$LOGIN_BODY" "$CREATE_BODY" "$CREATE_BODY_2"

print_summary

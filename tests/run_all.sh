#!/usr/bin/env bash
# End-to-end curl test suite for the Employee Management System API.
# Usage: BASE_URL=http://localhost:8080 bash tests/run_all.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

TS=$(date +%s)
EMAIL="test.user.${TS}@example.com"
PASSWORD="SuperSecret123"
EMP_EMAIL="jane.doe.${TS}@example.com"
EMP_EMAIL_UPDATED="jane.doe.updated.${TS}@example.com"

echo "== Auth: register =="
REGISTER_BODY=$(mktemp)
REGISTER_STATUS=$(curl -s -o "$REGISTER_BODY" -w "%{http_code}" -X POST "$BASE_URL/api/v1/auth/register" \
	-H "Content-Type: application/json" \
	-d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
assert_status "register new user" 201 "$REGISTER_STATUS"
cat "$REGISTER_BODY"; echo

echo "== Auth: register duplicate email -> 409 =="
DUP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/auth/register" \
	-H "Content-Type: application/json" \
	-d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
assert_status "duplicate register rejected" 409 "$DUP_STATUS"

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

echo "== Auth: login with wrong password -> 401 =="
BAD_LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/auth/login" \
	-H "Content-Type: application/json" \
	-d "{\"email\":\"$EMAIL\",\"password\":\"wrong-password\"}")
assert_status "login with wrong password rejected" 401 "$BAD_LOGIN_STATUS"

echo "== Employees: create without token -> 401 =="
NO_TOKEN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/employees" \
	-H "Content-Type: application/json" \
	-d '{}')
assert_status "create employee without token rejected" 401 "$NO_TOKEN_STATUS"

echo "== Employees: create with invalid token -> 401 =="
INVALID_TOKEN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/employees" \
	-H "Authorization: Bearer this.is.not.a.valid.token")
assert_status "list employees with invalid token rejected" 401 "$INVALID_TOKEN_STATUS"

echo "== Employees: create =="
CREATE_BODY=$(mktemp)
CREATE_STATUS=$(curl -s -o "$CREATE_BODY" -w "%{http_code}" -X POST "$BASE_URL/api/v1/employees" \
	-H "Content-Type: application/json" -H "$AUTH_HEADER" \
	-d "{\"firstName\":\"Jane\",\"lastName\":\"Doe\",\"email\":\"$EMP_EMAIL\",\"phone\":\"555-0100\",\"department\":\"Engineering\",\"designation\":\"Software Engineer\",\"salary\":95000.00,\"joiningDate\":\"2024-01-15\",\"status\":\"ACTIVE\"}")
assert_status "create employee" 201 "$CREATE_STATUS"
cat "$CREATE_BODY"; echo
EMP_ID=$(grep -o '"id":[0-9]*' "$CREATE_BODY" | head -1 | cut -d':' -f2)

echo "== Employees: create with duplicate email -> 409 =="
DUP_EMP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/employees" \
	-H "Content-Type: application/json" -H "$AUTH_HEADER" \
	-d "{\"firstName\":\"Jane\",\"lastName\":\"Doe\",\"email\":\"$EMP_EMAIL\",\"department\":\"Engineering\",\"designation\":\"Software Engineer\",\"salary\":95000.00,\"joiningDate\":\"2024-01-15\",\"status\":\"ACTIVE\"}")
assert_status "duplicate employee email rejected" 409 "$DUP_EMP_STATUS"

echo "== Employees: create with missing required field -> 400 =="
INVALID_BODY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/employees" \
	-H "Content-Type: application/json" -H "$AUTH_HEADER" \
	-d '{"firstName":"","lastName":"Doe"}')
assert_status "create employee with invalid payload rejected" 400 "$INVALID_BODY_STATUS"

echo "== Employees: get by id =="
GET_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/employees/$EMP_ID" \
	-H "$AUTH_HEADER")
assert_status "get employee by id" 200 "$GET_STATUS"

echo "== Employees: get missing id -> 404 =="
NOT_FOUND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/employees/999999999" \
	-H "$AUTH_HEADER")
assert_status "get nonexistent employee returns 404" 404 "$NOT_FOUND_STATUS"

echo "== Employees: list with pagination =="
LIST_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/v1/employees?page=0&limit=20" \
	-H "$AUTH_HEADER")
assert_status "list employees with pagination" 200 "$LIST_STATUS"

echo "== Employees: update =="
UPDATE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE_URL/api/v1/employees/$EMP_ID" \
	-H "Content-Type: application/json" -H "$AUTH_HEADER" \
	-d "{\"firstName\":\"Jane\",\"lastName\":\"Doe\",\"email\":\"$EMP_EMAIL_UPDATED\",\"phone\":\"555-0100\",\"department\":\"Engineering\",\"designation\":\"Senior Software Engineer\",\"salary\":110000.00,\"joiningDate\":\"2024-01-15\",\"status\":\"ACTIVE\"}")
assert_status "update employee" 200 "$UPDATE_STATUS"

echo "== Employees: update nonexistent -> 404 =="
UPDATE_404_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE_URL/api/v1/employees/999999999" \
	-H "Content-Type: application/json" -H "$AUTH_HEADER" \
	-d "{\"firstName\":\"X\",\"lastName\":\"Y\",\"email\":\"nobody-${TS}@example.com\",\"department\":\"D\",\"designation\":\"D\",\"salary\":1.00,\"joiningDate\":\"2024-01-15\",\"status\":\"ACTIVE\"}")
assert_status "update nonexistent employee returns 404" 404 "$UPDATE_404_STATUS"

echo "== Employees: search by department =="
SEARCH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -G "$BASE_URL/api/v1/employees/search" \
	--data-urlencode "department=Engineering" --data-urlencode "page=0" --data-urlencode "limit=20" \
	-H "$AUTH_HEADER")
assert_status "search employees by department" 200 "$SEARCH_STATUS"

echo "== Employees: search by name =="
SEARCH_NAME_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -G "$BASE_URL/api/v1/employees/search" \
	--data-urlencode "name=Jane" \
	-H "$AUTH_HEADER")
assert_status "search employees by name" 200 "$SEARCH_NAME_STATUS"

rm -f "$REGISTER_BODY" "$LOGIN_BODY" "$CREATE_BODY"

print_summary

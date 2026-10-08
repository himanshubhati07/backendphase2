#!/usr/bin/env bash
# Example: create an employee. Requires TOKEN to be set (see 02_login.sh).
BASE_URL="${BASE_URL:-http://localhost:8080}"
: "${TOKEN:?Set TOKEN to a valid JWT access token first}"

curl -i -X POST "$BASE_URL/api/v1/employees" \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer $TOKEN" \
	-d '{
		"firstName": "Jane",
		"lastName": "Doe",
		"email": "jane.doe@example.com",
		"phone": "555-0100",
		"department": "Engineering",
		"designation": "Software Engineer",
		"salary": 95000.00,
		"joiningDate": "2024-01-15",
		"status": "ACTIVE"
	}'

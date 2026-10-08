#!/usr/bin/env bash
# Example: update an existing employee. Requires TOKEN and ID.
BASE_URL="${BASE_URL:-http://localhost:8080}"
: "${TOKEN:?Set TOKEN to a valid JWT access token first}"
ID="${1:?Usage: $0 <employee-id>}"

curl -i -X PUT "$BASE_URL/api/v1/employees/$ID" \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer $TOKEN" \
	-d '{
		"firstName": "Jane",
		"lastName": "Doe",
		"email": "jane.doe.updated@example.com",
		"phone": "555-0100",
		"department": "Engineering",
		"designation": "Senior Software Engineer",
		"salary": 110000.00,
		"joiningDate": "2024-01-15",
		"status": "ACTIVE"
	}'

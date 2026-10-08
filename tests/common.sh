#!/usr/bin/env bash
# Shared helpers for the curl-based API test scripts.
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
PASS_COUNT=0
FAIL_COUNT=0

# assert_status <description> <expected_status> <actual_status>
assert_status() {
	local description="$1" expected="$2" actual="$3"
	if [[ "$actual" == "$expected" ]]; then
		echo "PASS - $description (status=$actual)"
		PASS_COUNT=$((PASS_COUNT + 1))
	else
		echo "FAIL - $description (expected=$expected actual=$actual)"
		FAIL_COUNT=$((FAIL_COUNT + 1))
	fi
}

print_summary() {
	echo "----------------------------------------"
	echo "Passed: $PASS_COUNT  Failed: $FAIL_COUNT"
	if [[ "$FAIL_COUNT" -gt 0 ]]; then
		exit 1
	fi
}

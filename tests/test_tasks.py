"""Integration coverage for owner-scoped task CRUD, listing, and validation."""
from fastapi.testclient import TestClient
import pytest

TASKS_URL = "/api/v1/tasks"


def task_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Plan release",
        "description": "Prepare and publish the release notes.",
        "priority": "High",
        "due_date": "2030-01-15",
        "status": "Pending",
    }
    payload.update(overrides)
    return payload


def create_task(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    response = client.post(TASKS_URL, json=task_payload(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Task created."
    return body["data"]


def assert_error(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == code
    assert body["message"]
    assert body["timestamp"]
    assert body["correlation_id"]
    return body


def test_create_and_retrieve_task_use_success_envelopes_and_persist(
    client: TestClient, user_headers: dict[str, str], db_connection
) -> None:
    created = create_task(client, user_headers)
    assert created["id"] == 1
    assert created["user_id"] == 1
    assert created["title"] == "Plan release"
    assert created["priority"] == "High"
    assert created["status"] == "Pending"
    assert created["created_at"] and created["updated_at"]

    with db_connection.cursor() as cursor:
        cursor.execute(
            "SELECT title, description, priority, due_date::text, status, user_id FROM tasks WHERE id = %s",
            (created["id"],),
        )
        persisted = cursor.fetchone()
    assert persisted == (
        "Plan release", "Prepare and publish the release notes.", "High", created["due_date"], "Pending", 1
    )

    response = client.get(f"{TASKS_URL}/{created['id']}", headers=user_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Task retrieved."
    assert body["data"] == created


def test_replace_complete_and_delete_task_persist_their_effects(
    client: TestClient, user_headers: dict[str, str], db_connection
) -> None:
    created = create_task(client, user_headers)
    replacement = task_payload(
        title="Updated plan", description="Replacement description", priority="Low",
        due_date="2031-02-03", status="In Progress",
    )
    update = client.put(f"{TASKS_URL}/{created['id']}", json=replacement, headers=user_headers)
    assert update.status_code == 200, update.text
    updated = update.json()
    assert updated["success"] is True
    assert updated["message"] == "Task updated."
    assert updated["data"]["title"] == "Updated plan"
    assert updated["data"]["status"] == "In Progress"
    assert updated["data"]["updated_at"] >= created["updated_at"]

    complete = client.patch(f"{TASKS_URL}/{created['id']}/complete", headers=user_headers)
    assert complete.status_code == 200, complete.text
    completed = complete.json()
    assert completed["success"] is True
    assert completed["message"] == "Task completed."
    assert completed["data"]["status"] == "Completed"

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT title, priority, due_date::text, status FROM tasks WHERE id = %s", (created["id"],))
        assert cursor.fetchone() == ("Updated plan", "Low", completed["data"]["due_date"], "Completed")

    deletion = client.delete(f"{TASKS_URL}/{created['id']}", headers=user_headers)
    assert deletion.status_code == 200, deletion.text
    assert deletion.json() == {
        "success": True,
        "message": "Task deleted.",
        "data": {"message": "Task deleted."},
    }
    assert_error(client.get(f"{TASKS_URL}/{created['id']}", headers=user_headers), 404, "not_found")
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE id = %s", (created["id"],))
        assert cursor.fetchone()[0] == 0


def test_tasks_are_invisible_and_unmodifiable_to_other_users(
    client: TestClient, user_headers: dict[str, str], second_user_headers: dict[str, str]
) -> None:
    owned = create_task(client, user_headers, title="Private task")

    listed = client.get(TASKS_URL, headers=second_user_headers)
    assert listed.status_code == 200
    assert listed.json()["data"] == {"items": [], "total": 0, "offset": 0, "limit": 20}

    assert_error(client.get(f"{TASKS_URL}/{owned['id']}", headers=second_user_headers), 404, "not_found")
    assert_error(
        client.put(f"{TASKS_URL}/{owned['id']}", json=task_payload(), headers=second_user_headers), 404, "not_found"
    )
    assert_error(client.patch(f"{TASKS_URL}/{owned['id']}/complete", headers=second_user_headers), 404, "not_found")
    assert_error(client.delete(f"{TASKS_URL}/{owned['id']}", headers=second_user_headers), 404, "not_found")

    owner_check = client.get(f"{TASKS_URL}/{owned['id']}", headers=user_headers)
    assert owner_check.status_code == 200
    assert owner_check.json()["data"]["status"] == "Pending"


def test_list_search_filters_and_pagination_report_matching_total(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    create_task(client, user_headers, title="Write quarterly report", priority="High", status="Pending")
    create_task(client, user_headers, title="Review quarterly report", priority="Low", status="Completed")
    create_task(client, user_headers, title="Book dentist", priority="High", status="Completed")
    create_task(client, user_headers, title="Write migration", priority="Medium", status="In Progress")

    filtered = client.get(
        TASKS_URL,
        params={"search": "REPORT", "status": "Completed", "priority": "Low", "limit": 1},
        headers=user_headers,
    )
    assert filtered.status_code == 200, filtered.text
    body = filtered.json()
    assert body["success"] is True
    assert body["message"] == "Tasks retrieved."
    assert body["data"]["total"] == 1
    assert body["data"]["offset"] == 0
    assert body["data"]["limit"] == 1
    assert [item["title"] for item in body["data"]["items"]] == ["Review quarterly report"]

    page = client.get(TASKS_URL, params={"offset": 1, "limit": 2}, headers=user_headers)
    assert page.status_code == 200
    page_data = page.json()["data"]
    assert page_data["total"] == 4
    assert page_data["offset"] == 1
    assert page_data["limit"] == 2
    assert [item["title"] for item in page_data["items"]] == ["Review quarterly report", "Book dentist"]


def test_list_default_limit_is_twenty_and_total_is_not_page_size(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    for number in range(21):
        create_task(client, user_headers, title=f"Task {number}")

    response = client.get(TASKS_URL, headers=user_headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["offset"] == 0
    assert data["limit"] == 20
    assert data["total"] == 21
    assert len(data["items"]) == 20
    assert [task["title"] for task in data["items"]] == [f"Task {number}" for number in range(20)]


@pytest.mark.parametrize("task_id", ["0", "-1", "not-a-number"])
def test_invalid_task_identifiers_are_validation_errors(
    client: TestClient, user_headers: dict[str, str], task_id: str
) -> None:
    response = client.get(f"{TASKS_URL}/{task_id}", headers=user_headers)
    assert_error(response, 422, "validation_error")


def test_missing_task_is_not_found(client: TestClient, user_headers: dict[str, str]) -> None:
    body = assert_error(client.get(f"{TASKS_URL}/99999", headers=user_headers), 404, "not_found")
    assert body["message"] == "Task not found."


@pytest.mark.parametrize(
    "payload",
    [
        {},
        task_payload(title=""),
        task_payload(description=""),
        task_payload(priority="Urgent"),
        task_payload(due_date="not-a-date"),
        task_payload(status="Done"),
    ],
)
def test_missing_or_invalid_task_fields_are_validation_errors(
    client: TestClient, user_headers: dict[str, str], payload: dict[str, object]
) -> None:
    response = client.post(TASKS_URL, json=payload, headers=user_headers)
    body = assert_error(response, 422, "validation_error")
    assert body["message"] == "Request validation failed."
    assert body["details"]


def test_update_requires_complete_valid_task_representation(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    task = create_task(client, user_headers)
    response = client.put(f"{TASKS_URL}/{task['id']}", json={"title": "Only title"}, headers=user_headers)
    assert_error(response, 422, "validation_error")

"""HTTP integration coverage for the public story catalogue and activities API."""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from stories.models import Activity, Category, Story

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def editor() -> User:
    return User.objects.create_user(email="editor@example.com", password="safe-password-123")


@pytest.fixture
def category() -> Category:
    return Category.objects.create(name="Animals")


def story_payload(category: Category, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "The Little Fox",
        "description": "A kind fox helps a friend.",
        "content": "Fox found a friend who needed help.",
        "category": str(category.id),
        "age_group": "2-3",
        "language": "en",
        "cover_image_url": "https://example.test/fox.jpg",
        "audio_url": "https://example.test/fox.mp3",
        "duration_minutes": 3,
        "learning_objective": "Practice kindness.",
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def activity_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "question": "What animal helped its friend?",
        "activity_type": "multiple_choice",
        "options": ["Fox", "Owl"],
        "correct_answer": "Fox",
        "difficulty": "easy",
    }
    payload.update(overrides)
    return payload


def authenticate(client: APIClient, user: User) -> None:
    client.force_authenticate(user=user)


def test_story_crud_and_detail_over_http(client: APIClient, editor: User, category: Category) -> None:
    authenticate(client, editor)
    created = client.post("/api/v1/stories", story_payload(category), format="json")

    assert created.status_code == 201
    created_data = created.json()["data"]
    story_id = created_data["id"]
    assert created.json()["success"] is True
    assert created_data["category"]["id"] == str(category.id)

    detail = client.get(f"/api/v1/stories/{story_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["title"] == "The Little Fox"

    replacement = story_payload(category, title="The Brave Fox", duration_minutes=4)
    updated = client.put(f"/api/v1/stories/{story_id}", replacement, format="json")
    assert updated.status_code == 200
    assert updated.json()["data"]["title"] == "The Brave Fox"
    assert updated.json()["data"]["duration_minutes"] == 4

    deleted = client.delete(f"/api/v1/stories/{story_id}")
    assert deleted.status_code == 200
    assert deleted.json()["data"] is None
    assert not Story.objects.filter(pk=story_id).exists()


def test_story_filter_search_and_limit_offset_pagination(client: APIClient, category: Category) -> None:
    matching = [
        Story.objects.create(title=f"Fox tale {number}", description="Forest friends", content="A fox story", category=category, age_group="2-3", language="en", duration_minutes=1)
        for number in range(3)
    ]
    other_category = Category.objects.create(name="Ocean")
    Story.objects.create(title="Fish tale", description="Ocean", content="A fish story", category=other_category, age_group="2-3", language="en", duration_minutes=1)
    Story.objects.create(title="French fox", content="Not contract language", category=category, age_group="2-3", language="fr", duration_minutes=1)

    listing = client.get(f"/api/v1/stories?category={category.id}&age_group=2-3&language=en&limit=2&offset=1")
    assert listing.status_code == 200
    page = listing.json()["data"]
    assert page["count"] == 3
    assert page["limit"] == 2
    assert page["offset"] == 1
    assert len(page["items"]) == 2

    searched = client.get("/api/v1/stories/search?q=forest")
    assert searched.status_code == 200
    assert {item["id"] for item in searched.json()["data"]["items"]} == {str(story.id) for story in matching}


def test_inactive_stories_are_not_public_in_listing_detail_search_or_activities(client: APIClient, category: Category) -> None:
    inactive = Story.objects.create(title="Hidden fox", description="secret forest", content="Do not publish", category=category, age_group="2-3", language="en", duration_minutes=1, is_active=False)
    Activity.objects.create(story=inactive, **activity_payload())

    assert client.get("/api/v1/stories").json()["data"]["count"] == 0
    assert client.get("/api/v1/stories/search?q=hidden").json()["data"]["count"] == 0
    assert client.get(f"/api/v1/stories/{inactive.id}").status_code == 404
    assert client.get(f"/api/v1/stories/{inactive.id}/activities").status_code == 404


def test_story_validation_and_unauthenticated_writes(client: APIClient, category: Category) -> None:
    unauthenticated = client.post("/api/v1/stories", story_payload(category), format="json")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error_code"] == "authentication_failed"

    editor = User.objects.create_user(email="validation@example.com", password="safe-password-123")
    authenticate(client, editor)
    invalid = client.post(
        "/api/v1/stories",
        story_payload(category, title="   ", content=" ", duration_minutes=0, age_group="wrong", language="fr"),
        format="json",
    )
    assert invalid.status_code == 400
    assert invalid.json()["error_code"] == "validation_error"
    details = invalid.json()["details"]
    assert {"title", "content", "duration_minutes", "age_group", "language"}.issubset(details)


def test_activity_create_list_update_and_delete_over_http(client: APIClient, editor: User, category: Category) -> None:
    story = Story.objects.create(title="Public fox", content="A public story", category=category, age_group="2-3", language="en", duration_minutes=1)
    authenticate(client, editor)

    created = client.post(f"/api/v1/stories/{story.id}/activities", activity_payload(), format="json")
    assert created.status_code == 201
    activity_id = created.json()["data"]["id"]
    assert created.json()["data"]["story"] == str(story.id)

    listed = client.get(f"/api/v1/stories/{story.id}/activities")
    assert listed.status_code == 200
    assert listed.json()["data"]["count"] == 1
    assert listed.json()["data"]["items"][0]["id"] == activity_id

    updated = client.put(f"/api/v1/activities/{activity_id}", activity_payload(difficulty="medium"), format="json")
    assert updated.status_code == 200
    assert updated.json()["data"]["difficulty"] == "medium"

    deleted = client.delete(f"/api/v1/activities/{activity_id}")
    assert deleted.status_code == 200
    assert deleted.json()["data"] is None
    assert not Activity.objects.filter(pk=activity_id).exists()


def test_activity_validation_not_found_and_authentication(client: APIClient, editor: User, category: Category) -> None:
    story = Story.objects.create(title="Public fox", content="A public story", category=category, age_group="2-3", language="en", duration_minutes=1)
    unknown_id = uuid.uuid4()

    assert client.post(f"/api/v1/stories/{story.id}/activities", activity_payload(), format="json").status_code == 401
    assert client.put(f"/api/v1/activities/{unknown_id}", activity_payload(), format="json").status_code == 401
    assert client.delete(f"/api/v1/activities/{unknown_id}").status_code == 401

    authenticate(client, editor)
    invalid_options = client.post(f"/api/v1/stories/{story.id}/activities", activity_payload(options={"Fox": True}), format="json")
    assert invalid_options.status_code == 400
    assert invalid_options.json()["error_code"] == "validation_error"
    assert "options" in invalid_options.json()["details"]

    invalid_question = client.post(f"/api/v1/stories/{story.id}/activities", activity_payload(question=" "), format="json")
    assert invalid_question.status_code == 400
    assert "question" in invalid_question.json()["details"]

    missing_story = client.post(f"/api/v1/stories/{unknown_id}/activities", activity_payload(), format="json")
    missing_activity = client.put(f"/api/v1/activities/{unknown_id}", activity_payload(), format="json")
    assert missing_story.status_code == 404
    assert missing_activity.status_code == 404
    assert missing_activity.json()["error_code"] == "not_found"

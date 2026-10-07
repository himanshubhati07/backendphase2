"""Integration tests for engagement ownership, idempotency, and pagination."""

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.models import User
from engagement.models import Favorite, LearningProgress
from stories.models import Category, Story

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def users():
    return (
        User.objects.create_user(email="first@example.com", password="safe-password"),
        User.objects.create_user(email="second@example.com", password="safe-password"),
    )


@pytest.fixture
def category():
    return Category.objects.create(name="Animals")


def make_story(category, number=0):
    return Story.objects.create(
        category=category,
        title=f"Story {number}",
        content="A short story.",
        language="en",
        age_group="2-3",
        duration_minutes=1,
    )


@override_settings(ROOT_URLCONF="engagement.test_urls")
def test_engagement_endpoints_require_authentication(client, category):
    story = make_story(category)

    assert client.post(f"/api/v1/stories/{story.id}/favorite").status_code == 401
    assert client.get("/api/v1/favorites").status_code == 401
    assert client.post(f"/api/v1/stories/{story.id}/complete").status_code == 401
    assert client.get("/api/v1/progress").status_code == 401
    assert client.get(f"/api/v1/progress/{story.id}").status_code == 401


@override_settings(ROOT_URLCONF="engagement.test_urls")
def test_favorites_are_isolated_and_duplicate_is_a_conflict(client, users, category):
    first, second = users
    story = make_story(category)
    client.force_authenticate(first)

    assert client.post(f"/api/v1/stories/{story.id}/favorite").status_code == 201
    assert client.post(f"/api/v1/stories/{story.id}/favorite").status_code == 409
    assert Favorite.objects.filter(user=first, story=story).count() == 1

    client.force_authenticate(second)
    listing = client.get("/api/v1/favorites")
    assert listing.status_code == 200
    assert listing.data["data"]["count"] == 0
    # A different user's favorite is deliberately indistinguishable from absent.
    assert client.delete(f"/api/v1/stories/{story.id}/favorite").status_code == 404


@override_settings(ROOT_URLCONF="engagement.test_urls")
def test_completion_is_idempotent_and_preserves_completion_time(client, users, category):
    user, _ = users
    story = make_story(category)
    client.force_authenticate(user)

    assert client.post(f"/api/v1/stories/{story.id}/complete").status_code == 200
    progress = LearningProgress.objects.get(user=user, story=story)
    completed_at = progress.completed_at

    assert client.post(f"/api/v1/stories/{story.id}/complete").status_code == 200
    progress.refresh_from_db()
    assert progress.is_completed is True
    assert progress.completed_at == completed_at
    assert LearningProgress.objects.filter(user=user, story=story).count() == 1


def test_delete_favorite_after_creation_uses_project_api_route(client, users, category):
    """A user can remove a newly created favorite through the deployed URLConf."""
    user, _ = users
    story = make_story(category)
    client.force_authenticate(user=user)

    created = client.post(f"/api/v1/stories/{story.id}/favorite")
    assert created.status_code == 201
    assert Favorite.objects.filter(user=user, story=story).exists()

    response = client.delete(f"/api/v1/stories/{story.id}/favorite")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Story removed from favorites.",
        "data": None,
    }
    assert not Favorite.objects.filter(user=user, story=story).exists()


def test_get_completed_progress_uses_project_api_route(client, users, category):
    """A completed story's progress is retrievable through the deployed URLConf."""
    user, _ = users
    story = make_story(category)
    client.force_authenticate(user=user)

    completed = client.post(f"/api/v1/stories/{story.id}/complete")
    assert completed.status_code == 200

    response = client.get(f"/api/v1/progress/{story.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Learning progress retrieved."
    assert body["data"]["id"] == completed.json()["data"]["id"]
    assert body["data"]["story"] == str(story.id)
    assert body["data"]["is_completed"] is True
    assert body["data"]["completed_at"] is not None


@override_settings(ROOT_URLCONF="engagement.test_urls")
def test_progress_and_favorites_use_limit_offset_pagination(client, users, category):
    user, _ = users
    client.force_authenticate(user)
    stories = [make_story(category, number=index) for index in range(25)]
    Favorite.objects.bulk_create([Favorite(user=user, story=story) for story in stories])
    LearningProgress.objects.bulk_create(
        [LearningProgress(user=user, story=story, is_completed=True) for story in stories]
    )

    favorites = client.get("/api/v1/favorites?limit=10&offset=10")
    progress = client.get("/api/v1/progress?limit=10&offset=10")
    for response in (favorites, progress):
        assert response.status_code == 200
        assert response.data["data"]["count"] == 25
        assert len(response.data["data"]["results"]) == 10
        assert response.data["data"]["next"]
        assert response.data["data"]["previous"]

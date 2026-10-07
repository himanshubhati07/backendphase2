"""Write-side operations for catalogue resources."""
from __future__ import annotations

from typing import Any

from .models import Activity, Story


def create_story(*, validated_data: dict[str, Any]) -> Story:
    return Story.objects.create(**validated_data)


def replace_story(*, story: Story, validated_data: dict[str, Any]) -> Story:
    for field, value in validated_data.items():
        setattr(story, field, value)
    story.save()
    return story


def delete_story(*, story: Story) -> None:
    story.delete()


def create_activity(*, story: Story, validated_data: dict[str, Any]) -> Activity:
    return Activity.objects.create(story=story, **validated_data)


def replace_activity(*, activity: Activity, validated_data: dict[str, Any]) -> Activity:
    for field, value in validated_data.items():
        setattr(activity, field, value)
    activity.save()
    return activity


def delete_activity(*, activity: Activity) -> None:
    activity.delete()

"""Wire serializers for the catalogue resources."""
from __future__ import annotations

from typing import Any

from django.conf import settings
from rest_framework import serializers

from .models import Activity, Category, Story


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "created_at")
        read_only_fields = ("id", "created_at")


class StoryWriteSerializer(serializers.ModelSerializer):
    """Validation-only representation used for story mutations."""

    # Validate against settings at request time rather than a fixed ChoiceField.
    language = serializers.CharField(max_length=10)
    age_group = serializers.CharField(max_length=10)

    class Meta:
        model = Story
        fields = (
            "title", "description", "content", "category", "age_group", "language",
            "cover_image_url", "audio_url", "duration_minutes", "learning_objective", "is_active",
        )

    def validate_language(self, value: str) -> str:
        if value not in settings.SUPPORTED_STORY_LANGUAGES:
            raise serializers.ValidationError("Unsupported story language.")
        return value

    def validate_age_group(self, value: str) -> str:
        if value not in settings.SUPPORTED_STORY_AGE_GROUPS:
            raise serializers.ValidationError("Unsupported story age group.")
        return value

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title cannot be blank.")
        return value.strip()

    def validate_content(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Content cannot be blank.")
        return value.strip()

    def validate_duration_minutes(self, value: int) -> int:
        if value <= 0:
            raise serializers.ValidationError("Duration must be greater than zero.")
        return value


class StoryReadSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Story
        fields = (
            "id", "title", "description", "content", "category", "age_group", "language",
            "cover_image_url", "audio_url", "duration_minutes", "learning_objective", "is_active",
            "created_at", "updated_at",
        )


class ActivityWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ("question", "activity_type", "options", "correct_answer", "difficulty")

    def validate_options(self, value: Any) -> list[Any] | None:
        if value is not None and not isinstance(value, list):
            raise serializers.ValidationError("Options must be a JSON array.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for field in ("question", "activity_type", "correct_answer", "difficulty"):
            value = attrs.get(field)
            if value is not None:
                if not value.strip():
                    raise serializers.ValidationError({field: "This field cannot be blank."})
                attrs[field] = value.strip()
        return attrs


class ActivityReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ("id", "story", "question", "activity_type", "options", "correct_answer", "difficulty", "created_at")
        read_only_fields = fields

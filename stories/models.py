"""Catalog and learning-activity persistence models."""
from __future__ import annotations

import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Category(models.Model):
    """A reusable classification for stories."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Story(models.Model):
    """An age-appropriate story in the public catalogue."""

    LANGUAGE_EN = "en"
    AGE_GROUP_TWO_TO_THREE = "2-3"
    LANGUAGE_CHOICES = ((LANGUAGE_EN, "English"),)
    AGE_GROUP_CHOICES = ((AGE_GROUP_TWO_TO_THREE, "2–3 years"),)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="stories")
    age_group = models.CharField(max_length=10, choices=AGE_GROUP_CHOICES, db_index=True)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, db_index=True)
    cover_image_url = models.URLField(blank=True)
    audio_url = models.URLField(blank=True)
    duration_minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    learning_objective = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("is_active", "category"), name="story_active_category_idx"),
            models.Index(fields=("is_active", "age_group", "language"), name="story_catalog_filter_idx"),
            models.Index(fields=("title",), name="story_title_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(duration_minutes__gt=0), name="story_duration_positive"),
            models.CheckConstraint(condition=~Q(title=""), name="story_title_nonempty"),
            models.CheckConstraint(condition=~Q(content=""), name="story_content_nonempty"),
        ]

    def __str__(self) -> str:
        return self.title


class Activity(models.Model):
    """A question a child can answer after reading a story."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="activities")
    question = models.TextField()
    activity_type = models.CharField(max_length=50)
    options = models.JSONField(null=True, blank=True)
    correct_answer = models.CharField(max_length=255)
    difficulty = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("story", "created_at"), name="activity_story_created_idx")]
        constraints = [
            models.CheckConstraint(condition=~Q(question=""), name="activity_question_nonempty"),
            models.CheckConstraint(condition=~Q(activity_type=""), name="activity_type_nonempty"),
            models.CheckConstraint(condition=~Q(correct_answer=""), name="activity_answer_nonempty"),
            models.CheckConstraint(condition=~Q(difficulty=""), name="activity_difficulty_nonempty"),
        ]

    def __str__(self) -> str:
        return f"{self.story}: {self.question[:50]}"

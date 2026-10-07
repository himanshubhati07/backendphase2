"""Models for a user's saved stories and completion state."""

import uuid

from django.db import models


class Favorite(models.Model):
    """A story saved by a particular user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    story = models.ForeignKey(
        "stories.Story",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "story"), name="unique_user_story_favorite"
            )
        ]
        indexes = [
            models.Index(fields=("user", "story"), name="favorite_user_story_idx"),
            models.Index(fields=("user", "created_at"), name="favorite_user_created_idx"),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user_id} favorited {self.story_id}"


class LearningProgress(models.Model):
    """A user's completion status for a story."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="learning_progress",
    )
    story = models.ForeignKey(
        "stories.Story",
        on_delete=models.CASCADE,
        related_name="learning_progress_records",
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "story"), name="unique_user_story_progress"
            )
        ]
        indexes = [
            models.Index(fields=("user", "story"), name="progress_user_story_idx"),
            models.Index(fields=("user", "updated_at"), name="progress_user_updated_idx"),
        ]
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        state = "completed" if self.is_completed else "in progress"
        return f"{self.user_id}: {self.story_id} ({state})"

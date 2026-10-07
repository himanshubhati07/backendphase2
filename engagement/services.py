"""Business operations for engagement resources."""

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.generics import get_object_or_404

from config.exceptions import Conflict
from stories.models import Story

from .models import Favorite, LearningProgress


def create_favorite(*, user, story_id) -> Favorite:
    """Save a story for *user*, rejecting duplicate saves."""
    story = get_object_or_404(Story, pk=story_id)
    try:
        with transaction.atomic():
            return Favorite.objects.create(user=user, story=story)
    except IntegrityError as exc:
        # The database constraint also protects this invariant under races.
        raise Conflict("This story is already in your favorites.") from exc


def remove_favorite(*, user, story_id) -> None:
    """Remove only the requesting user's saved story."""
    favorite = get_object_or_404(Favorite, user=user, story_id=story_id)
    favorite.delete()


def mark_story_complete(*, user, story_id) -> LearningProgress:
    """Mark a story complete without replacing its original completion time."""
    story = get_object_or_404(Story, pk=story_id)
    with transaction.atomic():
        progress, created = LearningProgress.objects.get_or_create(
            user=user,
            story=story,
            defaults={"is_completed": True, "completed_at": timezone.now()},
        )
        if not created:
            update_fields = []
            if not progress.is_completed:
                progress.is_completed = True
                update_fields.append("is_completed")
            if progress.completed_at is None:
                progress.completed_at = timezone.now()
                update_fields.append("completed_at")
            if update_fields:
                progress.save(update_fields=(*update_fields, "updated_at"))
    return progress

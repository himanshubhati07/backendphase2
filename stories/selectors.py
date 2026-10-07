"""Read-side query helpers for public catalogue endpoints."""
from __future__ import annotations

import uuid

from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from .models import Activity, Story


def active_stories(*, category: str | None = None, age_group: str | None = None, language: str | None = None) -> QuerySet[Story]:
    queryset = Story.objects.filter(is_active=True).select_related("category")
    if category:
        # Accept the UUID used by the API as well as a human-friendly category name.
        try:
            category_id = uuid.UUID(category)
        except (TypeError, ValueError, AttributeError):
            queryset = queryset.filter(category__name=category)
        else:
            queryset = queryset.filter(category_id=category_id)
    if age_group:
        queryset = queryset.filter(age_group=age_group)
    if language:
        queryset = queryset.filter(language=language)
    return queryset


def active_story_or_404(story_id: object) -> Story:
    return get_object_or_404(active_stories(), pk=story_id)


def search_active_stories(keyword: str | None) -> QuerySet[Story]:
    queryset = active_stories()
    if keyword and keyword.strip():
        term = keyword.strip()
        queryset = queryset.filter(Q(title__icontains=term) | Q(description__icontains=term) | Q(content__icontains=term))
    return queryset


def public_activities(story_id: object) -> QuerySet[Activity]:
    active_story_or_404(story_id)
    return Activity.objects.filter(story_id=story_id).select_related("story")

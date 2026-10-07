"""Engagement routes, included by the project under ``/api/v1/``."""

from django.urls import path

from .views import FavoriteCollectionView, FavoriteDetailView, ProgressCollectionView, ProgressDetailView

app_name = "engagement"

urlpatterns = [
    path("stories/<uuid:story_id>/favorite", FavoriteDetailView.as_view(), name="story-favorite"),
    path("favorites", FavoriteCollectionView.as_view(), name="favorites"),
    path("stories/<uuid:story_id>/complete", ProgressDetailView.as_view(), name="story-complete"),
    path("progress", ProgressCollectionView.as_view(), name="progress"),
    path("progress/<uuid:story_id>", ProgressDetailView.as_view(), name="progress-detail"),
]

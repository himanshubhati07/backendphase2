"""Version-relative story URL patterns (included beneath /api/v1/)."""
from django.urls import path

from .views import ActivityDetailView, StoryActivityCollectionView, StoryCollectionView, StoryDetailView, StorySearchView

urlpatterns = [
    path("stories", StoryCollectionView.as_view(), name="story-list"),
    path("stories/search", StorySearchView.as_view(), name="story-search"),
    path("stories/<uuid:id>", StoryDetailView.as_view(), name="story-detail"),
    path("stories/<uuid:story_id>/activities", StoryActivityCollectionView.as_view(), name="story-activities"),
    path("activities/<uuid:id>", ActivityDetailView.as_view(), name="activity-detail"),
]

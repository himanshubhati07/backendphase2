"""View facade for canonical HTTP adapters.

The classes below are the original endpoint views from their owner apps.  They
are re-exported for API-facing imports and are not wrapped or reimplemented.
"""

from accounts.views import LoginView, RegistrationView
from engagement.views import (
    FavoriteCollectionView,
    FavoriteDetailView,
    ProgressCollectionView,
    ProgressDetailView,
)
from stories.views import (
    ActivityDetailView,
    StoryActivityCollectionView,
    StoryCollectionView,
    StoryDetailView,
    StorySearchView,
)

__all__ = (
    "ActivityDetailView",
    "FavoriteCollectionView",
    "FavoriteDetailView",
    "LoginView",
    "ProgressCollectionView",
    "ProgressDetailView",
    "RegistrationView",
    "StoryActivityCollectionView",
    "StoryCollectionView",
    "StoryDetailView",
    "StorySearchView",
)

"""Serializer facade for the canonical resource apps.

These imports are aliases only.  Validation and representation behavior remain
owned by ``accounts``, ``stories``, and ``engagement``.
"""

from accounts.serializers import LoginSerializer, RegistrationSerializer, UserSerializer
from engagement.serializers import FavoriteSerializer, LearningProgressSerializer
from stories.serializers import (
    ActivityReadSerializer,
    ActivityWriteSerializer,
    CategorySerializer,
    StoryReadSerializer,
    StoryWriteSerializer,
)

__all__ = (
    "ActivityReadSerializer",
    "ActivityWriteSerializer",
    "CategorySerializer",
    "FavoriteSerializer",
    "LearningProgressSerializer",
    "LoginSerializer",
    "RegistrationSerializer",
    "StoryReadSerializer",
    "StoryWriteSerializer",
    "UserSerializer",
)

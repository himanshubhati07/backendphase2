"""Output serializers for engagement resources."""

from rest_framework import serializers

from .models import Favorite, LearningProgress


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ("id", "story", "created_at", "updated_at")
        read_only_fields = fields


class LearningProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningProgress
        fields = ("id", "story", "is_completed", "completed_at", "created_at", "updated_at")
        read_only_fields = fields

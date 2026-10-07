"""Serialization boundary for authentication endpoints."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from accounts.models import User, UserManager


class UserSerializer(serializers.ModelSerializer):
    """Public, password-free representation of a user."""

    class Meta:
        model = User
        fields = ("id", "email", "date_joined")
        read_only_fields = fields


class RegistrationSerializer(serializers.Serializer):
    """Validate a registration request without persisting it."""

    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=8)

    def validate_email(self, value: str) -> str:
        """Canonicalize email before it reaches the application service."""
        return UserManager.normalize_email_address(value)


class LoginSerializer(serializers.Serializer):
    """Validate a login request without exposing password data."""

    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value: str) -> str:
        """Canonicalize the login identity."""
        return UserManager.normalize_email_address(value)

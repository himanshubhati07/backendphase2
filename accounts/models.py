"""Account domain models."""

from __future__ import annotations

import uuid
from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager for email-address based users."""

    use_in_migrations = True

    @staticmethod
    def normalize_email_address(email: str) -> str:
        """Return the canonical value used for email uniqueness and login."""
        return BaseUserManager.normalize_email(email.strip()).lower()

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        """Create and persist a normal active user using Django password hashing."""
        if not email:
            raise ValueError("The email address must be set.")

        user = self.model(email=self.normalize_email_address(email), **extra_fields)
        if password is None:
            user.set_unusable_password()
        else:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        """Create an administrative user."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Application user identified by a canonical email address and UUID."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ("email",)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Maintain canonical email values even outside the manager."""
        self.email = UserManager.normalize_email_address(self.email)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email

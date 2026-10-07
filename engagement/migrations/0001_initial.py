# Generated manually for the engagement application.

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("stories", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Favorite",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorited_by", to="stories.story")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorites", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="LearningProgress",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_completed", models.BooleanField(default=False)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learning_progress_records", to="stories.story")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learning_progress", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-updated_at",)},
        ),
        migrations.AddConstraint(
            model_name="favorite",
            constraint=models.UniqueConstraint(fields=("user", "story"), name="unique_user_story_favorite"),
        ),
        migrations.AddIndex(
            model_name="favorite",
            index=models.Index(fields=["user", "story"], name="favorite_user_story_idx"),
        ),
        migrations.AddIndex(
            model_name="favorite",
            index=models.Index(fields=["user", "created_at"], name="favorite_user_created_idx"),
        ),
        migrations.AddConstraint(
            model_name="learningprogress",
            constraint=models.UniqueConstraint(fields=("user", "story"), name="unique_user_story_progress"),
        ),
        migrations.AddIndex(
            model_name="learningprogress",
            index=models.Index(fields=["user", "story"], name="progress_user_story_idx"),
        ),
        migrations.AddIndex(
            model_name="learningprogress",
            index=models.Index(fields=["user", "updated_at"], name="progress_user_updated_idx"),
        ),
    ]

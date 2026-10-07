# Generated manually for the stories application.
import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="Story",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("content", models.TextField()),
                ("age_group", models.CharField(choices=[("2-3", "2–3 years")], db_index=True, max_length=10)),
                ("language", models.CharField(choices=[("en", "English")], db_index=True, max_length=10)),
                ("cover_image_url", models.URLField(blank=True)),
                ("audio_url", models.URLField(blank=True)),
                ("duration_minutes", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("learning_objective", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stories", to="stories.category")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="Activity",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("question", models.TextField()),
                ("activity_type", models.CharField(max_length=50)),
                ("options", models.JSONField(blank=True, null=True)),
                ("correct_answer", models.CharField(max_length=255)),
                ("difficulty", models.CharField(max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activities", to="stories.story")),
            ],
            options={"ordering": ("created_at",)},
        ),
        migrations.AddIndex(model_name="story", index=models.Index(fields=["is_active", "category"], name="story_active_category_idx")),
        migrations.AddIndex(model_name="story", index=models.Index(fields=["is_active", "age_group", "language"], name="story_catalog_filter_idx")),
        migrations.AddIndex(model_name="story", index=models.Index(fields=["title"], name="story_title_idx")),
        migrations.AddConstraint(model_name="story", constraint=models.CheckConstraint(condition=Q(("duration_minutes__gt", 0)), name="story_duration_positive")),
        migrations.AddConstraint(model_name="story", constraint=models.CheckConstraint(condition=~Q(("title", "")), name="story_title_nonempty")),
        migrations.AddConstraint(model_name="story", constraint=models.CheckConstraint(condition=~Q(("content", "")), name="story_content_nonempty")),
        migrations.AddIndex(model_name="activity", index=models.Index(fields=["story", "created_at"], name="activity_story_created_idx")),
        migrations.AddConstraint(model_name="activity", constraint=models.CheckConstraint(condition=~Q(("question", "")), name="activity_question_nonempty")),
        migrations.AddConstraint(model_name="activity", constraint=models.CheckConstraint(condition=~Q(("activity_type", "")), name="activity_type_nonempty")),
        migrations.AddConstraint(model_name="activity", constraint=models.CheckConstraint(condition=~Q(("correct_answer", "")), name="activity_answer_nonempty")),
        migrations.AddConstraint(model_name="activity", constraint=models.CheckConstraint(condition=~Q(("difficulty", "")), name="activity_difficulty_nonempty")),
    ]

"""Focused catalogue validation and seed command tests."""
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from .models import Category, Story
from .serializers import ActivityWriteSerializer, StoryWriteSerializer
from .selectors import active_stories, search_active_stories


class StoryValidationTests(TestCase):
    def setUp(self) -> None:
        self.category = Category.objects.create(name="Test category")

    def test_rejects_blank_content_and_nonpositive_duration(self) -> None:
        serializer = StoryWriteSerializer(data={
            "title": "A title", "content": "   ", "category": self.category.pk,
            "age_group": "2-3", "language": "en", "duration_minutes": 0,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("content", serializer.errors)
        self.assertIn("duration_minutes", serializer.errors)

    def test_catalogue_options_accept_configured_values_and_reject_unsupported_values(self) -> None:
        self.assertEqual(
            tuple(value for value, _label in Story.LANGUAGE_CHOICES),
            settings.SUPPORTED_STORY_LANGUAGES,
        )
        self.assertEqual(
            tuple(value for value, _label in Story.AGE_GROUP_CHOICES),
            settings.SUPPORTED_STORY_AGE_GROUPS,
        )

        accepted = StoryWriteSerializer(data={
            "title": "A title", "content": "Story content", "category": self.category.pk,
            "age_group": settings.SUPPORTED_STORY_AGE_GROUPS[0],
            "language": settings.SUPPORTED_STORY_LANGUAGES[0], "duration_minutes": 1,
        })
        self.assertTrue(accepted.is_valid(), accepted.errors)

        rejected = StoryWriteSerializer(data={
            "title": "A title", "content": "Story content", "category": self.category.pk,
            "age_group": "unsupported", "language": "unsupported", "duration_minutes": 1,
        })
        self.assertFalse(rejected.is_valid())
        self.assertIn("age_group", rejected.errors)
        self.assertIn("language", rejected.errors)

    @override_settings(SUPPORTED_STORY_LANGUAGES=("es",), SUPPORTED_STORY_AGE_GROUPS=("4-5",))
    def test_serializer_uses_current_catalogue_option_settings(self) -> None:
        serializer = StoryWriteSerializer(data={
            "title": "Un título", "content": "Contenido", "category": self.category.pk,
            "age_group": "4-5", "language": "es", "duration_minutes": 1,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_options_must_be_an_array(self) -> None:
        serializer = ActivityWriteSerializer(data={
            "question": "What color?", "activity_type": "color", "options": {"red": 1},
            "correct_answer": "red", "difficulty": "easy",
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("options", serializer.errors)


class PublicCatalogueSelectorTests(TestCase):
    def setUp(self) -> None:
        category = Category.objects.create(name="Animals")
        self.active = Story.objects.create(title="Little Bunny", content="Hop along", category=category, age_group="2-3", language="en", duration_minutes=2)
        Story.objects.create(title="Hidden Bunny", content="Not public", category=category, age_group="2-3", language="en", duration_minutes=2, is_active=False)

    def test_public_queries_exclude_inactive_and_search(self) -> None:
        self.assertEqual(list(active_stories()), [self.active])
        self.assertEqual(list(search_active_stories("bunny")), [self.active])


class SeedStoriesTests(TestCase):
    def test_seed_is_idempotent(self) -> None:
        call_command("seed_stories")
        call_command("seed_stories")
        self.assertEqual(Category.objects.count(), 8)
        self.assertGreaterEqual(Story.objects.filter(is_active=True, language="en", age_group="2-3").count(), 10)

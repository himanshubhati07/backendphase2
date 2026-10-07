"""Seed the catalogue with a small, repeatable toddler-friendly library."""
from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from stories.models import Category, Story


CATEGORIES = ("Animals", "Colors", "Counting", "Shapes", "Nature", "Family", "Feelings", "Daily Routines")
STORIES = (
    ("The Little Bunny", "Animals", "A little bunny looks for a soft place to rest.", "Bunny hops through the grass, says hello to friends, and finds a cozy burrow.", 3),
    ("Colors Around Us", "Colors", "A walk to find bright colors.", "We see red apples, blue sky, and yellow flowers all around us.", 3),
    ("Five Little Ducks", "Counting", "Five ducklings swim with their mother.", "One, two, three, four, five little ducks splash and quack by the pond.", 3),
    ("My First Shapes", "Shapes", "Friendly shapes are everywhere.", "A circle rolls, a square sits, and a triangle points up high.", 2),
    ("Good Morning, Sun", "Daily Routines", "A gentle start to the day.", "Good morning, sun. We wake up, wash our face, and eat breakfast.", 3),
    ("Milo Finds a Leaf", "Nature", "Milo notices autumn colors.", "Milo picks up a crunchy leaf and watches it twirl down from a tree.", 3),
    ("Hug for Grandma", "Family", "A warm family visit.", "Nia makes a picture for Grandma and gives her a big, gentle hug.", 2),
    ("The Happy Raincloud", "Feelings", "A cloud learns that feelings can change.", "A small cloud feels blue, then sees children dancing in warm rain.", 3),
    ("Teddy Counts To Three", "Counting", "Teddy counts snack berries.", "Teddy has one berry, two berries, and three berries to share.", 2),
    ("Pip the Tiny Puppy", "Animals", "Pip learns to be brave.", "Pip takes three small steps outside and meets a kind butterfly.", 3),
)


class Command(BaseCommand):
    help = "Create the standard categories and sample active stories."

    def handle(self, *args: object, **options: object) -> None:
        categories = {name: Category.objects.get_or_create(name=name)[0] for name in CATEGORIES}
        for title, category_name, description, content, duration in STORIES:
            Story.objects.update_or_create(
                title=title,
                defaults={
                    "category": categories[category_name],
                    "description": description,
                    "content": content,
                    "age_group": settings.SUPPORTED_STORY_AGE_GROUPS[0],
                    "language": settings.SUPPORTED_STORY_LANGUAGES[0],
                    "duration_minutes": duration,
                    "learning_objective": "Build early language and observation skills.",
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS("Seeded 8 categories and 10 stories."))

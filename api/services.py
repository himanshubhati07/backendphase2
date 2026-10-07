"""Service facade for the canonical domain apps.

All operations are re-exported from their owning applications; this module
adds no business behavior or persistence paths.
"""

from accounts.services import authenticate_user, register_user, token_data_for_user
from engagement.services import create_favorite, mark_story_complete, remove_favorite
from stories.services import (
    create_activity,
    create_story,
    delete_activity,
    delete_story,
    replace_activity,
    replace_story,
)

__all__ = (
    "authenticate_user",
    "create_activity",
    "create_favorite",
    "create_story",
    "delete_activity",
    "delete_story",
    "mark_story_complete",
    "register_user",
    "remove_favorite",
    "replace_activity",
    "replace_story",
    "token_data_for_user",
)

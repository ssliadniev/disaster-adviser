"""User & Preferences Module

Domain exceptions and business logic.
"""

from app.modules.user.preferences import (
    apply_preference_updates,
)
from app.modules.user.exceptions import (
    UserNotFoundError,
    PreferencesNotFoundError,
    InvalidPreferencesError,
)

__all__ = [
    "apply_preference_updates",
    "UserNotFoundError",
    "PreferencesNotFoundError",
    "InvalidPreferencesError",
]

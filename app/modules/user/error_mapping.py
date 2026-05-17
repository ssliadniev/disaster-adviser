"""Error mapping configuration for user domain.

This module defines how domain exceptions map to HTTP status codes.
"""
from fastapi import status

from app.modules.user.exceptions import (
    UserNotFoundError,
    PreferencesNotFoundError,
    InvalidPreferencesError,
)
from app.utils.error_handlers import create_error_mapper


user_error_mapper = create_error_mapper({
    UserNotFoundError: (status.HTTP_404_NOT_FOUND, lambda e: str(e)),
    PreferencesNotFoundError: (status.HTTP_400_BAD_REQUEST, lambda e: str(e)),
    InvalidPreferencesError: (status.HTTP_400_BAD_REQUEST, lambda e: str(e)),
    ValueError: (status.HTTP_400_BAD_REQUEST, lambda e: str(e)),
})
"""User domain exceptions."""


class UserNotFoundError(Exception):
    """Raised when user is not found"""

    pass


class PreferencesNotFoundError(Exception):
    """Raised when preferences are not found"""

    pass


class InvalidPreferencesError(Exception):
    """Raised when preference values are invalid"""

    pass

class WebhookRegistrationError(Exception):
    """Raised when webhook registration with Google fails"""

    pass


class WebhookNotFoundError(Exception):
    """Raised when webhook channel or user is not found"""

    pass


class WebhookPermissionError(Exception):
    """Raised when user lacks permission for webhook operation"""

    pass


class TravelPlanNotFoundError(Exception):
    """Raised when travel plan is not found"""

    pass

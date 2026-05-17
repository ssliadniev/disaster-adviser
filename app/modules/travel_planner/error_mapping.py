"""Error mapping configuration for travel planner domain."""
from fastapi import status

from app.modules.travel_planner.exceptions import (
    WebhookRegistrationError,
    WebhookNotFoundError,
    WebhookPermissionError,
    TravelPlanNotFoundError,
)
from app.utils.error_handlers import create_error_mapper


webhook_error_mapper = create_error_mapper({
    WebhookRegistrationError: (status.HTTP_500_INTERNAL_SERVER_ERROR, lambda e: str(e)),
    WebhookNotFoundError: (status.HTTP_404_NOT_FOUND, lambda e: str(e)),
    WebhookPermissionError: (status.HTTP_403_FORBIDDEN, lambda e: str(e)),
    TravelPlanNotFoundError: (status.HTTP_404_NOT_FOUND, lambda e: str(e)),
    ValueError: (status.HTTP_400_BAD_REQUEST, lambda e: str(e)),
})
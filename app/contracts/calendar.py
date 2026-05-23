from datetime import datetime
from typing import TypedDict, Literal
from pydantic import BaseModel


class EventDetails(TypedDict, total=False):
    id: str
    summary: str
    location: str | None
    start: str | None
    end: str | None
    description: str | None
    error: str


class TravelPlanData(TypedDict, total=False):
    event_id: str
    calendar_id: str
    event_summary: str
    location_name: str | None
    latitude: float | None
    longitude: float | None
    start_time: datetime
    end_time: datetime


class WebhookRegisterResponse(BaseModel):
    channel_id: str
    resource_id: str | None
    expiration: str | None
    webhook_url: str
    message: str
    note: str


class WebhookEventResponse(BaseModel):
    status: str
    type: str
    message: str
    user: str | None
    event: dict | None


class WebhookChannel(TypedDict):
    """Webhook channel response"""

    channel_id: str
    resource_id: str | None
    expiration: str | None
    webhook_url: str


class NotificationResult(TypedDict):
    """Notification processing result"""

    status: Literal["acknowledged", "processed", "ok"]
    type: str
    message: str
    user: str | None
    event: dict | None


ResourceState = Literal["sync", "exists", "not_exists"]

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.risk import Severity


class AlertKind(str, Enum):
    DIRECT = "DIRECT"
    HOTSPOT = "HOTSPOT"


class Notification(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: str
    travel_plan_id: str
    kind: AlertKind
    source_key: str
    severity: Severity
    risk_score: float
    subject: str
    body: str
    email_to: str | None = None
    disaster_event_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    notification: Notification
    created_at: datetime


class NotificationResponse(BaseModel):
    id: int | None = None
    user_id: int | str
    travel_plan_id: int | str | None = None
    kind: str
    source_key: str
    severity: str
    risk_score: float
    subject: str
    body: str
    recipient_email: str | None = None
    disaster_event_id: str | None = None
    sent_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]


class NotificationRecomputeResponse(BaseModel):
    assessments: list[dict]
    hotspot_warnings: list[dict]
    notifications: list[NotificationResponse]

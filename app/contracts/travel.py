from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_validator


class TravelPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    user_id: str
    title: str
    start_at: datetime
    end_at: datetime
    city: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("start_at", "end_at", mode="before")
    @classmethod
    def _normalize_trip_dt(cls, value: datetime | str) -> datetime:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value if value.tzinfo else value.replace(tzinfo=UTC)


class TravelPlanResponse(BaseModel):
    id: int
    user_id: int
    event_id: str
    calendar_id: str
    title: str
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    start_at: datetime
    end_at: datetime


class TravelPlanListResponse(BaseModel):
    travel_plans: list[TravelPlanResponse]

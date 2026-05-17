from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.contracts.risk import Severity


class HotspotWarning(BaseModel):
    model_config = ConfigDict(frozen=True)

    travel_plan_id: str
    user_id: str
    location_name: str
    hotspot_score: float
    severity: Severity
    event_ids: tuple[str, ...]
    radius_km: float
    lookback_days: int


class HotspotRegionStat(BaseModel):
    model_config = ConfigDict(frozen=True)

    region_key: str
    center_latitude: float
    center_longitude: float
    event_count: int
    weighted_score: float
    severity: Severity
    latest_event_at: datetime
    event_ids: tuple[str, ...]
    lookback_days: int


class HotspotRegionResponse(BaseModel):
    region_key: str
    center_latitude: float
    center_longitude: float
    event_count: int
    weighted_score: float
    severity: str
    latest_event_at: datetime
    event_ids: list[str]
    lookback_days: int


class HotspotListResponse(BaseModel):
    hotspots: list[HotspotRegionResponse]

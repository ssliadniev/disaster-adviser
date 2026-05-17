from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    travel_plan_id: str
    user_id: str
    disaster_event_id: str
    distance_km: float
    time_delta_days: float
    risk_score: float
    severity: Severity
    matched: bool
    reason: str | None = None

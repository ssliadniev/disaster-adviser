from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from app.contracts.disaster import StandardDisasterEvent
from app.contracts.risk import RiskAssessment, Severity
from app.contracts.travel import TravelPlan
from app.contracts.user import UserPreferences
from app.utils.functional import (
    Maybe,
    Nothing,
    Some,
)

CATEGORY_WEIGHTS: dict[str, float] = {
    "severe storm": 1.0,
    "wildfire": 0.95,
    "flood": 0.9,
    "volcanic eruption": 0.85,
    "volcanic_eruption": 0.85,
    "earthquake": 1.0,
    "drought": 0.6,
}


def _normalize_category(category: object) -> str:
    raw = category.value if hasattr(category, "value") else category
    normalized = str(raw).strip().lower().replace("_", " ").replace("-", " ")
    aliases = {
        "severe storms": "severe storm",
        "storms": "severe storm",
        "storm": "severe storm",
        "wildfires": "wildfire",
        "fires": "wildfire",
        "floods": "flood",
        "earthquakes": "earthquake",
        "volcanoes": "volcanic eruption",
        "volcano": "volcanic eruption",
        "volcanic eruption": "volcanic eruption",
        "volcanic activity": "volcanic eruption",
    }
    return aliases.get(normalized, normalized)


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if (lat1, lon1) == (lat2, lon2):
        return 0.0

    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(
        radians, (lat1, lon1, lat2, lon2)
    )
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad
    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    return 6371.0 * 2 * asin(sqrt(haversine))


def matches_time_window(
    event: StandardDisasterEvent, plan: TravelPlan, prefs: UserPreferences
) -> bool:
    if event.date > plan.start_at:
        return False
    delta_days = (plan.start_at - event.date).total_seconds() / 86400
    return 0 <= delta_days <= prefs.max_days_ahead


def calculate_risk_score(
    distance: float, time_delta_days: float, category: object
) -> float:
    category_weight = CATEGORY_WEIGHTS.get(_normalize_category(category), 0.7)
    distance_component = 1 / (1 + distance / 50)
    time_component = 1 / (1 + time_delta_days / 2)
    score = (0.45 * distance_component) + (0.35 * time_component) + (0.20 * category_weight)
    return round(min(1.0, score), 4)


def _severity_from_score(score: float) -> Severity:
    if score >= 0.8:
        return Severity.HIGH
    if score >= 0.6:
        return Severity.MEDIUM
    return Severity.LOW


def _category_enabled(category: object, prefs: UserPreferences) -> bool:
    normalized = _normalize_category(category)
    enabled = {_normalize_category(item) for item in prefs.enabled_categories}
    return normalized in enabled


def _with_distance(
    args: tuple[StandardDisasterEvent, TravelPlan, UserPreferences]
) -> Maybe[tuple[StandardDisasterEvent, TravelPlan, UserPreferences, float]]:
    event, plan, prefs = args
    assert plan.latitude is not None
    assert plan.longitude is not None
    distance = distance_km(event.latitude, event.longitude, plan.latitude, plan.longitude)
    return (
        Some((event, plan, prefs, distance))
        if distance <= prefs.max_distance_km
        else Nothing()
    )


def _build_assessment(
    args: tuple[StandardDisasterEvent, TravelPlan, UserPreferences, float]
) -> RiskAssessment:
    event, plan, _prefs, distance = args
    time_delta_days = (plan.start_at - event.date).total_seconds() / 86400
    score = calculate_risk_score(distance, time_delta_days, event.category)
    return RiskAssessment(
        travel_plan_id=plan.id,
        user_id=plan.user_id,
        disaster_event_id=event.id,
        distance_km=round(distance, 3),
        time_delta_days=round(time_delta_days, 3),
        risk_score=score,
        severity=_severity_from_score(score),
        matched=True,
    )


def assess_risk(
    event: StandardDisasterEvent, plan: TravelPlan, prefs: UserPreferences
) -> RiskAssessment | None:
    assessment = (
        Some((event, plan, prefs))
        .filter(lambda args: args[2].notifications_enabled)
        .filter(lambda args: _category_enabled(args[0].category, args[2]))
        .filter(lambda args: args[1].latitude is not None and args[1].longitude is not None)
        .filter(lambda args: matches_time_window(args[0], args[1], args[2]))
        .flat_map(_with_distance)
        .map(_build_assessment)
    )
    return assessment.get_or_else(None)

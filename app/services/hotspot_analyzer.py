from __future__ import annotations

from datetime import datetime, timedelta

from app.core.config import settings
from app.contracts.disaster import StandardDisasterEvent
from app.contracts.hotspot import HotspotWarning
from app.contracts.risk import Severity
from app.contracts.travel import TravelPlan
from app.services.risk_analyzer import CATEGORY_WEIGHTS, _normalize_category, distance_km
from app.utils.functional import (
    Some,
)


def _category_weight(category: object) -> float:
    return CATEGORY_WEIGHTS.get(_normalize_category(category), 0.7)


def _event_contribution(
    event: StandardDisasterEvent, destination: TravelPlan, now: datetime
) -> float:
    assert destination.latitude is not None
    assert destination.longitude is not None

    distance = distance_km(
        event.latitude, event.longitude, destination.latitude, destination.longitude
    )
    if distance > settings.HOTSPOT_RADIUS_KM:
        return 0.0

    event_age_days = max(0.0, (now - event.date).total_seconds() / 86400)
    if event_age_days > settings.HOTSPOT_LOOKBACK_DAYS:
        return 0.0

    recency_factor = 1 - (event_age_days / settings.HOTSPOT_LOOKBACK_DAYS)
    distance_factor = 1 - (distance / settings.HOTSPOT_RADIUS_KM)
    active_bonus = settings.HOTSPOT_ACTIVE_BONUS if event.closed is None else 0.0
    return max(
        0.0,
        (_category_weight(event.category) * recency_factor * max(distance_factor, 0.1))
        + active_bonus,
    )


def calculate_hotspot_score(
    events: list[StandardDisasterEvent], destination: TravelPlan, now: datetime
) -> float:
    if destination.latitude is None or destination.longitude is None:
        return 0.0
    return round(sum(_event_contribution(event, destination, now) for event in events), 4)


def _severity_from_hotspot(score: float) -> Severity:
    if score >= settings.HOTSPOT_THRESHOLD + 1:
        return Severity.HIGH
    if score >= settings.HOTSPOT_THRESHOLD:
        return Severity.MEDIUM
    return Severity.LOW


def _build_hotspot_warning(
    args: tuple[TravelPlan, list[StandardDisasterEvent], float, datetime]
) -> HotspotWarning:
    destination, relevant_events, score, now = args
    contributing_ids = tuple(
        event.id
        for event in relevant_events
        if _event_contribution(event, destination, now) > 0
    )
    location_name = ", ".join(filter(None, [destination.city, destination.country])) or destination.title
    return HotspotWarning(
        travel_plan_id=destination.id,
        user_id=destination.user_id,
        location_name=location_name,
        hotspot_score=score,
        severity=_severity_from_hotspot(score),
        event_ids=contributing_ids,
        radius_km=settings.HOTSPOT_RADIUS_KM,
        lookback_days=settings.HOTSPOT_LOOKBACK_DAYS,
    )


def assess_hotspot(
    events: list[StandardDisasterEvent], destination: TravelPlan, now: datetime
) -> HotspotWarning | None:
    active_window_start = now - timedelta(days=settings.HOTSPOT_LOOKBACK_DAYS)
    relevant_events = [
        event for event in events if active_window_start <= event.date <= now
    ]
    score = calculate_hotspot_score(relevant_events, destination, now)
    warning = (
        Some((destination, relevant_events, score, now))
        .filter(lambda args: args[0].latitude is not None and args[0].longitude is not None)
        .filter(lambda args: args[2] >= settings.HOTSPOT_THRESHOLD)
        .map(_build_hotspot_warning)
    )
    return warning.get_or_else(None)

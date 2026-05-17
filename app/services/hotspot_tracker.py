from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from math import floor

from app.core.config import settings
from app.contracts.disaster import StandardDisasterEvent
from app.contracts.hotspot import HotspotRegionStat
from app.contracts.risk import Severity
from app.services.risk_analyzer import CATEGORY_WEIGHTS, _normalize_category
from app.utils.functional import (
    Maybe,
    Some,
    compose,
    pipe,
)


def _severity_from_score(score: float) -> Severity:
    if score >= settings.HOTSPOT_THRESHOLD + 1:
        return Severity.HIGH
    if score >= settings.HOTSPOT_THRESHOLD:
        return Severity.MEDIUM
    return Severity.LOW


def region_key(
    latitude: float,
    longitude: float,
    grid_degrees: float = settings.HOTSPOT_GRID_DEGREES,
) -> str:
    lat_bucket = floor((latitude + 90.0) / grid_degrees)
    lon_bucket = floor((longitude + 180.0) / grid_degrees)
    return f"{grid_degrees:.2f}:{lat_bucket}:{lon_bucket}"


def region_center(region_key_value: str) -> tuple[float, float]:
    grid_part, lat_bucket, lon_bucket = region_key_value.split(":")
    grid_degrees = float(grid_part)
    lat_index = int(lat_bucket)
    lon_index = int(lon_bucket)
    center_lat = (lat_index * grid_degrees) - 90.0 + (grid_degrees / 2)
    center_lon = (lon_index * grid_degrees) - 180.0 + (grid_degrees / 2)
    return round(center_lat, 4), round(center_lon, 4)


def calculate_event_weight(
    event: StandardDisasterEvent,
    now: datetime,
    lookback_days: int = settings.HOTSPOT_LOOKBACK_DAYS,
) -> float:
    age_days = max(0.0, (now - event.date).total_seconds() / 86400)
    if age_days > lookback_days:
        return 0.0

    recency_factor = 1 - (age_days / lookback_days)
    category_weight = CATEGORY_WEIGHTS.get(_normalize_category(event.category), 0.7)
    active_bonus = settings.HOTSPOT_ACTIVE_BONUS if event.closed is None else 0.0
    return round(max(0.0, (category_weight * recency_factor) + active_bonus), 4)


def _build_region_stat(
    args: tuple[str, list[StandardDisasterEvent], datetime]
) -> Maybe[HotspotRegionStat]:
    key, region_events, now = args
    weighted_score = round(
        sum(calculate_event_weight(event, now) for event in region_events), 4
    )

    candidate: Maybe[tuple[str, list[StandardDisasterEvent], datetime, float]] = Some(
        (key, region_events, now, weighted_score)
    )
    candidate = candidate.filter(lambda item: item[3] > 0)
    return candidate.map(_to_region_stat)


def _to_region_stat(
    args: tuple[str, list[StandardDisasterEvent], datetime, float]
) -> HotspotRegionStat:
    key, region_events, _now, weighted_score = args
    center_latitude, center_longitude = region_center(key)
    latest_event_at = max(event.date for event in region_events)
    event_ids = tuple(sorted({event.id for event in region_events}))
    return HotspotRegionStat(
        region_key=key,
        center_latitude=center_latitude,
        center_longitude=center_longitude,
        event_count=len(region_events),
        weighted_score=weighted_score,
        severity=_severity_from_score(weighted_score),
        latest_event_at=latest_event_at,
        event_ids=event_ids,
        lookback_days=settings.HOTSPOT_LOOKBACK_DAYS,
    )


def build_hotspot_stats(
    events: list[StandardDisasterEvent],
    now: datetime,
    grid_degrees: float = settings.HOTSPOT_GRID_DEGREES,
) -> list[HotspotRegionStat]:
    window_start = now - timedelta(days=settings.HOTSPOT_LOOKBACK_DAYS)
    grouped: dict[str, list[StandardDisasterEvent]] = defaultdict(list)

    for event in events:
        if window_start <= event.date <= now:
            grouped[region_key(event.latitude, event.longitude, grid_degrees)].append(
                event
            )

    stats = [
        _build_region_stat((key, region_events, now)).get_or_else(None)
        for key, region_events in grouped.items()
    ]
    return sorted(
        [stat for stat in stats if stat is not None],
        key=lambda item: item.weighted_score,
        reverse=True,
    )


def top_hotspots(
    stats: list[HotspotRegionStat],
    *,
    limit: int,
    minimum_score: float = 0.0,
) -> list[HotspotRegionStat]:
    rank_hotspots = compose(
        lambda items: [stat for stat in items if stat.weighted_score >= minimum_score],
        lambda items: items[:limit],
    )
    return rank_hotspots(stats)

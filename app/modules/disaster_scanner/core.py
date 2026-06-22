import logging

from datetime import datetime, timezone
from typing import List, Optional

from app.contracts.disaster import StandardDisasterEvent, DisasterSource

logger = logging.getLogger(__name__)


def _pick_localized(values: Optional[List[dict]], locale: str = "en") -> Optional[str]:
    if not values:
        return None

    for entry in values:
        if isinstance(entry, dict) and entry.get("locale") == locale:
            return entry.get("value")

    first = values[0]
    return first.get("value") if isinstance(first, dict) else None


def normalize_nasa_event(raw_event: dict) -> StandardDisasterEvent:
    geometry = sorted(
        raw_event.get("geometry") or [],
        key=lambda g: g.get("date", ""),
        reverse=True,
    )
    latest = geometry[0] if geometry else {}

    coords = latest.get("coordinates") or []

    if len(coords) >= 2 and all(isinstance(c, (int, float)) for c in coords[:2]):
        lon, lat = coords[0], coords[1]
    else:
        raise ValueError(f"Geometry missing or not a simple 2D point. Coords: {coords}")

    categories = raw_event.get("categories") or []
    raw_date = latest.get("date", "1970-01-01T00:00:00Z")

    raw_closed = raw_event.get("closed")
    closed = (
        datetime.fromisoformat(raw_closed.replace("Z", "+00:00"))
        if isinstance(raw_closed, str) and raw_closed
        else None
    )

    return StandardDisasterEvent(
        id=str(raw_event.get("id", "UNKNOWN")),
        title=raw_event.get("title", "Untitled Event"),
        category=categories[0].get("title", "Unknown") if categories else "Unknown",
        longitude=float(lon),
        latitude=float(lat),
        date=datetime.fromisoformat(raw_date.replace("Z", "+00:00")),
        source=DisasterSource.NASA,
        closed=closed,
    )


def normalize_pdc_event(raw_event: dict) -> StandardDisasterEvent:
    """
    Pure mapping: DisasterAWARE (PDC) V2 hazard -> StandardDisasterEvent.

    The V2 schema differs substantially from the old code this replaces:
      * timestamps are Unix *seconds* (the old code divided by 1000 for ms),
      * the human name lives in a localized `name` array (not `hazard_Name`),
      * the disaster phenomenon is in `type` (EARTHQUAKE/CYCLONE/...), which is
        the closest analogue to NASA's category.
    """

    epoch_seconds = (
        raw_event.get("updatedAt")
        or raw_event.get("startedAt")
        or raw_event.get("createdAt")
        or 0
    )

    ended_at = raw_event.get("endedAt")
    closed = (
        datetime.fromtimestamp(int(ended_at), tz=timezone.utc)
        if raw_event.get("severity") == "TERMINATION" and ended_at
        else None
    )

    return StandardDisasterEvent(
        id=str(raw_event.get("uuid", "UNKNOWN")),
        title=_pick_localized(raw_event.get("name")) or "Untitled Event",
        category=raw_event.get("type", "Unknown"),
        latitude=float(raw_event.get("latitude", 0.0) or 0.0),
        longitude=float(raw_event.get("longitude", 0.0) or 0.0),
        date=datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc),
        source=DisasterSource.PDC,
        closed=closed,
    )


def normalize_router(raw_event: dict) -> StandardDisasterEvent:
    """
    Route a raw event to the correct pure normalizer by shape.
    """

    if "geometry" in raw_event:
        return normalize_nasa_event(raw_event)

    return normalize_pdc_event(raw_event)


def try_normalize(raw_event: dict) -> Optional[StandardDisasterEvent]:
    try:
        return normalize_router(raw_event)
    except Exception as exc:
        ident = raw_event.get("id") or raw_event.get("uuid")
        logger.info(f"Skipping unparseable event {ident} ({exc})")
        return None

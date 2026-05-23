from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.disaster import DisasterCategory
from app.contracts.disaster import StandardDisasterEvent
from app.contracts.hotspot import HotspotRegionStat
from app.core.config import settings
from app.db.crud import disaster_event as disaster_event_crud
from app.db.crud import hotspot_region as hotspot_region_crud
from app.services.hotspot_tracker import build_hotspot_stats


def to_domain_disaster_row(row: dict) -> StandardDisasterEvent:
    return StandardDisasterEvent(
        id=row["external_event_id"],
        title=row["title"],
        category=DisasterCategory.from_string(row["category"]),
        latitude=row["latitude"],
        longitude=row["longitude"],
        date=row["event_date"],
        source=row["source"],
        closed=row.get("closed_at"),
    )


async def refresh_hotspot_regions(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> list[HotspotRegionStat]:
    current_time = now or datetime.now(UTC)
    recent_rows = await disaster_event_crud.get_recent_events(
        session,
        since=current_time - timedelta(days=settings.HOTSPOT_LOOKBACK_DAYS),
    )
    recent_events = [to_domain_disaster_row(row) for row in recent_rows]
    stats = build_hotspot_stats(recent_events, current_time)
    await hotspot_region_crud.replace_snapshot(session, stats)
    return stats


async def list_global_hotspots(
    session: AsyncSession,
    *,
    limit: int,
    refresh: bool = False,
) -> list[dict]:
    if refresh:
        await refresh_hotspot_regions(session)
    return await hotspot_region_crud.get_top_regions(session, limit=limit)

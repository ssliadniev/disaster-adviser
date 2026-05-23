from __future__ import annotations

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import hotspot_regions_table
from app.db.utils import rows_to_list
from app.contracts.hotspot import HotspotRegionStat


async def replace_snapshot(
    session: AsyncSession,
    stats: list[HotspotRegionStat],
) -> list[dict]:
    await session.execute(delete(hotspot_regions_table))
    if stats:
        await session.execute(
            insert(hotspot_regions_table),
            [
                dict(
                    region_key=stat.region_key,
                    center_latitude=stat.center_latitude,
                    center_longitude=stat.center_longitude,
                    event_count=stat.event_count,
                    weighted_score=stat.weighted_score,
                    severity=stat.severity.value,
                    latest_event_at=stat.latest_event_at,
                    event_ids=list(stat.event_ids),
                    lookback_days=stat.lookback_days,
                )
                for stat in stats
            ],
        )
    await session.commit()
    return await get_top_regions(session, limit=max(len(stats), 1))


async def get_top_regions(session: AsyncSession, *, limit: int) -> list[dict]:
    stmt = (
        select(hotspot_regions_table)
        .order_by(hotspot_regions_table.c.weighted_score.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return rows_to_list(result)

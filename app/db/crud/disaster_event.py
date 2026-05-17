from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud import base
from app.db.models import disaster_events_table
from app.db.utils import rows_to_list


async def get_by_external_key(
    session: AsyncSession,
    *,
    external_event_id: str,
    source: str,
) -> dict | None:
    return await base.get_by_fields(
        session,
        disaster_events_table,
        external_event_id=external_event_id,
        source=source,
    )


async def upsert_disaster_event(
    session: AsyncSession,
    *,
    external_event_id: str,
    title: str,
    category: str,
    latitude: float,
    longitude: float,
    event_date: datetime,
    source: str,
    closed_at: datetime | None = None,
) -> dict:
    existing = await get_by_external_key(
        session,
        external_event_id=external_event_id,
        source=source,
    )
    values = dict(
        title=title,
        category=category,
        latitude=latitude,
        longitude=longitude,
        event_date=event_date,
        closed_at=closed_at,
        last_seen_at=datetime.now(UTC),
    )
    if existing:
        return await base.update_by_id(
            session,
            disaster_events_table,
            existing["id"],
            **values,
        )

    return await base.create(
        session,
        disaster_events_table,
        external_event_id=external_event_id,
        source=source,
        **values,
    )


async def get_recent_events(
    session: AsyncSession,
    *,
    since: datetime,
) -> list[dict]:
    stmt = (
        select(disaster_events_table)
        .where(disaster_events_table.c.event_date >= since)
        .order_by(disaster_events_table.c.event_date.desc())
    )
    result = await session.execute(stmt)
    return rows_to_list(result)


async def get_active_events(session: AsyncSession) -> list[dict]:
    stmt = (
        select(disaster_events_table)
        .where(disaster_events_table.c.closed_at.is_(None))
        .order_by(disaster_events_table.c.event_date.desc())
    )
    result = await session.execute(stmt)
    return rows_to_list(result)

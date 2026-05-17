from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import travel_plans_table
from app.db.utils import rows_to_list
from app.db.crud import base


async def create(
    session: AsyncSession,
    *,
    user_id: int,
    event_id: str,
    calendar_id: str,
    event_summary: str,
    location_name: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    start_time: datetime,
    end_time: datetime,
) -> dict:
    """Create a new travel plan"""
    return await base.create(
        session,
        travel_plans_table,
        user_id=user_id,
        event_id=event_id,
        calendar_id=calendar_id,
        event_summary=event_summary,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        start_time=start_time,
        end_time=end_time,
    )


async def get_by_id(session: AsyncSession, travel_plan_id: int) -> dict | None:
    """Get travel plan by ID"""
    return await base.get_by_id(session, travel_plans_table, travel_plan_id)


async def get_by_event_id(
    session: AsyncSession, user_id: int, event_id: str
) -> dict | None:
    """Get travel plan by event ID"""
    return await base.get_by_fields(
        session,
        travel_plans_table,
        user_id=user_id,
        event_id=event_id,
    )


async def get_by_user_and_timerange(
    session: AsyncSession,
    user_id: int,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """Get all travel plans for a user within a time range"""
    stmt = (
        select(travel_plans_table)
        .where(
            travel_plans_table.c.user_id == user_id,
            travel_plans_table.c.start_time >= start,
            travel_plans_table.c.end_time <= end,
        )
        .order_by(travel_plans_table.c.start_time)
    )
    result = await session.execute(stmt)
    return rows_to_list(result)


async def get_all_by_user(session: AsyncSession, user_id: int) -> list[dict]:
    """Get all travel plans for a user"""
    return await base.get_all(
        session,
        travel_plans_table,
        order_by="start_time",
        user_id=user_id,
    )


async def update_coordinates(
    session: AsyncSession,
    travel_plan_id: int,
    latitude: float,
    longitude: float,
) -> dict | None:
    """Update coordinates for a travel plan"""
    return await base.update_by_id(
        session,
        travel_plans_table,
        travel_plan_id,
        latitude=latitude,
        longitude=longitude,
    )


async def update_travel_plan(
    session: AsyncSession,
    travel_plan_id: int,
    **kwargs,
) -> dict | None:
    """Update travel plan fields"""
    return await base.update_by_id(
        session, travel_plans_table, travel_plan_id, **kwargs
    )


async def upsert_travel_plan(
    session: AsyncSession,
    *,
    user_id: int,
    event_id: str,
    calendar_id: str,
    event_summary: str,
    location_name: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    start_time: datetime,
    end_time: datetime,
) -> dict:
    """Create or update a travel plan if it already exists"""
    existing = await get_by_event_id(session, user_id, event_id)

    if existing:
        return await update_travel_plan(
            session,
            existing["id"],
            calendar_id=calendar_id,
            event_summary=event_summary,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            start_time=start_time,
            end_time=end_time,
        )
    else:
        return await create(
            session,
            user_id=user_id,
            event_id=event_id,
            calendar_id=calendar_id,
            event_summary=event_summary,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            start_time=start_time,
            end_time=end_time,
        )


async def delete_travel_plan(session: AsyncSession, travel_plan_id: int) -> bool:
    """Delete a travel plan"""
    return await base.delete_by_id(session, travel_plans_table, travel_plan_id)


async def delete_by_event_id(
    session: AsyncSession,
    user_id: int,
    event_id: str,
) -> bool:
    """Delete a travel plan by event ID"""
    return await base.delete_by_fields(
        session,
        travel_plans_table,
        user_id=user_id,
        event_id=event_id,
    )

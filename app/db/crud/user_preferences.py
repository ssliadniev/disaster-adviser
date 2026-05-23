from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.disaster import DisasterCategory
from app.db.models import user_preferences_table
from app.db.crud import base


async def get_by_user_id(session: AsyncSession, user_id: int) -> dict | None:
    return await base.get_by_field(session, user_preferences_table, "user_id", user_id)


async def create_default_preferences(session: AsyncSession, user_id: int) -> dict:
    default_categories = DisasterCategory.get_all_values()

    return await base.create(
        session,
        user_preferences_table,
        user_id=user_id,
        notification_enabled=True,
        disaster_categories=default_categories,
        alert_threshold_distance_km=100.0,
        timezone="UTC",
    )


async def update_preferences(
    session: AsyncSession,
    user_id: int,
    **kwargs,
) -> dict | None:
    return await base.update_by_fields(
        session,
        user_preferences_table,
        filters={"user_id": user_id},
        values=kwargs,
    )


async def get_or_create_preferences(session: AsyncSession, user_id: int) -> dict:
    preferences = await get_by_user_id(session, user_id)
    if not preferences:
        preferences = await create_default_preferences(session, user_id)
    return preferences

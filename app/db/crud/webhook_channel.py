from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import webhook_channels_table
from app.db.utils import rows_to_list
from app.db.crud import base


async def create_channel(
    session: AsyncSession,
    *,
    channel_id: str,
    user_id: int,
    calendar_id: str,
    webhook_url: str,
    resource_id: str | None = None,
    expiration: int | None = None,
) -> dict:
    """Create a new webhook channel"""
    return await base.create(
        session,
        webhook_channels_table,
        channel_id=channel_id,
        user_id=user_id,
        calendar_id=calendar_id,
        webhook_url=webhook_url,
        resource_id=resource_id,
        expiration=expiration,
        is_active=True,
    )


async def get_by_channel_id(session: AsyncSession, channel_id: str) -> dict | None:
    """Get webhook channel by channel_id"""
    return await base.get_by_field(session, webhook_channels_table, "channel_id", channel_id)


async def get_active_by_user(session: AsyncSession, user_id: int) -> list[dict]:
    """Get all active webhook channels for a user"""
    return await base.get_all(
        session,
        webhook_channels_table,
        user_id=user_id,
        is_active=True,
    )


async def deactivate_channel(
    session: AsyncSession,
    channel_id: str,
) -> dict | None:
    return await base.update_by_fields(
        session,
        webhook_channels_table,
        filters={"channel_id": channel_id},
        values={"is_active": False, "stopped_at": datetime.utcnow()},
    )


async def delete_channel(session: AsyncSession, channel_id: str) -> bool:
    return await base.delete_by_fields(session, webhook_channels_table, channel_id=channel_id)


async def get_expired_channels(session: AsyncSession) -> list[dict]:
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    stmt = select(webhook_channels_table).where(
        webhook_channels_table.c.is_active == True,
        webhook_channels_table.c.expiration < now_ms,
    )
    result = await session.execute(stmt)
    return rows_to_list(result)

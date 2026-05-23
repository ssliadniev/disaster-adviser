from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models import oauth_accounts_table
from app.db.utils import row_to_dict
from app.db.crud import base


async def get_by_user_and_provider(
    session: AsyncSession,
    user_id: int,
    provider: str,
) -> dict | None:
    """Get OAuth account by user_id and provider"""
    return await base.get_by_fields(
        session,
        oauth_accounts_table,
        user_id=user_id,
        provider=provider,
    )


async def get_by_provider_user_id(
    session: AsyncSession,
    provider: str,
    provider_user_id: str,
) -> dict | None:
    """Get OAuth account by provider and provider_user_id"""
    return await base.get_by_fields(
        session,
        oauth_accounts_table,
        provider=provider,
        provider_user_id=provider_user_id,
    )


async def create_or_update_oauth_account(
    session: AsyncSession,
    *,
    user_id: int,
    provider: str,
    provider_user_id: str,
    access_token: str | None = None,
) -> dict:
    """Create or update OAuth account (upsert)"""
    stmt = pg_insert(oauth_accounts_table).values(
        user_id=user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        access_token=access_token,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_oauth_provider_user",
        set_=dict(
            access_token=access_token,
            user_id=user_id,
        ),
    ).returning(oauth_accounts_table)

    result = await session.execute(stmt)
    await session.commit()
    return row_to_dict(result)

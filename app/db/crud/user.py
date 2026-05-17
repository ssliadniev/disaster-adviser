from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import users_table
from app.db.crud import base


async def get_by_id(session: AsyncSession, user_id: int) -> dict | None:
    """Get user by ID"""
    return await base.get_by_id(session, users_table, user_id)


async def get_by_email(session: AsyncSession, email: str) -> dict | None:
    """Get user by email"""
    return await base.get_by_field(session, users_table, "email", email)


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    hashed_password: str | None = None,
) -> dict:
    """Create a new user"""
    return await base.create(
        session,
        users_table,
        email=email,
        hashed_password=hashed_password,
    )


async def update_user(
    session: AsyncSession,
    user_id: int,
    **kwargs,
) -> dict | None:
    """Update user fields"""
    return await base.update_by_id(session, users_table, user_id, **kwargs)


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    """Delete a user"""
    return await base.delete_by_id(session, users_table, user_id)

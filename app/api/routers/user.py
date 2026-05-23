from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.contracts.user import TokenData, PreferencesUpdate, PreferencesResponse
from app.db.session import get_db
from app.db.crud import user as user_crud
from app.db.crud import user_preferences as prefs_crud
from app.modules.user.error_mapping import user_error_mapper
from app.modules.user.exceptions import UserNotFoundError
from app.modules.user.preferences import apply_preference_updates

router = APIRouter(prefix="/api/v1/users/me/preferences", tags=["User Preferences"])


@router.get("", response_model=PreferencesResponse, summary="Get User Preferences")
async def get_preferences(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await user_crud.get_by_email(db, current_user.email)
        if not user:
            raise UserNotFoundError(f"User not found: {current_user.email}")

        prefs = await prefs_crud.get_or_create_preferences(db, user["id"])
        return prefs
    except Exception as e:
        raise user_error_mapper(e)


@router.patch("", response_model=PreferencesResponse)
async def update_preferences(
    updates: PreferencesUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user preferences."""
    try:
        user = await user_crud.get_by_email(db, current_user.email)
        if not user:
            raise UserNotFoundError(f"User not found: {current_user.email}")

        update_data = updates.model_dump(exclude_unset=True)

        prefs = (
            await apply_preference_updates(db, user["id"], update_data)
            if update_data
            else await prefs_crud.get_or_create_preferences(db, user["id"])
        )

        await db.commit()
        return prefs

    except Exception as e:
        await db.rollback()
        raise user_error_mapper(e)

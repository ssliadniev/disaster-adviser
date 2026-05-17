from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud import user_preferences as prefs_crud
from app.modules.user.exceptions import PreferencesNotFoundError, InvalidPreferencesError
from app.utils.functional import Ok, Err, Result
from app.utils.validators import validate_preferences


def _extract_validated(result: Result) -> dict:
    match result:
        case Ok(validated):
            return validated
        case Err(error):
            raise InvalidPreferencesError(error)


def _validate_prefs_exist(prefs: dict | None, user_id: int) -> dict:
    if not prefs:
        raise PreferencesNotFoundError(f"Preferences not found for user_id: {user_id}")
    return prefs


async def _update_preferences(db: AsyncSession, user_id: int, validated: dict) -> dict | None:
    return await prefs_crud.update_preferences(db, user_id, **validated)


async def apply_preference_updates(
    db: AsyncSession,
    user_id: int,
    update_data: dict
) -> dict:
    validation_result = validate_preferences(update_data)
    validated = _extract_validated(validation_result)

    prefs = await _update_preferences(db, user_id, validated)
    return _validate_prefs_exist(prefs, user_id)

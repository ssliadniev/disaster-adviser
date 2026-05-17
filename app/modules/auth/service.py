from typing import Callable
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.crud import user as user_crud
from app.db.crud import user_preferences as prefs_crud
from app.modules.auth.exceptions import InvalidCredentialsError, EmailAlreadyExistsError
from app.utils.functional import compose


def _verify_user_exists(user: dict | None) -> dict:
    if not user:
        raise InvalidCredentialsError("Incorrect email or password")
    return user


def _verify_has_password(user: dict) -> dict:
    if not user.get("hashed_password"):
        raise InvalidCredentialsError("Incorrect email or password")
    return user


def _verify_password_matches(password: str) -> Callable[[dict], dict]:
    def verify(user: dict) -> dict:
        if not verify_password(password, user["hashed_password"]):
            raise InvalidCredentialsError("Incorrect email or password")
        return user
    return verify


def _create_token_response(user: dict) -> dict:
    access_token = create_access_token(data={"sub": user["email"], "user_id": user["id"]})
    return {"access_token": access_token, "token_type": "bearer"}


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> dict:
    user = await user_crud.get_by_email(db, email)

    validate_and_create_token = compose(
        _verify_user_exists,
        _verify_has_password,
        _verify_password_matches(password),
        _create_token_response,
    )

    return validate_and_create_token(user)


def _validate_email_available(existing: dict | None) -> None:
    if existing:
        raise EmailAlreadyExistsError("Email already registered")


def _hash_password(password: str) -> str:
    return get_password_hash(password)


async def _create_user(db: AsyncSession, email: str, hashed_password: str) -> dict:
    return await user_crud.create_user(db, email=email, hashed_password=hashed_password)


async def _initialize_preferences(db: AsyncSession, user_id: int) -> None:
    await prefs_crud.create_default_preferences(db, user_id)


async def register_new_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> dict:

    existing_email = await user_crud.get_by_email(db, email)
    _validate_email_available(existing_email)

    hashed_password = _hash_password(password)
    new_user = await _create_user(db, email, hashed_password)
    await _initialize_preferences(db, new_user["id"])

    return new_user
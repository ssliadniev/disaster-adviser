from datetime import datetime, timedelta, timezone
from typing import TypeAlias
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.core.config import settings
from app.infrastructure.auth_client import (
    OAUTH_SCOPES,
    CALENDAR_SCOPES,
    GOOGLE_AUTH_URL,
    exchange_code_for_tokens,
    get_user_info,
)
from app.db.crud import user as user_crud
from app.db.crud import oauth_token as oauth_crud
from app.db.crud import user_preferences as prefs_crud
from app.utils.functional import compose

TokenResponse: TypeAlias = dict[str, object]
TokenData: TypeAlias = dict[str, object]
UserInfo: TypeAlias = dict[str, object]


def _merge_scopes(scopes: list[str] | None) -> list[str]:
    return OAUTH_SCOPES + (scopes if scopes is not None else CALENDAR_SCOPES)


def _build_oauth_params(state: str, scopes: list[str]) -> dict:
    param_configs = [
        ("client_id", settings.GOOGLE_CLIENT_ID or ""),
        ("redirect_uri", settings.GOOGLE_REDIRECT_URI or ""),
        ("response_type", "code"),
        ("scope", " ".join(scopes)),
        ("state", state),
        ("access_type", "offline"),
        ("prompt", "consent"),
    ]

    return {
        key: value
        for key, value in param_configs
        if value not in (None, "")
    }


def _format_url(params: dict) -> str:
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def get_authorization_url(state: str, scopes: list[str] | None = None) -> str:
    def build_params(merged_scopes: list[str]) -> dict:
        return _build_oauth_params(state, merged_scopes)

    return compose(
        _merge_scopes,
        build_params,
        _format_url,
    )(scopes)


def build_auth_url(state: str, scopes: list[str] | None = None) -> str:
    return get_authorization_url(state, scopes)


def calculate_expiry(expires_in: int, now: datetime) -> datetime:
    return now + timedelta(seconds=expires_in)


def _get_access_token(response: TokenResponse) -> str | None:
    return response.get("access_token")


def _get_refresh_token(response: TokenResponse) -> str | None:
    return response.get("refresh_token")


def _get_expires_in(response: TokenResponse) -> int:
    return int(response.get("expires_in", 3600))


def _get_scope(response: TokenResponse) -> str | None:
    return response.get("scope")


def extract_token_data(token_response: TokenResponse, now: datetime) -> TokenData:
    return {
        "access_token": _get_access_token(token_response),
        "refresh_token": _get_refresh_token(token_response),
        "expires_at": calculate_expiry(_get_expires_in(token_response), now),
        "scope": _get_scope(token_response),
    }


def build_registration_response(user: dict, message: str) -> dict:
    return {
        "access_token": create_access_token(data={"sub": user["email"], "user_id": user["id"]}),
        "token_type": "bearer",
        "message": message,
        "user": {
            "id": user["id"],
            "email": user["email"],
        },
    }


def build_connection_response(token_data: TokenData, scope: str) -> dict:
    return {
        "access_token": token_data["access_token"],
        "token_type": "bearer",
        "message": "Successfully connected to Google Calendar",
        "scope": scope,
    }


async def _exchange_and_extract(code: str) -> TokenData:
    token_response = await exchange_code_for_tokens(code)
    return extract_token_data(token_response, now=datetime.now(timezone.utc))


async def _find_user_by_oauth(db: AsyncSession, google_id: str) -> tuple[dict, str] | None:
    oauth_account = await oauth_crud.get_by_provider_user_id(db, "google", google_id)
    if not oauth_account:
        return None

    user = await user_crud.get_by_id(db, oauth_account["user_id"])
    return (user, "Account already exists. Logged in successfully.") if user else None


async def _find_user_by_email(db: AsyncSession, email: str) -> tuple[dict, str] | None:
    user = await user_crud.get_by_email(db, email)
    return (user, "Linked Google account to existing user") if user else None


async def _create_new_user(db: AsyncSession, email: str) -> tuple[dict, str]:
    new_user = await user_crud.create_user(db, email=email, hashed_password=None)
    await prefs_crud.create_default_preferences(db, new_user["id"])
    return new_user, "Account created successfully via Google"


async def _resolve_or_create_user(db: AsyncSession, google_id: str, email: str) -> tuple[dict, str]:
    return (
        await _find_user_by_oauth(db, google_id)
        or await _find_user_by_email(db, email)
        or await _create_new_user(db, email)
    )


async def _store_token(db: AsyncSession, user_id: int, provider_user_id: str, token_data: TokenData) -> None:
    await oauth_crud.create_or_update_oauth_account(
        db,
        user_id=user_id,
        provider="google",
        provider_user_id=provider_user_id,
        access_token=token_data["access_token"],
    )


def _validate_user_info(google_id: str, email: str) -> None:
    if not google_id or not email:
        raise ValueError("Email and Google ID are required for registration")


def _extract_google_credentials(user_info: UserInfo) -> tuple[str, str]:
    google_id = str(user_info.get("id", ""))
    email = str(user_info.get("email", ""))
    _validate_user_info(google_id, email)
    return google_id, email


def _build_registration_result(user: dict, message: str, token_data: TokenData, scope: str | None) -> dict:
    return {"user": user, "message": message, "token_data": token_data, "scope": scope}


async def process_oauth_registration(code: str, scope: str | None, db: AsyncSession) -> dict:
    token_data = await _exchange_and_extract(code)
    user_info: UserInfo = await get_user_info(token_data["access_token"])

    google_id, email = _extract_google_credentials(user_info)
    user, message = await _resolve_or_create_user(db, google_id, email)
    await _store_token(db, user["id"], google_id, token_data)

    return _build_registration_result(user, message, token_data, scope)


def _validate_google_id(google_id: str) -> str:
    if not google_id:
        raise ValueError("Google ID is required")
    return google_id


def _extract_google_id(user_info: UserInfo) -> str:
    google_id = str(user_info.get("id", ""))
    return _validate_google_id(google_id)


def _build_connection_result(token_data: TokenData, scope: str | None) -> dict:
    return {"token_data": token_data, "scope": scope}


async def process_oauth_connection(code: str, scope: str | None, user_id: int, db: AsyncSession) -> dict:
    token_data = await _exchange_and_extract(code)
    user_info: UserInfo = await get_user_info(token_data["access_token"])

    google_id = _extract_google_id(user_info)
    await _store_token(db, user_id, google_id, token_data)

    return _build_connection_result(token_data, scope)


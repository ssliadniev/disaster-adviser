from typing import TypeAlias
import httpx

from app.core.config import settings

TokenResponse: TypeAlias = dict[str, object]
UserInfo: TypeAlias = dict[str, object]

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

OAUTH_SCOPES = ["openid", "email", "profile"]


def _build_token_request_data(code: str) -> dict:
    token_configs = [
        ("client_id", settings.GOOGLE_CLIENT_ID),
        ("client_secret", settings.GOOGLE_CLIENT_SECRET),
        ("code", code),
        ("grant_type", "authorization_code"),
        ("redirect_uri", settings.GOOGLE_REDIRECT_URI),
    ]

    return {key: value for key, value in token_configs if value is not None}


async def _post_token_request(data: dict) -> TokenResponse:
    async with httpx.AsyncClient() as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()


async def exchange_code_for_tokens(code: str) -> TokenResponse:
    data = _build_token_request_data(code)
    return await _post_token_request(data)


def _build_auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


async def _fetch_user_info(access_token: str) -> UserInfo:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers=_build_auth_headers(access_token),
        )
        response.raise_for_status()
        return response.json()


async def get_user_info(access_token: str) -> UserInfo:
    return await _fetch_user_info(access_token)

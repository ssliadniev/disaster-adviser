from __future__ import annotations

import logging
import uuid
from functools import partial

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.calendar import NotificationResult, ResourceState
from app.db.crud import user as user_crud
from app.db.crud import oauth_token as oauth_crud
from app.db.crud import webhook_channel as webhook_crud
from app.db.session import AsyncSessionLocal
from app.infrastructure.calendar_client import (
    register_calendar_webhook as google_register_webhook,
)
from app.modules.travel_planner.exceptions import (
    WebhookRegistrationError,
    WebhookNotFoundError,
    WebhookPermissionError,
)
from app.modules.travel_planner.events import (
    handle_calendar_sync,
    handle_calendar_change,
    handle_calendar_deletion,
)
from app.utils.functional import pipe

logger = logging.getLogger(__name__)


def _make_channel_id() -> str:
    return str(uuid.uuid4())


def _assert_https(url: str) -> str:
    if not url.startswith("https://"):
        raise ValueError("Webhook URL must use HTTPS")
    return url


def _user_email(user: dict | None) -> str:
    return user.get("email", "unknown") if user else "unknown"


def _build_webhook_channel(
    channel_id: str, webhook_url: str, watch_response: dict
) -> dict:
    return {
        "channel_id": channel_id,
        "resource_id": watch_response.get("resourceId"),
        "expiration": watch_response.get("expiration"),
        "webhook_url": webhook_url,
        "message": "Webhook registered successfully",
        "note": "Google Calendar will send notifications to this webhook when events change",
    }


def _make_acknowledged(
    type_: str, message: str, user: str | None = None
) -> NotificationResult:
    return NotificationResult(
        status="acknowledged", type=type_, message=message, user=user, event=None
    )


async def _get_user_or_raise(session: AsyncSession, email: str) -> dict:
    user = await user_crud.get_by_email(session, email)
    if not user:
        raise WebhookNotFoundError("User not found")
    return user


async def _get_google_oauth_or_raise(session: AsyncSession, user_id: int) -> dict:
    oauth = await oauth_crud.get_by_user_and_provider(session, user_id, "google")
    if not oauth:
        raise WebhookPermissionError(
            "Google Calendar not connected. Please authenticate first."
        )
    if not oauth.get("access_token"):
        raise WebhookPermissionError("No valid access token. Please re-authenticate.")
    return oauth


async def register_webhook(
    session: AsyncSession,
    user_email: str,
    webhook_url: str,
    calendar_id: str = "primary",
) -> dict:
    pipe(webhook_url, _assert_https)

    user = await _get_user_or_raise(session, user_email)
    oauth = await _get_google_oauth_or_raise(session, user["id"])
    channel_id = _make_channel_id()

    try:
        watch_response = await google_register_webhook(
            access_token=oauth["access_token"],
            channel_id=channel_id,
            webhook_url=webhook_url,
            calendar_id=calendar_id,
        )
    except httpx.HTTPStatusError as exc:
        raise WebhookRegistrationError(
            f"Failed to register webhook with Google: {exc.response.text}"
        ) from exc

    expiration_str = watch_response.get("expiration")
    expiration_int = int(expiration_str) if expiration_str else None

    await webhook_crud.create_channel(
        session,
        channel_id=channel_id,
        user_id=user["id"],
        calendar_id=calendar_id,
        webhook_url=webhook_url,
        resource_id=watch_response.get("resourceId"),
        expiration=expiration_int,
    )

    return pipe(
        watch_response, partial(_build_webhook_channel, channel_id, webhook_url)
    )


async def process_webhook_notification(
    channel_id: str, resource_state: ResourceState
) -> NotificationResult:
    logger.info(
        f"Processing webhook notification: channel_id={channel_id}, state={resource_state}"
    )

    async with AsyncSessionLocal() as session:
        channel = await webhook_crud.get_by_channel_id(session, channel_id)

        if not channel or not channel.get("is_active"):
            logger.info(
                f"Webhook channel not found or inactive: channel_id={channel_id}"
            )
            return _make_acknowledged(
                resource_state, "Webhook received (channel not found or inactive)"
            )

        user = await user_crud.get_by_id(session, channel["user_id"])
        user_email = pipe(user, _user_email)

        logger.info(f"Found webhook user: email={user_email}, state={resource_state}")

        match resource_state:
            case "sync":
                logger.info(f"Handling webhook SYNC for user={user_email}")
                return await handle_calendar_sync(user_email)
            case "exists":
                logger.info(f"Handling webhook CALENDAR CHANGE for user={user_email}")
                result = await handle_calendar_change(
                    session, channel["user_id"], user_email
                )
                await session.commit()
                return result
            case "not_exists":
                logger.info(f"Handling webhook DELETION for user={user_email}")
                return await handle_calendar_deletion(user_email)
            case _:
                logger.warning(
                    f"Unknown webhook state '{resource_state}', treating as SYNC"
                )
                return await handle_calendar_sync(user_email)

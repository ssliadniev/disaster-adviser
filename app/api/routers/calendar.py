import logging
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import RedirectResponse

from app.contracts.calendar import WebhookRegisterResponse, WebhookEventResponse
from app.contracts.travel import TravelPlanListResponse
from app.core.config import settings
from app.core.dependencies import (
    get_current_user,
    OAuthStateManager,
    get_oauth_state_manager,
)
from app.contracts.user import TokenData
from app.db.crud import travel_plan as travel_plan_crud
from app.db.session import get_db
from app.modules.auth.google_oauth_service import build_auth_url
from app.modules.travel_planner.webhook import (
    register_webhook as register_webhook_service,
    process_webhook_notification,
)
from app.modules.travel_planner.events import _sync_and_cleanup_deleted_events
from app.modules.travel_planner.error_mapping import webhook_error_mapper
from app.db.crud import user as user_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Calendar"])


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _serialize_travel_plan(row: dict) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "event_id": row["event_id"],
        "calendar_id": row["calendar_id"],
        "title": row["event_summary"],
        "location_name": row.get("location_name"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "start_at": row["start_time"],
        "end_at": row["end_time"],
    }


@router.get(
    "/calendar/connect",
    summary="Connect Google Calendar",
    description="Initialize Google Calendar connection for the authenticated user",
)
async def connect_calendar(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    state_manager: OAuthStateManager = Depends(get_oauth_state_manager),
) -> RedirectResponse:
    """Connect Google Calendar with full calendar access.

    Redirects user to Google OAuth consent screen with calendar permissions.
    After authorization, user will be redirected back to the callback endpoint.
    """
    try:
        user = await user_crud.get_by_email(db, current_user.email)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        state = state_manager.register(action="connect", user_id=user["id"])

        auth_url = build_auth_url(state)

        return RedirectResponse(url=auth_url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate calendar connection: {str(e)}",
        )


@router.get(
    "/calendar/events",
    response_model=TravelPlanListResponse,
    summary="Get Calendar Events For Date",
    description="Return stored travel plans that overlap the specified UTC date for the authenticated user.",
)
async def get_calendar_events_for_date(
    query_date: date = Query(..., alias="date"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[dict]]:
    try:
        user = await user_crud.get_by_email(db, current_user.email)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        start, end = _day_bounds(query_date)
        plans = await travel_plan_crud.get_by_user_overlapping_timerange(
            db,
            user["id"],
            start,
            end,
        )
        return {"travel_plans": [_serialize_travel_plan(plan) for plan in plans]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query calendar events: {str(e)}",
        )


@router.post(
    "/webhook/register",
    response_model=WebhookRegisterResponse,
    summary="Register Calendar Webhook",
    description="Register a webhook for the user's primary Google Calendar using the configured webhook URL. Automatically deactivates old webhooks for the same user.",
)
async def register_webhook(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a webhook for calendar change notifications.

    Uses the GOOGLE_WEBHOOK_URL from configuration and registers for the user's primary calendar.
    Automatically deactivates any existing active webhooks for this user to prevent duplicates.
    """
    if not settings.GOOGLE_WEBHOOK_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_WEBHOOK_URL is not configured in environment variables",
        )

    try:
        user = await user_crud.get_by_email(db, current_user.email)
        if user:
            from app.db.crud import webhook_channel as webhook_crud

            active_webhooks = await webhook_crud.get_active_by_user(db, user["id"])
            for webhook in active_webhooks:
                await webhook_crud.deactivate_channel(db, webhook["channel_id"])

            if active_webhooks:
                logger.info(
                    f"Deactivated {len(active_webhooks)} old webhook(s) for user {user['id']}"
                )

        result = await register_webhook_service(
            db,
            user_email=current_user.email,
            webhook_url=settings.GOOGLE_WEBHOOK_URL,
            calendar_id="primary",
        )

        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise webhook_error_mapper(e)


@router.post(
    "/webhook/events",
    response_model=WebhookEventResponse,
    summary="Webhook Event Handler (Called by Google)",
)
async def webhook_events(
    x_goog_channel_id: str | None = Header(None),
    x_goog_resource_id: str | None = Header(None),
    x_goog_resource_state: str | None = Header(None),
    x_goog_message_number: str | None = Header(None),
) -> WebhookEventResponse:
    """Handle incoming webhook notifications from Google Calendar.

    This endpoint is called by Google when calendar events change.
    """
    logger.info(
        f"Webhook received: channel_id={x_goog_channel_id}, state={x_goog_resource_state}, resource_id={x_goog_resource_id}, msg_num={x_goog_message_number}"
    )

    try:
        result = await process_webhook_notification(
            channel_id=x_goog_channel_id,
            resource_state=x_goog_resource_state,
        )

        logger.info(
            f"Webhook processed: status={result['status']}, type={result['type']}, message={result['message']}"
        )
        return WebhookEventResponse(**result)
    except Exception as e:
        logger.error(f"Webhook error: {type(e).__name__}: {str(e)}")
        raise webhook_error_mapper(e)


@router.post(
    "/calendar/sync",
    summary="Sync Calendar Events",
    description="Sync calendar events with database and clean up deleted events",
)
async def sync_calendar_events(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually sync calendar events and remove deleted events from database."""
    try:
        user = await user_crud.get_by_email(db, current_user.email)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        deleted_count = await _sync_and_cleanup_deleted_events(db, user["id"])
        await db.commit()

        return {
            "message": "Calendar sync completed successfully",
            "deleted_events": deleted_count,
            "user_email": current_user.email,
        }

    except Exception as e:
        await db.rollback()
        raise webhook_error_mapper(e)

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.calendar import EventDetails, NotificationResult
from app.db.crud import oauth_token as oauth_crud
from app.db.crud import travel_plan as travel_plan_crud
from app.infrastructure.calendar_client import get_events
from app.infrastructure.geocoding import geocode_location

logger = logging.getLogger(__name__)


def _time_window(minutes_back: int) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(minutes=minutes_back), now + timedelta(days=30)


def _extract_event_details(event: dict) -> EventDetails:
    return EventDetails(
        id=event.get("id", ""),
        summary=event.get("summary", "Untitled Event"),
        location=event.get("location"),
        start=event.get("start", {}).get("dateTime"),
        end=event.get("end", {}).get("dateTime"),
        description=event.get("description"),
    )


async def _fetch_recent_events(access_token: str, minutes_back: int = 5) -> list[dict]:
    time_min, time_max = _time_window(minutes_back)
    logger.info(
        f"Fetching recent events: minutes_back={minutes_back}, time_min={time_min.isoformat()}, time_max={time_max.isoformat()}"
    )

    events = await get_events(
        access_token=access_token,
        time_min=time_min,
        time_max=time_max,
        max_results=10,
        single_events=True,
        order_by="startTime",
    )

    logger.info(f"Fetched events successfully: event_count={len(events)}")
    return events


def _validate_oauth(oauth: dict | None) -> dict:
    if not (oauth and oauth.get("access_token")):
        raise ValueError("No OAuth token found")
    return oauth


def _validate_events(events: list[dict]) -> dict:
    if not events:
        raise ValueError("No recent events found")
    return events[0]


def _create_error_event(exc: Exception) -> EventDetails:
    return EventDetails(error=str(exc))


async def _fetch_and_extract_recent_event(
    session: AsyncSession, user_id: int
) -> EventDetails | None:
    try:
        logger.info(f"Fetching and extracting recent event: user_id={user_id}")

        oauth = await oauth_crud.get_by_user_and_provider(session, user_id, "google")
        validated_oauth = _validate_oauth(oauth)

        events = await _fetch_recent_events(
            validated_oauth["access_token"], minutes_back=5
        )
        first_event = _validate_events(events)

        event_details = _extract_event_details(first_event)
        logger.info(
            f"Extracted event details: user_id={user_id}, event_id={event_details.get('id')}, event_summary={event_details.get('summary')}"
        )
        return event_details

    except ValueError as exc:
        logger.info(f"{str(exc)}: user_id={user_id}")
        return None
    except Exception as exc:
        logger.error(f"Error fetching event details: user_id={user_id}, error={exc}")
        return _create_error_event(exc)


def _create_sync_result(user_email: str) -> NotificationResult:
    return NotificationResult(
        status="acknowledged",
        type="sync",
        message="Webhook sync successful",
        user=user_email,
        event=None,
    )


async def handle_calendar_sync(user_email: str) -> NotificationResult:
    logger.info(f"Handling calendar sync webhook: user_email={user_email}")
    return _create_sync_result(user_email)


def _is_valid_event(event: EventDetails | None) -> bool:
    return bool(event and not event.get("error"))


def _has_required_fields(event: EventDetails) -> bool:
    return bool(event.get("id") and event.get("start") and event.get("end"))


def _parse_datetime(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


async def _geocode_if_location(
    event_id: str, location_name: str | None
) -> tuple[float | None, float | None]:
    if not location_name:
        return None, None

    logger.info(f"Geocoding location: event_id={event_id}, location={location_name}")
    coordinates = await geocode_location(location_name)

    if coordinates:
        logger.info(
            f"Geocoded location successfully: event_id={event_id}, latitude={coordinates['latitude']}, longitude={coordinates['longitude']}"
        )
        return coordinates["latitude"], coordinates["longitude"]

    logger.info(
        f"Failed to geocode location: event_id={event_id}, location={location_name}"
    )
    return None, None


async def _save_event_to_travel_plan(
    session: AsyncSession, user_id: int, event: EventDetails
) -> dict | None:
    if not _is_valid_event(event):
        return None

    if not _has_required_fields(event):
        logger.info(
            f"Skipping event save - missing required fields: event_id={event.get('id')}"
        )
        return None

    event_id = event.get("id", "")
    start_time = _parse_datetime(event.get("start"))
    end_time = _parse_datetime(event.get("end"))

    if not start_time or not end_time:
        logger.info(f"Skipping event save - invalid datetime: event_id={event_id}")
        return None

    try:
        location_name = event.get("location")
        latitude, longitude = await _geocode_if_location(event_id, location_name)

        travel_plan = await travel_plan_crud.upsert_travel_plan(
            session,
            user_id=user_id,
            event_id=event_id,
            calendar_id="primary",
            event_summary=event.get("summary", "Untitled Event"),
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            start_time=start_time,
            end_time=end_time,
        )

        logger.info(
            f"Saved event to travel_plans: user_id={user_id}, event_id={event_id}, travel_plan_id={travel_plan.get('id')}, has_coordinates={bool(latitude and longitude)}"
        )
        from app.modules.notification_service.integration import (
            process_travel_plan_notifications,
        )

        await process_travel_plan_notifications(session, travel_plan)
        return travel_plan

    except Exception as exc:
        logger.error(
            f"Error saving event to travel_plans: user_id={user_id}, event_id={event_id}, error={exc}"
        )
        return None


def _create_change_result(
    user_email: str, event: EventDetails | None
) -> NotificationResult:
    return NotificationResult(
        status="processed",
        type="event_change",
        message="Calendar event change detected",
        user=user_email,
        event=event,
    )


async def handle_calendar_change(
    session: AsyncSession, user_id: int, user_email: str
) -> NotificationResult:
    logger.info(
        f"Handling calendar change webhook: user_id={user_id}, user_email={user_email}"
    )

    event = await _fetch_and_extract_recent_event(session, user_id)

    if event:
        logger.info(
            f"Calendar change processed with event: user_id={user_id}, event_id={event.get('id')}"
        )
        await _save_event_to_travel_plan(session, user_id, event)
    else:
        logger.info(f"Calendar change processed but no event found: user_id={user_id}")

    deleted_count = await _sync_and_cleanup_deleted_events(session, user_id)
    if deleted_count > 0:
        logger.info(
            f"Deleted events during sync: user_id={user_id}, deleted_count={deleted_count}"
        )

    return _create_change_result(user_email, event)


def _get_sync_time_window() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=30), now + timedelta(days=90)


def _extract_event_ids(events: list[dict]) -> set[str]:
    return {event.get("id") for event in events if event.get("id")}


def _should_delete(
    db_event: dict, google_event_ids: set[str]
) -> tuple[bool, str | None]:
    event_id = db_event.get("event_id")
    return (event_id is not None and event_id not in google_event_ids, event_id)


async def _fetch_google_events(
    oauth: dict, time_min: datetime, time_max: datetime
) -> list[dict]:
    return await get_events(
        access_token=oauth["access_token"],
        time_min=time_min,
        time_max=time_max,
        max_results=250,
        single_events=True,
        order_by="startTime",
    )


async def _delete_stale_events(
    session: AsyncSession,
    user_id: int,
    db_events: list[dict],
    google_event_ids: set[str],
) -> int:
    deleted_count = 0
    for db_event in db_events:
        should_delete, event_id = _should_delete(db_event, google_event_ids)
        if should_delete and event_id:
            await travel_plan_crud.delete_by_event_id(session, user_id, event_id)
            deleted_count += 1
            logger.info(
                f"Deleted event from database (no longer in Google Calendar): user_id={user_id}, event_id={event_id}"
            )

    return deleted_count


async def _sync_and_cleanup_deleted_events(session: AsyncSession, user_id: int) -> int:
    try:
        oauth = await oauth_crud.get_by_user_and_provider(session, user_id, "google")
        if not (oauth and oauth.get("access_token")):
            logger.info(f"Cannot sync - no OAuth token: user_id={user_id}")
            return 0

        time_min, time_max = _get_sync_time_window()
        google_events = await _fetch_google_events(oauth, time_min, time_max)
        google_event_ids = _extract_event_ids(google_events)

        logger.info(
            f"Fetched events from Google for sync: user_id={user_id}, count={len(google_event_ids)}"
        )

        db_events = await travel_plan_crud.get_by_user_and_timerange(
            session, user_id, time_min, time_max
        )
        deleted_count = await _delete_stale_events(
            session, user_id, db_events, google_event_ids
        )

        if deleted_count > 0:
            logger.info(
                f"Cleanup complete: user_id={user_id}, deleted_count={deleted_count}"
            )

        return deleted_count

    except Exception as exc:
        logger.error(
            f"Error syncing and cleaning up deleted events: user_id={user_id}, error={exc}"
        )
        return 0


def _create_deletion_result(user_email: str) -> NotificationResult:
    return NotificationResult(
        status="processed",
        type="event_deleted",
        message="Calendar event deleted",
        user=user_email,
        event=None,
    )


async def handle_calendar_deletion(user_email: str) -> NotificationResult:
    logger.info(f"Handling calendar deletion webhook: user_email={user_email}")
    return _create_deletion_result(user_email)

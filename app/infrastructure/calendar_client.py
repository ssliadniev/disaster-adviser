from typing import TypeAlias
from datetime import datetime, timezone, timedelta
import httpx

CalendarEvent: TypeAlias = dict[str, object]
CalendarList: TypeAlias = list[CalendarEvent]

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


def _build_calendar_url(endpoint: str) -> str:
    return f"{CALENDAR_API_BASE}/{endpoint}"


async def _make_calendar_request(
    access_token: str,
    endpoint: str,
    params: dict | None = None,
) -> dict:
    url = _build_calendar_url(endpoint)
    headers = _build_bearer_headers(access_token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json() if response.text else {}


def parse_google_datetime(dt_data: dict | None) -> datetime | None:
    if not dt_data:
        return None

    dt_str = dt_data.get("dateTime") or dt_data.get("date")
    if not dt_str:
        return None

    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _format_datetime_for_google(dt: datetime) -> str:
    utc_dt = (
        dt.replace(tzinfo=timezone.utc)
        if dt.tzinfo is None
        else dt.astimezone(timezone.utc)
    )
    return utc_dt.replace(tzinfo=None).isoformat() + "Z"


def _build_query_params(
    time_min: datetime | None = None,
    time_max: datetime | None = None,
    max_results: int | None = None,
    single_events: bool | None = None,
    order_by: str | None = None,
) -> dict:
    param_configs = [
        ("timeMin", time_min, _format_datetime_for_google),
        ("timeMax", time_max, _format_datetime_for_google),
        ("maxResults", max_results, None),
        ("singleEvents", single_events, None),
        ("orderBy", order_by, None),
    ]

    return {
        api_key: (transform(value) if transform else value)
        for api_key, value, transform in param_configs
        if value is not None
    }


async def get_events(
    access_token: str,
    calendar_id: str = "primary",
    time_min: datetime | None = None,
    time_max: datetime | None = None,
    max_results: int | None = None,
    single_events: bool | None = None,
    order_by: str | None = None,
) -> CalendarList:
    params = _build_query_params(
        time_min=time_min,
        time_max=time_max,
        max_results=max_results,
        single_events=single_events,
        order_by=order_by,
    )

    response = await _make_calendar_request(
        access_token,
        f"calendars/{calendar_id}/events",
        params=params,
    )
    return response.get("items", [])


def _calculate_expiration_ms(hours: int) -> int:
    expiration_time = datetime.now(timezone.utc) + timedelta(hours=hours)
    return int(expiration_time.timestamp() * 1000)


def _build_webhook_payload(
    channel_id: str, webhook_url: str, expiration_ms: int
) -> dict:
    return {
        "id": channel_id,
        "type": "web_hook",
        "address": webhook_url,
        "expiration": expiration_ms,
    }


def _build_watch_url(calendar_id: str) -> str:
    return f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/watch"


def _build_bearer_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


async def _post_webhook_registration(
    url: str,
    access_token: str,
    payload: dict,
) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=_build_bearer_headers(access_token),
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


async def register_calendar_webhook(
    access_token: str,
    channel_id: str,
    webhook_url: str,
    calendar_id: str = "primary",
    expiration_hours: int = 168,
) -> dict:
    expiration_ms = _calculate_expiration_ms(expiration_hours)
    payload = _build_webhook_payload(channel_id, webhook_url, expiration_ms)
    url = _build_watch_url(calendar_id)

    return await _post_webhook_registration(url, access_token, payload)

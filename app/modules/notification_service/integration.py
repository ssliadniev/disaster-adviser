from __future__ import annotations

from datetime import UTC, datetime
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.disaster import DisasterCategory
from app.contracts.disaster import StandardDisasterEvent
from app.core.config import settings
from app.contracts.travel import TravelPlan
from app.contracts.user import UserPreferences
from app.db.crud import disaster_event as disaster_event_crud
from app.db.crud import notification as notification_crud
from app.db.crud import user as user_crud
from app.db.crud import user_preferences as user_preferences_crud
from app.db.models import travel_plans_table
from app.db.utils import rows_to_list
from app.modules.hotspot_tracker.integration import to_domain_disaster_row
from app.services.hotspot_analyzer import assess_hotspot
from app.services.notification_service import (
    make_hotspot_notification_decision,
    make_notification_decision,
)
from app.services.risk_analyzer import assess_risk


def _normalize_category(category: object) -> str:
    if hasattr(category, "value"):
        return str(category.value)
    return str(category)


def to_domain_disaster(raw_event) -> StandardDisasterEvent:
    return StandardDisasterEvent(
        id=raw_event.id,
        title=raw_event.title,
        category=DisasterCategory.from_string(_normalize_category(raw_event.category)),
        latitude=raw_event.latitude,
        longitude=raw_event.longitude,
        date=raw_event.date,
        source=raw_event.source.value if hasattr(raw_event.source, "value") else raw_event.source,
        closed=getattr(raw_event, "closed", None),
    )


def to_domain_travel_plan(raw_plan: dict) -> TravelPlan:
    return TravelPlan(
        id=str(raw_plan["id"]),
        user_id=str(raw_plan["user_id"]),
        title=raw_plan["event_summary"],
        start_at=raw_plan["start_time"],
        end_at=raw_plan["end_time"],
        city=raw_plan.get("location_name"),
        country=None,
        latitude=raw_plan.get("latitude"),
        longitude=raw_plan.get("longitude"),
    )


def to_domain_preferences(raw_preferences: dict) -> UserPreferences:
    return UserPreferences(
        user_id=str(raw_preferences["user_id"]),
        max_distance_km=float(raw_preferences["alert_threshold_distance_km"]),
        max_days_ahead=settings.RISK_MAX_DAYS_AHEAD,
        enabled_categories=tuple(raw_preferences["disaster_categories"]),
        notifications_enabled=bool(raw_preferences["notification_enabled"]),
    )


async def _load_active_events(session: AsyncSession) -> list[StandardDisasterEvent]:
    rows = await disaster_event_crud.get_active_events(session)
    return [to_domain_disaster_row(row) for row in rows]


async def _load_recent_events(session: AsyncSession) -> list[StandardDisasterEvent]:
    rows = await disaster_event_crud.get_recent_events(
        session,
        since=datetime.now(UTC) - timedelta(days=settings.HOTSPOT_LOOKBACK_DAYS),
    )
    return [to_domain_disaster_row(row) for row in rows]


async def _persist_notification(
    session: AsyncSession,
    *,
    user_row: dict,
    plan_row: dict,
    decision,
) -> None:
    stored, changed = await notification_crud.upsert_notification(
        session,
        user_id=user_row["id"],
        travel_plan_id=plan_row["id"],
        kind=decision.notification.kind.value,
        source_key=decision.notification.source_key,
        severity=decision.notification.severity.value,
        risk_score=decision.notification.risk_score,
        subject=decision.notification.subject,
        body=decision.notification.body,
        recipient_email=user_row["email"],
        disaster_event_id=decision.notification.disaster_event_id,
    )
    if not changed:
        return

    # Publishing to the notifications API is the primary delivery mechanism.
    await notification_crud.mark_published(session, stored["id"])


async def process_travel_plan_notifications(
    session: AsyncSession, plan_row: dict
) -> None:
    user_row = await user_crud.get_by_id(session, plan_row["user_id"])
    preferences_row = await user_preferences_crud.get_or_create_preferences(
        session, plan_row["user_id"]
    )
    if user_row is None or preferences_row is None:
        return

    domain_plan = to_domain_travel_plan(plan_row)
    domain_preferences = to_domain_preferences(preferences_row)
    domain_events = await _load_active_events(session)
    historical_events = await _load_recent_events(session)

    for event in domain_events:
        assessment = assess_risk(event, domain_plan, domain_preferences)
        if assessment is None:
            continue
        decision = make_notification_decision(
            assessment, domain_plan, event, domain_preferences
        )
        if decision is not None:
            await _persist_notification(
                session, user_row=user_row, plan_row=plan_row, decision=decision
            )

    hotspot = assess_hotspot(historical_events, domain_plan, datetime.now(UTC))
    if hotspot is not None:
        decision = make_hotspot_notification_decision(hotspot, domain_plan)
        await _persist_notification(
            session, user_row=user_row, plan_row=plan_row, decision=decision
        )


async def process_disaster_notifications(session: AsyncSession, raw_event) -> None:
    _ = to_domain_disaster(raw_event)
    result = await session.execute(select(travel_plans_table))
    all_plans = rows_to_list(result)
    for plan_row in all_plans:
        await process_travel_plan_notifications(session, plan_row)

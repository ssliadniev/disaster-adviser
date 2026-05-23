from __future__ import annotations

from app.contracts.disaster import StandardDisasterEvent
from app.contracts.hotspot import HotspotWarning
from app.contracts.notification import (
    AlertKind,
    Notification,
    NotificationDecision,
)
from app.contracts.risk import RiskAssessment
from app.contracts.travel import TravelPlan
from app.contracts.user import UserPreferences
from app.utils.functional import (
    Some,
)

NOTIFICATION_THRESHOLD = 0.6


def _category_label(category: object) -> str:
    raw = category.value if hasattr(category, "value") else category
    return str(raw).replace("_", " ")


def _build_direct_body(
    assessment: RiskAssessment, plan: TravelPlan, event: StandardDisasterEvent
) -> str:
    return (
        f"Travel alert for {plan.title}: {event.title} ({_category_label(event.category)}) is "
        f"{assessment.distance_km:.1f} km from your destination. "
        f"Risk score: {assessment.risk_score:.2f}."
    )


def _build_hotspot_body(warning: HotspotWarning, plan: TravelPlan) -> str:
    return (
        f"Hotspot warning for {plan.title}: {warning.location_name} has an elevated "
        f"regional disaster score of {warning.hotspot_score:.2f} over the last "
        f"{warning.lookback_days} days."
    )


def make_notification_decision(
    assessment: RiskAssessment,
    plan: TravelPlan,
    event: StandardDisasterEvent,
    prefs: UserPreferences,
) -> NotificationDecision | None:
    decision = (
        Some((assessment, plan, event, prefs))
        .filter(lambda args: args[3].notifications_enabled)
        .filter(lambda args: args[0].matched)
        .filter(lambda args: args[0].risk_score >= NOTIFICATION_THRESHOLD)
        .map(lambda args: _build_direct_decision(*args))
    )
    return decision.get_or_else(None)


def _build_direct_decision(
    assessment: RiskAssessment,
    plan: TravelPlan,
    event: StandardDisasterEvent,
    _prefs: UserPreferences,
) -> NotificationDecision:
    notification = Notification(
        user_id=plan.user_id,
        travel_plan_id=plan.id,
        kind=AlertKind.DIRECT,
        source_key=event.id,
        disaster_event_id=event.id,
        severity=assessment.severity,
        risk_score=assessment.risk_score,
        subject=f"Travel alert: {_category_label(event.category)} near {plan.title}",
        body=_build_direct_body(assessment, plan, event),
    )
    return NotificationDecision(notification=notification, created_at=notification.created_at)


def make_hotspot_notification_decision(
    warning: HotspotWarning, plan: TravelPlan
) -> NotificationDecision:
    notification = Notification(
        user_id=plan.user_id,
        travel_plan_id=plan.id,
        kind=AlertKind.HOTSPOT,
        source_key=warning.location_name.strip().lower(),
        severity=warning.severity,
        risk_score=warning.hotspot_score,
        subject=f"Hotspot warning: {warning.location_name}",
        body=_build_hotspot_body(warning, plan),
    )
    return NotificationDecision(
        notification=notification,
        created_at=notification.created_at,
    )

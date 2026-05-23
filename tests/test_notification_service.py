from datetime import UTC, datetime

from app.contracts.disaster import DisasterSource, StandardDisasterEvent
from app.contracts.hotspot import HotspotWarning
from app.contracts.risk import RiskAssessment, Severity
from app.contracts.travel import TravelPlan
from app.contracts.user import UserPreferences
from app.services.notification_service import (
    make_hotspot_notification_decision,
    make_notification_decision,
)


def build_inputs():
    event = StandardDisasterEvent(
        id="event-1",
        title="Cyclone",
        category="Severe Storms",
        latitude=35.6764,
        longitude=139.65,
        date=datetime(2026, 4, 7, tzinfo=UTC),
        source=DisasterSource.NASA,
    )
    plan = TravelPlan(
        id="plan-1",
        user_id="alice",
        title="Tokyo trip",
        start_at=datetime(2026, 4, 10, tzinfo=UTC),
        end_at=datetime(2026, 4, 13, tzinfo=UTC),
        city="Tokyo",
        country="Japan",
        latitude=35.6764,
        longitude=139.65,
    )
    prefs = UserPreferences(
        user_id="alice",
        max_distance_km=300.0,
        max_days_ahead=7.0,
        enabled_categories=("Severe Storms",),
        notifications_enabled=True,
    )
    return event, plan, prefs


def test_notification_decision_created_only_above_threshold():
    event, plan, prefs = build_inputs()
    low = RiskAssessment(
        travel_plan_id=plan.id,
        user_id=plan.user_id,
        disaster_event_id=event.id,
        distance_km=250.0,
        time_delta_days=6.0,
        risk_score=0.59,
        severity=Severity.MEDIUM,
        matched=True,
    )
    assert make_notification_decision(low, plan, event, prefs) is None


def test_hotspot_notification_decision_uses_hotspot_metadata():
    _, plan, _ = build_inputs()
    warning = HotspotWarning(
        travel_plan_id=plan.id,
        user_id=plan.user_id,
        location_name="Tokyo, Japan",
        hotspot_score=3.2,
        severity=Severity.HIGH,
        event_ids=("a", "b", "c"),
        radius_km=300.0,
        lookback_days=30,
    )
    decision = make_hotspot_notification_decision(warning, plan)
    assert decision.notification.kind.value == "HOTSPOT"
    assert "Tokyo, Japan" in decision.notification.subject
    assert decision.notification.risk_score == 3.2

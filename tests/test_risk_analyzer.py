from datetime import UTC, datetime, timedelta

from app.contracts.disaster import DisasterSource, StandardDisasterEvent
from app.contracts.travel import TravelPlan
from app.contracts.user import UserPreferences
from app.services.risk_analyzer import (
    assess_risk,
    calculate_risk_score,
    distance_km,
    matches_time_window,
)


def build_event(**overrides):
    now = datetime(2026, 4, 7, tzinfo=UTC)
    base = dict(
        id="event-1",
        title="Cyclone",
        category="Severe Storms",
        latitude=35.6764,
        longitude=139.65,
        date=now,
        source=DisasterSource.NASA,
    )
    base.update(overrides)
    return StandardDisasterEvent(**base)


def build_plan(**overrides):
    now = datetime(2026, 4, 10, tzinfo=UTC)
    base = dict(
        id="plan-1",
        user_id="alice",
        title="Tokyo trip",
        start_at=now,
        end_at=now + timedelta(days=3),
        city="Tokyo",
        country="Japan",
        latitude=35.6764,
        longitude=139.65,
    )
    base.update(overrides)
    return TravelPlan(**base)


def build_prefs(**overrides):
    base = dict(
        user_id="alice",
        max_distance_km=300.0,
        max_days_ahead=7.0,
        enabled_categories=("Severe Storms",),
        notifications_enabled=True,
    )
    base.update(overrides)
    return UserPreferences(**base)


def test_distance_km_returns_zero_for_same_point():
    assert distance_km(10.0, 10.0, 10.0, 10.0) == 0.0


def test_distance_km_distinguishes_near_and_far_points():
    near = distance_km(35.6764, 139.65, 35.6895, 139.6917)
    far = distance_km(35.6764, 139.65, 51.5072, -0.1276)
    assert near < 10
    assert far > 9000


def test_matches_time_window_includes_boundaries():
    event = build_event(date=datetime(2026, 4, 3, tzinfo=UTC))
    plan = build_plan(start_at=datetime(2026, 4, 10, tzinfo=UTC))
    prefs = build_prefs(max_days_ahead=7.0)
    assert matches_time_window(event, plan, prefs) is True


def test_matches_time_window_excludes_events_after_trip_or_too_old():
    prefs = build_prefs()
    assert matches_time_window(build_event(date=datetime(2026, 4, 11, tzinfo=UTC)), build_plan(), prefs) is False
    assert matches_time_window(build_event(date=datetime(2026, 3, 31, tzinfo=UTC)), build_plan(), prefs) is False


def test_calculate_risk_score_is_monotonic():
    strong = calculate_risk_score(10.0, 1.0, "Severe Storms")
    weak = calculate_risk_score(200.0, 6.0, "Severe Storms")
    assert strong > weak


def test_assess_risk_returns_none_for_disabled_category():
    assessment = assess_risk(build_event(category="Volcanoes"), build_plan(), build_prefs())
    assert assessment is None


def test_assess_risk_returns_none_when_distance_exceeds_threshold():
    far_event = build_event(latitude=40.7128, longitude=-74.0060)
    assessment = assess_risk(far_event, build_plan(), build_prefs())
    assert assessment is None


def test_assess_risk_returns_assessment_for_matching_event():
    assessment = assess_risk(build_event(), build_plan(), build_prefs())
    assert assessment is not None
    assert assessment.matched is True
    assert assessment.risk_score >= 0.6

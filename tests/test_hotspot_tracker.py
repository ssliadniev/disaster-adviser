from datetime import UTC, datetime, timedelta

from app.contracts.disaster import DisasterSource, StandardDisasterEvent
from app.services.hotspot_tracker import build_hotspot_stats, top_hotspots


def build_event(event_id: str, **overrides):
    now = datetime(2026, 4, 10, tzinfo=UTC)
    base = dict(
        id=event_id,
        title="Storm",
        category="Severe Storms",
        latitude=35.6764,
        longitude=139.65,
        date=now - timedelta(days=2),
        source=DisasterSource.NASA,
        closed=None,
    )
    base.update(overrides)
    return StandardDisasterEvent(**base)


def test_build_hotspot_stats_groups_recent_events_into_regions():
    now = datetime(2026, 4, 10, tzinfo=UTC)
    stats = build_hotspot_stats(
        [
            build_event("a"),
            build_event("b", latitude=35.9, longitude=139.8),
            build_event("old", date=now - timedelta(days=60)),
        ],
        now,
    )
    assert len(stats) == 1
    assert stats[0].event_count == 2
    assert stats[0].weighted_score > 0


def test_top_hotspots_orders_by_weighted_score():
    now = datetime(2026, 4, 10, tzinfo=UTC)
    stats = build_hotspot_stats(
        [
            build_event("near-1", latitude=35.6764, longitude=139.65),
            build_event("near-2", latitude=35.7, longitude=139.7),
            build_event(
                "far-1",
                latitude=-15.78,
                longitude=-71.85,
                date=now - timedelta(days=1),
            ),
        ],
        now,
    )
    ranked = top_hotspots(stats, limit=2)
    assert len(ranked) == 2
    assert ranked[0].weighted_score >= ranked[1].weighted_score

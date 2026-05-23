import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.factory import create_app
from app.api.routers import notifications as notifications_router
from app.db.crud import disaster_event as disaster_event_crud
from app.db.crud import travel_plan as travel_plan_crud
from app.db.crud import user as user_crud
from app.db.crud import user_preferences as prefs_crud
from app.db.models.base import metadata
from app.db.session import get_db

import app.db.models  # noqa: F401


def _run(coro):
    return asyncio.run(coro)


async def _create_schema(engine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)


async def _seed_matching_case(session_maker) -> int:
    async with session_maker() as session:
        user = await user_crud.create_user(
            session,
            email="alice@example.com",
            hashed_password="hashed",
        )
        await prefs_crud.create_default_preferences(session, user["id"])
        await prefs_crud.update_preferences(
            session,
            user["id"],
            disaster_categories=["Severe Storms"],
            alert_threshold_distance_km=300.0,
        )
        await travel_plan_crud.upsert_travel_plan(
            session,
            user_id=user["id"],
            event_id="plan-tokyo",
            calendar_id="primary",
            event_summary="Tokyo trip",
            location_name="Tokyo",
            latitude=35.6764,
            longitude=139.65,
            start_time=datetime(2026, 5, 14, tzinfo=UTC),
            end_time=datetime(2026, 5, 18, tzinfo=UTC),
        )
        await disaster_event_crud.upsert_disaster_event(
            session,
            external_event_id="event-tokyo",
            title="Tokyo cyclone",
            category="Severe Storms",
            latitude=35.6764,
            longitude=139.65,
            event_date=datetime(2026, 5, 10, tzinfo=UTC),
            source="NASA",
        )
        return user["id"]


def make_client(tmp_path, monkeypatch):
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    engine = create_async_engine(database_url, future=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    _run(_create_schema(engine))

    monkeypatch.setattr(notifications_router, "AsyncSessionLocal", session_maker)

    app = create_app()

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, session_maker, engine


def test_recompute_creates_matching_notification(tmp_path, monkeypatch):
    client, session_maker, engine = make_client(tmp_path, monkeypatch)
    user_id = _run(_seed_matching_case(session_maker))

    response = client.post(f"/notifications/recompute/{user_id}")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["notifications"]) == 1
    assert payload["notifications"][0]["kind"] == "DIRECT"
    _run(engine.dispose())


def test_recompute_does_not_duplicate_same_notification(tmp_path, monkeypatch):
    client, session_maker, engine = make_client(tmp_path, monkeypatch)
    user_id = _run(_seed_matching_case(session_maker))

    first = client.post(f"/notifications/recompute/{user_id}")
    second = client.post(f"/notifications/recompute/{user_id}")
    listed = client.get(f"/notifications/{user_id}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert listed.status_code == 200
    assert len(listed.json()["notifications"]) == 1
    _run(engine.dispose())


def test_notification_stream_emits_sse_event(tmp_path, monkeypatch):
    client, session_maker, engine = make_client(tmp_path, monkeypatch)
    user_id = _run(_seed_matching_case(session_maker))
    recompute = client.post(f"/notifications/recompute/{user_id}")
    assert recompute.status_code == 200

    class _RequestStub:
        async def is_disconnected(self) -> bool:
            return False

    async def _read_first_chunk() -> str:
        stream = notifications_router._notification_event_stream(
            request=_RequestStub(),
            user_id=user_id,
            after_id=0,
        )
        try:
            return await anext(stream)
        finally:
            await stream.aclose()

    chunk = _run(_read_first_chunk())
    assert "event: notification" in chunk
    assert '"kind": "DIRECT"' in chunk
    assert '"subject": "Travel alert:' in chunk
    _run(engine.dispose())


def test_global_hotspots_are_available(tmp_path, monkeypatch):
    client, session_maker, engine = make_client(tmp_path, monkeypatch)
    _run(_seed_matching_case(session_maker))

    response = client.get("/api/v1/hotspots")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["hotspots"]) == 1
    assert payload["hotspots"][0]["region_key"]
    assert payload["hotspots"][0]["weighted_score"] > 0
    _run(engine.dispose())


def test_overlap_timerange_includes_trip_on_requested_day(tmp_path, monkeypatch):
    _, session_maker, engine = make_client(tmp_path, monkeypatch)
    user_id = _run(_seed_matching_case(session_maker))

    async def _fetch():
        async with session_maker() as session:
            return await travel_plan_crud.get_by_user_overlapping_timerange(
                session,
                user_id,
                datetime(2026, 5, 15, tzinfo=UTC),
                datetime(2026, 5, 16, tzinfo=UTC),
            )

    plans = _run(_fetch())
    assert len(plans) == 1
    assert plans[0]["event_summary"] == "Tokyo trip"
    _run(engine.dispose())

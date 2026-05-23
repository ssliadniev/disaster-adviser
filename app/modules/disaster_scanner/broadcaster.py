import asyncio

from app.db.crud import disaster_event as disaster_event_crud
from app.db.session import AsyncSessionLocal
from app.modules.hotspot_tracker import refresh_hotspot_regions
from app.modules.disaster_scanner.cache import store_disaster
from app.modules.disaster_scanner.pipeline import build_disaster_pipeline
from app.modules.disaster_scanner.repository import save_event_to_csv


async def stream_consumer_worker():
    from aiostream import streamcontext

    print(">>> [WORKER] Background stream consumer started!", flush=True)
    pipeline = build_disaster_pipeline()

    try:
        async with streamcontext(pipeline) as streamer:
            async for event in streamer:
                try:
                    print(
                        f">>> [PIPELINE] Processed: {event.source.value} - {event.title}",
                        flush=True,
                    )
                    store_disaster(event)
                    await save_event_to_csv(event)
                    from app.modules.notification_service.integration import (
                        process_disaster_notifications,
                    )

                    async with AsyncSessionLocal() as session:
                        await disaster_event_crud.upsert_disaster_event(
                            session,
                            external_event_id=event.id,
                            title=event.title,
                            category=event.category.value
                            if hasattr(event.category, "value")
                            else str(event.category),
                            latitude=event.latitude,
                            longitude=event.longitude,
                            event_date=event.date,
                            source=event.source.value,
                            closed_at=getattr(event, "closed", None),
                        )
                        await refresh_hotspot_regions(session)
                        await process_disaster_notifications(session, event)
                except Exception as e:
                    print(f">>> [PIPELINE ERROR]: {e}", flush=True)

    except asyncio.CancelledError:
        print(">>> [WORKER] Shutting down.", flush=True)
    except Exception as e:
        print(f">>> [FATAL PIPELINE CRASH]: {e}", flush=True)

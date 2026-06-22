import asyncio
import logging

import aiohttp

from app.db.crud import disaster_event as disaster_event_crud
from app.db.session import AsyncSessionLocal
from app.modules.disaster_scanner.cache import store_disaster
from app.modules.disaster_scanner.config import ScannerConfig
from app.modules.disaster_scanner.pipeline import build_disaster_pipeline
from app.modules.disaster_scanner.repository import save_event_to_csv
from app.modules.hotspot_tracker import refresh_hotspot_regions
from app.modules.disaster_scanner.sources_auth import TokenProvider

logger = logging.getLogger(__name__)


async def _load_initial_dedup_keys() -> set:
    return set()


async def stream_consumer_worker():
    from aiostream import streamcontext

    logger.info(msg=">>> [WORKER] Background stream consumer started!")

    config = ScannerConfig()

    try:
        async with aiohttp.ClientSession() as http_session:
            token_provider = TokenProvider(
                session=http_session,
                authorize_url=config.dae_authorize_url,
                credentials=config.dae_credentials,
                timeout_seconds=config.request_timeout_seconds,
            )

            initial_keys = await _load_initial_dedup_keys()
            pipeline = build_disaster_pipeline(
                http_session, token_provider, config, initial_keys=initial_keys
            )

            async with streamcontext(pipeline) as streamer:
                async for event in streamer:
                    try:
                        logger.info(f">>> [PIPELINE] Processed: {event.source.value} - {event.title}")
                        store_disaster(event)
                        await save_event_to_csv(event)
                        from app.modules.notification_service.integration import \
                            process_disaster_notifications

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
                    except Exception as error:
                        logger.info(f">>> [PIPELINE ERROR]: {error}")

    except asyncio.CancelledError:
        logger.info(">>> [WORKER] Shutting down.")
    except Exception as error:
        logger.info(f">>> [FATAL PIPELINE CRASH]: {error}")

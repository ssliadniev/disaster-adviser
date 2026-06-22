import asyncio
import logging
from typing import AsyncIterator, Awaitable, Callable, List, Optional

import aiohttp

from app.modules.disaster_scanner.config import ScannerConfig
from app.modules.disaster_scanner.exceptions import (PermanentFetchError,
                                                     RetryableFetchError)
from app.modules.disaster_scanner.helpers import (_decode_ndjson,
                                                  _parse_retry_after,
                                                  _sleep_idle)
from app.modules.disaster_scanner.sources_auth import TokenProvider

logger = logging.getLogger(__name__)


async def _poll(
    fetch_once: Callable[[], Awaitable[List[dict]]],
    config: ScannerConfig,
    *,
    name: str,
    stop: Optional[asyncio.Event] = None,
    max_consecutive_failures: Optional[int] = None,
) -> AsyncIterator[dict]:
    backoff = 1.0
    failures = 0

    while stop is None or not stop.is_set():
        try:
            batch = await fetch_once()
        except asyncio.CancelledError:
            raise
        except RetryableFetchError as exc:
            failures += 1

            if max_consecutive_failures is not None and failures >= max_consecutive_failures:
                logger.info(msg=f"[{name}] giving up after {failures} consecutive failures")
                raise

            wait = exc.retry_after if exc.retry_after is not None else backoff
            wait = min(wait, config.max_backoff_seconds)
            logger.info(msg=f"[{name}] retryable error: {exc} (waiting {wait})")

            await asyncio.sleep(wait)

            backoff = min(backoff * 2, config.max_backoff_seconds)
            continue

        failures = 0
        backoff = 1.0

        for item in batch:
            yield item

        await _sleep_idle(config)


async def _fetch_nasa_once(
    session: aiohttp.ClientSession, config: ScannerConfig
) -> List[dict]:
    try:
        async with session.get(
            config.nasa_events_url,
            headers={"Accept": "application/json"},
            timeout=aiohttp.ClientTimeout(total=config.request_timeout_seconds)
        ) as response:
            if response.status == 429:
                raise RetryableFetchError(
                    message="NASA 429",
                    retry_after=_parse_retry_after(response.headers.get("Retry-After")),
                )

            if response.status >= 500:
                raise RetryableFetchError(f"NASA {response.status}")

            if response.status != 200:
                raise PermanentFetchError(f"NASA {response.status}")

            data = await response.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise RetryableFetchError(f"NASA network error: {exc}") from exc

    events = data.get("events", []) or []
    logger.info(f"[NASA] fetched {len(events)} events")

    return events


def fetch_nasa_stream(
    session: aiohttp.ClientSession,
    config: ScannerConfig,
    *,
    stop: Optional[asyncio.Event] = None,
) -> AsyncIterator[dict]:
    return _poll(
        lambda: _fetch_nasa_once(session, config),
        config,
        name="NASA",
        stop=stop,
        max_consecutive_failures=config.max_consecutive_failures,
    )


async def _fetch_dae_once(
    session: aiohttp.ClientSession,
    token_provider: TokenProvider,
    config: ScannerConfig,
) -> List[dict]:
    headers = await token_provider.authorization_header()
    headers["Accept"] = "application/x-ndjson"

    try:
        async with session.get(
            config.dae_hazards_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=config.request_timeout_seconds),
        ) as response:
            if response.status in (401, 403):
                await token_provider.invalidate()
                raise RetryableFetchError(f"DAE auth rejected ({response.status})")

            if response.status == 429:
                raise RetryableFetchError(
                    message="DAE 429",
                    retry_after=_parse_retry_after(response.headers.get("Retry-After"))
                )

            if response.status >= 500:
                raise RetryableFetchError(f"DAE {response.status}")

            if response.status != 200:
                raise PermanentFetchError(f"DAE {response.status}")

            raw = await response.read()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise RetryableFetchError(f"DAE network error: {exc}") from exc

    hazards = list(_decode_ndjson(raw))
    logger.info(f"[DAE] fetched {len(hazards)} hazards", len(hazards))

    return hazards


def fetch_disasteraware_stream(
    session: aiohttp.ClientSession,
    token_provider: TokenProvider,
    config: ScannerConfig,
    *,
    stop: Optional[asyncio.Event] = None,
) -> AsyncIterator[dict]:
    return _poll(
        lambda: _fetch_dae_once(session, token_provider, config),
        config,
        name="DAE",
        stop=stop,
        max_consecutive_failures=config.max_consecutive_failures,
    )

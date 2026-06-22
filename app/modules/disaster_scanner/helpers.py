import asyncio
import logging
import gzip
import json
import random
from typing import Iterator, Optional

from config import ScannerConfig

logger = logging.getLogger(__name__)

_GZIP_MAGIC = b"\x1f\x8b"


def _parse_retry_after(value: Optional[str]) -> Optional[float]:
    """
    Retry-After in delta-seconds form.
    """

    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


async def _sleep_idle(config: ScannerConfig) -> None:
    await asyncio.sleep(
        config.poll_interval_seconds
        + random.uniform(0, max(0.0, config.poll_jitter_seconds))
    )


def _decode_ndjson(raw: bytes) -> Iterator[dict]:
    """
    Decode a (possibly gzipped) NDJSON payload into dict objects.
    """

    if raw[:2] == _GZIP_MAGIC:
        raw = gzip.decompress(raw)

    for line in raw.splitlines():
        line = line.strip()

        if not line:
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.info("[DAE] skipping malformed NDJSON line")
            continue
        if isinstance(obj, dict):
            yield obj

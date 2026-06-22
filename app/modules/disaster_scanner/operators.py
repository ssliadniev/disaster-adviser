import time
from collections import OrderedDict
from typing import Callable, Hashable, Iterable, Optional, TypeVar

from aiostream import pipable_operator, streamcontext

T = TypeVar("T")
TKey = TypeVar("TKey", bound=Hashable)


@pipable_operator
async def distinct(
    source,
    key: Callable[[T], TKey],
    *,
    max_size: int = 100_000,
    ttl_seconds: Optional[float] = None,
    initial_keys: Optional[Iterable[TKey]] = None,
):
    """
    Yield each item only the first time `key(item)` is seen.
    """

    monotonic = time.monotonic
    cache: "OrderedDict[TKey, float]" = OrderedDict()

    if initial_keys:
        seeded_at = monotonic()
        for k in initial_keys:
            cache[k] = seeded_at

    def _purge_expired() -> None:
        if ttl_seconds is None:
            return

        cutoff = monotonic() - ttl_seconds
        while cache:
            _oldest_key, inserted_at = next(iter(cache.items()))

            if inserted_at >= cutoff:
                break

            cache.popitem(last=False)

    async with streamcontext(source) as streamer:
        async for item in streamer:
            _purge_expired()
            k = key(item)

            if k in cache:
                cache.move_to_end(k)
                continue

            cache[k] = monotonic()
            while len(cache) > max_size:
                cache.popitem(last=False)

            yield item

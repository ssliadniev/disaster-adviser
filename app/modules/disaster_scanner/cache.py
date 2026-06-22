from collections import OrderedDict
from typing import List

from app.contracts.disaster import StandardDisasterEvent

MAX_CACHE_SIZE = 10_000
ACTIVE_DISASTERS_CACHE: OrderedDict[str, StandardDisasterEvent] = OrderedDict()


def get_current_disasters() -> List[StandardDisasterEvent]:
    return list(ACTIVE_DISASTERS_CACHE.values())


def store_disaster(event: StandardDisasterEvent) -> None:
    if event.id in ACTIVE_DISASTERS_CACHE:
        ACTIVE_DISASTERS_CACHE.move_to_end(event.id)

    ACTIVE_DISASTERS_CACHE[event.id] = event

    while len(ACTIVE_DISASTERS_CACHE) > MAX_CACHE_SIZE:
        ACTIVE_DISASTERS_CACHE.popitem(last=False)

from __future__ import annotations

from typing import Dict

from app.contracts.disaster import StandardDisasterEvent

ACTIVE_DISASTERS_CACHE: Dict[str, StandardDisasterEvent] = {}


def get_current_disasters() -> list[StandardDisasterEvent]:
    return list(ACTIVE_DISASTERS_CACHE.values())


def store_disaster(event: StandardDisasterEvent) -> None:
    ACTIVE_DISASTERS_CACHE[event.id] = event

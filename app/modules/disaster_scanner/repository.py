import asyncio
import csv
import logging
import os
from typing import Set

from app.contracts.disaster import (DedupKey, StandardDisasterEvent,
                                    make_dedup_key)

CSV_FILE_PATH = "disasters_events.csv"

_CSV_HEADER = [
    "ID", "Title", "Category", "Latitude", "Longitude", "Date", "Source", "Closed",
]

logger = logging.getLogger(__name__)

_csv_lock = asyncio.Lock()


def _category_value(event: StandardDisasterEvent):
    return event.category.value if hasattr(event.category, "value") else event.category


async def save_event_to_csv(event: StandardDisasterEvent) -> None:
    def _write() -> None:
        file_exists = os.path.isfile(CSV_FILE_PATH)

        with open(CSV_FILE_PATH, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            if not file_exists:
                writer.writerow(_CSV_HEADER)

            writer.writerow(
                [
                    event.id,
                    event.title,
                    _category_value(event),
                    event.latitude,
                    event.longitude,
                    event.date.isoformat(),
                    event.source.value,
                    event.severity or "",
                    event.closed.isoformat() if event.closed else "",
                ]
            )

    async with _csv_lock:
        try:
            await asyncio.to_thread(_write)
        except Exception as exc:
            logger.error(f"Failed to save event {event.id} to CSV: {exc}")


def load_seen_keys_from_csv() -> Set[DedupKey]:
    keys: Set[DedupKey] = set()
    if not os.path.isfile(CSV_FILE_PATH):
        return keys

    try:
        with open(CSV_FILE_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                keys.add(
                    make_dedup_key(
                        row["Source"], row["ID"], row["Date"], row.get("Closed") or None
                    )
                )
    except Exception as exc:
        logger.warning(f"Could not seed dedup from CSV: {exc}")

    return keys

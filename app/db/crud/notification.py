from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import notifications_table
from app.db.utils import row_to_dict, rows_to_list

SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


async def get_by_dedup_key(
    session: AsyncSession,
    *,
    user_id: int,
    travel_plan_id: int | None,
    kind: str,
    source_key: str,
) -> dict | None:
    stmt = select(notifications_table).where(
        notifications_table.c.user_id == user_id,
        notifications_table.c.travel_plan_id == travel_plan_id,
        notifications_table.c.kind == kind,
        notifications_table.c.source_key == source_key,
    )
    result = await session.execute(stmt)
    return row_to_dict(result)


def _is_upgrade(existing: dict, severity: str, risk_score: float) -> bool:
    existing_rank = SEVERITY_ORDER.get(existing["severity"], 0)
    next_rank = SEVERITY_ORDER.get(severity, 0)
    return next_rank > existing_rank or (
        next_rank == existing_rank and risk_score > existing["risk_score"]
    )


async def upsert_notification(
    session: AsyncSession,
    *,
    user_id: int,
    travel_plan_id: int | None,
    kind: str,
    source_key: str,
    severity: str,
    risk_score: float,
    subject: str,
    body: str,
    recipient_email: str,
    disaster_event_id: str | None = None,
) -> tuple[dict, bool]:
    existing = await get_by_dedup_key(
        session,
        user_id=user_id,
        travel_plan_id=travel_plan_id,
        kind=kind,
        source_key=source_key,
    )

    if existing is None:
        stmt = notifications_table.insert().values(
            user_id=user_id,
            travel_plan_id=travel_plan_id,
            kind=kind,
            source_key=source_key,
            severity=severity,
            risk_score=risk_score,
            subject=subject,
            body=body,
            recipient_email=recipient_email,
            disaster_event_id=disaster_event_id,
        ).returning(notifications_table)
        result = await session.execute(stmt)
        await session.commit()
        return row_to_dict(result), True

    if not _is_upgrade(existing, severity, risk_score):
        return existing, False

    stmt = (
        update(notifications_table)
        .where(notifications_table.c.id == existing["id"])
        .values(
            severity=severity,
            risk_score=risk_score,
            subject=subject,
            body=body,
            recipient_email=recipient_email,
            disaster_event_id=disaster_event_id,
            updated_at=datetime.now(UTC),
        )
        .returning(notifications_table)
    )
    result = await session.execute(stmt)
    await session.commit()
    return row_to_dict(result), True


async def mark_published(session: AsyncSession, notification_id: int) -> dict | None:
    stmt = (
        update(notifications_table)
        .where(notifications_table.c.id == notification_id)
        .values(sent_at=datetime.now(UTC))
        .returning(notifications_table)
    )
    result = await session.execute(stmt)
    await session.commit()
    return row_to_dict(result)


async def get_by_user_id(session: AsyncSession, user_id: int) -> list[dict]:
    stmt = (
        select(notifications_table)
        .where(notifications_table.c.user_id == user_id)
        .order_by(notifications_table.c.updated_at.desc())
    )
    result = await session.execute(stmt)
    return rows_to_list(result)

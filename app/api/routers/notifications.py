from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.contracts.notification import (
    NotificationListResponse,
    NotificationResponse,
    NotificationRecomputeResponse,
)
from app.contracts.user import TokenData
from app.db.crud import notification as notification_crud
from app.db.crud import travel_plan as travel_plan_crud
from app.db.session import AsyncSessionLocal
from app.modules.notification_service.integration import (
    process_travel_plan_notifications,
)

router = APIRouter(tags=["Notifications"])
api_router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])

try:
    from app.core.dependencies import get_current_user
except ModuleNotFoundError:
    get_current_user = None


STREAM_POLL_INTERVAL_SECONDS = 1.0


async def _db_recompute(user_id: str) -> dict[str, list]:
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {"assessments": [], "hotspot_warnings": [], "notifications": []}

    async with AsyncSessionLocal() as session:
        plans = await travel_plan_crud.get_all_by_user(session, user_id_int)
        for plan in plans:
            await process_travel_plan_notifications(session, plan)
        notifications = await notification_crud.get_by_user_id(session, user_id_int)
        return {
            "assessments": [],
            "hotspot_warnings": [],
            "notifications": notifications,
        }


async def _db_list_notifications(user_id: str) -> dict[str, list]:
    try:
        user_id_int = int(user_id)
    except ValueError:
        return {"notifications": []}

    async with AsyncSessionLocal() as session:
        notifications = await notification_crud.get_by_user_id(session, user_id_int)
        return {"notifications": notifications}


def _coerce_user_id(user_id: str) -> int:
    try:
        return int(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc


def _format_sse_event(notification: dict) -> str:
    payload = NotificationResponse.model_validate(notification).model_dump(mode="json")
    event_id = payload.get("id", "")
    return (
        f"id: {event_id}\n"
        "event: notification\n"
        f"data: {json.dumps(payload)}\n\n"
    )


async def _notification_event_stream(
    *,
    request: Request,
    user_id: int,
    after_id: int,
) -> AsyncIterator[str]:
    last_seen_id = after_id

    while True:
        if await request.is_disconnected():
            break

        async with AsyncSessionLocal() as session:
            notifications = await notification_crud.get_by_user_id_after(
                session,
                user_id,
                last_seen_id,
            )

        if notifications:
            for notification in notifications:
                if await request.is_disconnected():
                    return
                last_seen_id = max(last_seen_id, int(notification["id"]))
                yield _format_sse_event(notification)
        else:
            yield ": keepalive\n\n"

        await asyncio.sleep(STREAM_POLL_INTERVAL_SECONDS)


def _serialize_recompute_result(result: dict[str, list]) -> dict[str, list]:
    return result


@router.post("/notifications/recompute/{user_id}", response_model=NotificationRecomputeResponse)
async def recompute_notifications(user_id: str, request: Request) -> dict[str, list]:
    _ = request
    return await _db_recompute(user_id)


@router.get("/notifications/{user_id}", response_model=NotificationListResponse)
async def list_notifications(user_id: str, request: Request) -> dict[str, list]:
    _ = request
    return await _db_list_notifications(user_id)


@router.get("/notifications/stream/{user_id}")
async def stream_notifications(
    user_id: str,
    request: Request,
    after_id: int = Query(0, ge=0),
) -> StreamingResponse:
    return StreamingResponse(
        _notification_event_stream(
            request=request,
            user_id=_coerce_user_id(user_id),
            after_id=after_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if get_current_user is not None:

    @api_router.post("/recompute", response_model=NotificationRecomputeResponse)
    async def recompute_my_notifications(
        current_user: TokenData = Depends(get_current_user),
    ) -> dict[str, list]:
        if current_user.user_id is None:
            return {"assessments": [], "hotspot_warnings": [], "notifications": []}
        return await _db_recompute(str(current_user.user_id))


    @api_router.get("", response_model=NotificationListResponse)
    async def list_my_notifications(
        current_user: TokenData = Depends(get_current_user),
    ) -> dict[str, list]:
        if current_user.user_id is None:
            return {"notifications": []}
        return await _db_list_notifications(str(current_user.user_id))


    @api_router.get("/stream")
    async def stream_my_notifications(
        request: Request,
        current_user: TokenData = Depends(get_current_user),
        after_id: int = Query(0, ge=0),
    ) -> StreamingResponse:
        if current_user.user_id is None:
            raise HTTPException(status_code=401, detail="User not authenticated")
        return StreamingResponse(
            _notification_event_stream(
                request=request,
                user_id=current_user.user_id,
                after_id=after_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.contracts.notification import (
    NotificationListResponse,
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

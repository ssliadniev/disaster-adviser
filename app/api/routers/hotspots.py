from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.hotspot import HotspotListResponse
from app.db.session import get_db
from app.modules.hotspot_tracker import list_global_hotspots

router = APIRouter(prefix="/api/v1/hotspots", tags=["Hotspots"])


@router.get("", response_model=HotspotListResponse)
async def get_global_hotspots(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[dict]]:
    hotspots = await list_global_hotspots(db, limit=limit, refresh=True)
    return {"hotspots": hotspots}

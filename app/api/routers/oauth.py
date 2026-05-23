from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import OAuthStateManager, get_oauth_state_manager
from app.modules.auth.google_oauth_service import (
    process_oauth_registration,
    process_oauth_connection,
    build_auth_url,
    build_registration_response,
    build_connection_response,
)
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/oauth", tags=["OAuth"])


@router.get(
    "/google/register",
    summary="Register with Google (Browser Redirect)",
    description="Start Google OAuth registration flow - no authentication required",
)
async def google_register(
    state_manager: OAuthStateManager = Depends(get_oauth_state_manager),
) -> RedirectResponse:
    state = state_manager.register(action="register")
    return RedirectResponse(url=build_auth_url(state, scopes=[]))


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str | None = None,
    scope: str | None = None,
    db: AsyncSession = Depends(get_db),
    state_manager: OAuthStateManager = Depends(get_oauth_state_manager),
) -> dict:
    payload = state_manager.consume(state) if state else None

    match payload:
        case None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state",
            )
        case {"action": "register"}:
            result = await process_oauth_registration(code, scope, db)
            return build_registration_response(result["user"], result["message"])

        case {"action": "connect", "user_id": int(user_id)}:
            result = await process_oauth_connection(code, scope, user_id, db)
            return build_connection_response(result["token_data"], result["scope"])

        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown OAuth action",
            )

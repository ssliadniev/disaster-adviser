from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.user import Token, UserCreate, UserResponse
from app.modules.auth.error_mapping import auth_error_mapper
from app.modules.auth.service import authenticate_user, register_new_user
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/token",
    response_model=Token,
    summary="Login",
    description="Authenticate user and get access token",
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> Token:
    """Authenticate user and return access token."""
    try:
        token_data = await authenticate_user(db, form_data.username, form_data.password)
        return Token(**token_data)
    except Exception as e:
        http_exc = auth_error_mapper(e)
        if http_exc.status_code == status.HTTP_401_UNAUTHORIZED:
            http_exc.headers = {"WWW-Authenticate": "Bearer"}
        raise http_exc


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register User",
    description="Create a new user account",
)
async def register_user(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Register a new user with default preferences."""
    try:
        new_user = await register_new_user(db, user_data.email, user_data.password)
        await db.commit()
        return UserResponse(id=new_user["id"], email=new_user["email"])
    except Exception as e:
        await db.rollback()
        raise auth_error_mapper(e)

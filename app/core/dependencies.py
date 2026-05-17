import secrets
from typing import TypeAlias

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.contracts.user import TokenData
from app.core.security import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def _extract_user_credentials(payload: dict) -> tuple[str | None, int | None]:
    return payload.get("sub"), payload.get("user_id")


def _validate_email(email: str | None) -> str:
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return email


def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    payload = verify_token(token)
    email, user_id = _extract_user_credentials(payload)
    validated_email = _validate_email(email)
    return TokenData(email=validated_email, user_id=user_id)


OAuthState: TypeAlias = dict[str, object]
OAuthStateStore: TypeAlias = dict[str, OAuthState]


def _generate_state_key() -> str:
    return secrets.token_urlsafe(32)


def _build_state(action: str, user_id: int | None) -> OAuthState:
    return {"user_id": user_id, "action": action}


def _add_state(store: OAuthStateStore, key: str, state: OAuthState) -> OAuthStateStore:
    return {**store, key: state}


def _remove_state(store: OAuthStateStore, key: str) -> OAuthStateStore:
    return {k: v for k, v in store.items() if k != key}


class OAuthStateManager:
    def __init__(self) -> None:
        self._store: OAuthStateStore = {}

    def register(self, action: str, user_id: int | None = None) -> str:
        key = _generate_state_key()
        state = _build_state(action, user_id)
        self._store = _add_state(self._store, key, state)
        return key

    def consume(self, key: str) -> OAuthState | None:
        value = self._store.get(key)
        self._store = _remove_state(self._store, key)
        return value


oauth_state_manager = OAuthStateManager()


def get_oauth_state_manager() -> OAuthStateManager:
    return oauth_state_manager
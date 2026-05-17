import hashlib
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import TypeAlias, Callable

import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.core.config import settings
from app.utils.functional import compose

Payload: TypeAlias = dict[str, object]
Token: TypeAlias = str


_encode_token = partial(jwt.encode, key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)
_decode_token = partial(jwt.decode, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

def create_access_token(data: Payload, expires_delta: timedelta | None = None) -> Token:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return _encode_token({**data, "exp": expire})

def verify_token(token: Token) -> Payload:
    try:
        return _decode_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _sha256_hex(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _bcrypt_hash(intermediate: str) -> str:
    return bcrypt.hashpw(intermediate.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _bcrypt_verify(intermediate: str, hashed: str) -> bool:
    return bcrypt.checkpw(intermediate.encode("utf-8"), hashed.encode("utf-8"))

get_password_hash: Callable[[str], str] = compose(_sha256_hex, _bcrypt_hash)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return compose(_sha256_hex, partial(_bcrypt_verify, hashed=hashed_password))(plain_password)
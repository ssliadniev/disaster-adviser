import asyncio
import base64
import json
import logging
import time
from typing import Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)

_EXP_SKEW_SECONDS = 60
_FALLBACK_LIFETIME_SECONDS = 13 * 60


def _decode_jwt_exp(token: str) -> Optional[int]:
    """
    Read the `exp` (epoch seconds) claim from a JWT *without* verifying the signature.

    Returns None if the token is not a decodable JWT.
    """

    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)

        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = claims.get("exp")

        return int(exp) if exp is not None else None
    except (IndexError, ValueError, TypeError, json.JSONDecodeError) as exc:
        logger.warning("Failed to decode JWT expiry: %s", exc)
        return None


class TokenProvider:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        authorize_url: str,
        credentials: Dict[str, str],
        *,
        timeout_seconds: float | int = 30.0,
    ) -> None:
        self._session = session
        self._authorize_url = authorize_url
        self._credentials = credentials
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: float | int = 0.0
        self._lock = asyncio.Lock()

    @property
    def _is_valid(self) -> bool:
        return (
            self._access_token is not None
            and time.time() < self._expires_at - _EXP_SKEW_SECONDS
        )

    async def get_token(self) -> Optional[str]:
        if self._is_valid:
            return self._access_token

        async with self._lock:
            if self._is_valid:
                return self._access_token

            await self._authorize()
            return self._access_token

    async def authorization_header(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {await self.get_token()}"}

    async def invalidate(self) -> None:
        """
        Drop the cached token so the next get_token() re-authorizes.
        """

        async with self._lock:
            self._access_token = None
            self._expires_at = 0.0

    async def _authorize(self) -> None:
        logger.info("Authorizing with DisasterAWARE ...")

        async with self._session.post(
            self._authorize_url, json=self._credentials, timeout=self._timeout
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"Authorization failed ({resp.status}): {body[:300]}")

            data = await resp.json(content_type=None)

        token = data.get("accessToken") or data.get("access_token")
        if not token:
            raise RuntimeError(f"No accessToken in authorize response: {list(data)}")

        self._access_token = token
        self._refresh_token = data.get("refreshToken") or data.get("refresh_token")

        exp = _decode_jwt_exp(token)
        self._expires_at = float(exp) if exp else time.time() + _FALLBACK_LIFETIME_SECONDS

        logger.info("Token acquired (valid ~%.0fs).", self._expires_at - time.time())

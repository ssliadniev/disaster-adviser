import os
from dataclasses import dataclass
from typing import Dict, Optional


def _env_float(name: str, default: float | int) -> float | int:
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        return float(raw)
    except ValueError:
        return default


def _env_int_or_none(name: str) -> Optional[int]:
    raw = os.getenv(name)
    if not raw:
        return None

    try:
        return int(raw)
    except ValueError:
        return None


@dataclass(frozen=True)
class ScannerConfig:
    dae_base_url: str = os.getenv("DAE_BASE_URL", "https://api-v2.disasteraware.com")
    dae_authorize_path: str = os.getenv("DAE_AUTHORIZE_PATH", "/authorize")
    dae_hazards_path: str = os.getenv("DAE_HAZARDS_PATH", "/active-hazards-query")
    dae_username: str = os.getenv("DAE_USERNAME", "")
    dae_password: str = os.getenv("DAE_PASSWORD", "")

    nasa_events_url: str = os.getenv(
        "NASA_EVENTS_URL", "https://eonet.gsfc.nasa.gov/api/v3/events"
    )

    poll_interval_seconds: float = _env_float("SCANNER_POLL_INTERVAL", 300.0)
    poll_jitter_seconds: float = _env_float("SCANNER_POLL_JITTER", 30.0)

    max_backoff_seconds: float = _env_float("SCANNER_MAX_BACKOFF", 120.0)
    request_timeout_seconds: float = _env_float("SCANNER_REQUEST_TIMEOUT", 30.0)
    max_consecutive_failures: Optional[int] = _env_int_or_none("SCANNER_MAX_FAILURES")

    dedup_max_size: int = int(os.getenv("SCANNER_DEDUP_MAX", "100000"))

    @property
    def dae_authorize_url(self) -> str:
        return f"{self.dae_base_url}{self.dae_authorize_path}"

    @property
    def dae_hazards_url(self) -> str:
        return f"{self.dae_base_url}{self.dae_hazards_path}"

    @property
    def dae_credentials(self) -> Dict[str, str]:
        return {"username": self.dae_username, "password": self.dae_password}

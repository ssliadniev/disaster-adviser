from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./disaster_adviser.db"
    SECRET_KEY: str = "development-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 200
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RISK_MAX_DAYS_AHEAD: float = 7.0
    HOTSPOT_LOOKBACK_DAYS: int = 30
    HOTSPOT_RADIUS_KM: float = 300.0
    HOTSPOT_THRESHOLD: float = 2.4
    HOTSPOT_ACTIVE_BONUS: float = 0.15
    HOTSPOT_GRID_DEGREES: float = 5.0

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    GOOGLE_SCOPES: str | None = None
    GOOGLE_WEBHOOK_URL: str | None = None
    GEOAPIFY_API_KEY: str | None = None

    CORS_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

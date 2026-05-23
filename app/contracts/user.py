from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.contracts.disaster import DisasterCategory


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None
    user_id: int | None = None


class UserPreferences(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: str
    max_distance_km: float = Field(gt=0)
    max_days_ahead: float = Field(gt=0)
    enabled_categories: tuple[str, ...]
    notifications_enabled: bool = True


class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (plain text, will be hashed)",
    )


class UserResponse(BaseModel):
    """Response schema for user data (no password)"""

    id: int
    email: str

    class Config:
        from_attributes = True


class PreferencesUpdate(BaseModel):
    """User preferences update"""

    notification_enabled: bool | None = None
    disaster_categories: list[str] | None = Field(
        None,
        description=f"List of disaster types to track. Valid categories: {', '.join(DisasterCategory.get_all_values())}",
        examples=[DisasterCategory.get_all_values()],
    )
    alert_threshold_distance_km: float | None = Field(None, gt=0, le=10000)
    timezone: str | None = Field(
        None, description="Timezone (e.g., 'UTC', 'America/New_York')"
    )


class PreferencesResponse(BaseModel):
    """User preferences response"""

    id: int
    user_id: int
    notification_enabled: bool
    disaster_categories: list[str]
    alert_threshold_distance_km: float
    timezone: str

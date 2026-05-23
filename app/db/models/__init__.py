from app.db.models.user import users_table
from app.db.models.oauth_token import oauth_accounts_table
from app.db.models.webhook_channel import webhook_channels_table
from app.db.models.travel_plan import travel_plans_table
from app.db.models.user_preferences import user_preferences_table

__all__ = [
    "users_table",
    "oauth_accounts_table",
    "webhook_channels_table",
    "travel_plans_table",
    "user_preferences_table",
]

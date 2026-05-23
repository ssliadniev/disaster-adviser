from app.db.models.user import users_table
from app.db.models.oauth_token import oauth_accounts_table
from app.db.models.webhook_channel import webhook_channels_table
from app.db.models.travel_plan import travel_plans_table
from app.db.models.user_preferences import user_preferences_table
from app.db.models.disaster_event import disaster_events_table
from app.db.models.hotspot_region import hotspot_regions_table
from app.db.models.notification import notifications_table

__all__ = [
    "users_table",
    "oauth_accounts_table",
    "webhook_channels_table",
    "travel_plans_table",
    "user_preferences_table",
    "disaster_events_table",
    "hotspot_regions_table",
    "notifications_table",
]

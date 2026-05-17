import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from app.db.models.base import metadata

disaster_categories_type = sa.JSON().with_variant(ARRAY(sa.String), "postgresql")

user_preferences_table = sa.Table(
    "user_preferences",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column(
        "user_id",
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    ),
    sa.Column("notification_enabled", sa.Boolean, default=True, nullable=False),
    sa.Column("disaster_categories", disaster_categories_type, default=list, nullable=False),
    sa.Column("alert_threshold_distance_km", sa.Float, default=100.0, nullable=False),
    sa.Column("timezone", sa.String, default="UTC", nullable=False),
)

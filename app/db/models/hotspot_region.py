import sqlalchemy as sa

from app.db.models.base import metadata

hotspot_regions_table = sa.Table(
    "hotspot_regions",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("region_key", sa.String, nullable=False, unique=True),
    sa.Column("center_latitude", sa.Float, nullable=False),
    sa.Column("center_longitude", sa.Float, nullable=False),
    sa.Column("event_count", sa.Integer, nullable=False),
    sa.Column("weighted_score", sa.Float, nullable=False, index=True),
    sa.Column("severity", sa.String, nullable=False),
    sa.Column("latest_event_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("event_ids", sa.JSON, nullable=False),
    sa.Column("lookback_days", sa.Integer, nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

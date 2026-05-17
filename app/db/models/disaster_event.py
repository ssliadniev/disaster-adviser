import sqlalchemy as sa

from app.db.models.base import metadata

disaster_events_table = sa.Table(
    "disaster_events",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("external_event_id", sa.String, nullable=False),
    sa.Column("title", sa.String, nullable=False),
    sa.Column("category", sa.String, nullable=False),
    sa.Column("latitude", sa.Float, nullable=False),
    sa.Column("longitude", sa.Float, nullable=False),
    sa.Column("event_date", sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column("source", sa.String, nullable=False),
    sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.UniqueConstraint(
        "external_event_id",
        "source",
        name="uq_disaster_events_external_source",
    ),
)

import sqlalchemy as sa

from app.db.models.base import metadata

travel_plans_table = sa.Table(
    "travel_plans",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    sa.Column("event_id", sa.String, nullable=False, index=True),
    sa.Column("calendar_id", sa.String, nullable=False, default="primary"),
    sa.Column("event_summary", sa.String, nullable=False),
    sa.Column("location_name", sa.String, nullable=True),
    sa.Column("latitude", sa.Float, nullable=True),
    sa.Column("longitude", sa.Float, nullable=True),
    sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
    sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.UniqueConstraint("user_id", "event_id", name="uq_user_event"),
)
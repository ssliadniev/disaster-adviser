import sqlalchemy as sa

from app.db.models.base import metadata

notifications_table = sa.Table(
    "notifications",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column(
        "user_id",
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    sa.Column(
        "travel_plan_id",
        sa.Integer,
        sa.ForeignKey("travel_plans.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    ),
    sa.Column("kind", sa.String, nullable=False),
    sa.Column("source_key", sa.String, nullable=False),
    sa.Column("severity", sa.String, nullable=False),
    sa.Column("risk_score", sa.Float, nullable=False),
    sa.Column("subject", sa.String, nullable=False),
    sa.Column("body", sa.Text, nullable=False),
    sa.Column("recipient_email", sa.String, nullable=False),
    sa.Column("disaster_event_id", sa.String, nullable=True),
    sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    ),
    sa.UniqueConstraint(
        "user_id",
        "travel_plan_id",
        "kind",
        "source_key",
        name="uq_notifications_user_plan_kind_source",
    ),
)

import sqlalchemy as sa

from app.db.models.base import metadata

webhook_channels_table = sa.Table(
    "webhook_channels",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("channel_id", sa.String, unique=True, nullable=False, index=True),
    sa.Column(
        "user_id",
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("calendar_id", sa.String, nullable=False),
    sa.Column("webhook_url", sa.String, nullable=False),
    sa.Column("resource_id", sa.String, nullable=True),
    sa.Column("expiration", sa.BigInteger, nullable=True),
    sa.Column("is_active", sa.Boolean, default=True, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
)

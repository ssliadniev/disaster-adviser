import sqlalchemy as sa

from app.db.models.base import metadata

oauth_accounts_table = sa.Table(
    "oauth_accounts",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    sa.Column("provider", sa.String, nullable=False),
    sa.Column("provider_user_id", sa.String, nullable=False),
    sa.Column("access_token", sa.Text, nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

    sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
)
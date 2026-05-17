import sqlalchemy as sa

from app.db.models.base import metadata

users_table = sa.Table(
    "users",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("email", sa.String, unique=True, index=True, nullable=False),
    sa.Column("hashed_password", sa.String, nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

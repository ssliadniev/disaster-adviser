"""create disaster events and hotspot regions tables

Revision ID: 0f5f2cbf6921
Revises: 7e1f3f52c2c4
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0f5f2cbf6921"
down_revision = "7e1f3f52c2c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "disaster_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_event_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "external_event_id",
            "source",
            name="uq_disaster_events_external_source",
        ),
    )
    op.create_index(
        op.f("ix_disaster_events_event_date"),
        "disaster_events",
        ["event_date"],
        unique=False,
    )

    op.create_table(
        "hotspot_regions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("region_key", sa.String(), nullable=False, unique=True),
        sa.Column("center_latitude", sa.Float(), nullable=False),
        sa.Column("center_longitude", sa.Float(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("weighted_score", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("latest_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_ids", sa.JSON(), nullable=False),
        sa.Column("lookback_days", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        op.f("ix_hotspot_regions_weighted_score"),
        "hotspot_regions",
        ["weighted_score"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_hotspot_regions_weighted_score"), table_name="hotspot_regions")
    op.drop_table("hotspot_regions")
    op.drop_index(op.f("ix_disaster_events_event_date"), table_name="disaster_events")
    op.drop_table("disaster_events")

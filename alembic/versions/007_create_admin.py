"""007_create_admin

Block 8: Admin Panel
Creates: system_settings, banners tables with default settings

Revision ID: 007_create_admin
Revises: 006_create_wallet
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "007_create_admin"
down_revision: str = "006_create_wallet"
branch_labels = None
depends_on    = None

DEFAULT_SETTINGS = [
    ("commission_rate",         "0.15"),
    ("registration_fee",        "5000"),
    ("extra_slot_price",        "50"),
    ("free_shipping_threshold", "5000"),
    ("standard_shipping_fee",   "200"),
    ("cod_timeout_minutes",     "30"),
    ("wallet_hold_days",        "3"),
]


def upgrade() -> None:
    # system_settings
    op.create_table(
        "system_settings",
        sa.Column("key",        sa.String(100), primary_key=True),
        sa.Column("value",      sa.Text,        nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # Seed default settings
    op.bulk_insert(
        sa.table(
            "system_settings",
            sa.column("key",   sa.String),
            sa.column("value", sa.Text),
        ),
        [{"key": k, "value": v} for k, v in DEFAULT_SETTINGS],
    )

    # banners
    op.create_table(
        "banners",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("title",       sa.String(200), nullable=False),
        sa.Column("image_url",   sa.String(500), nullable=False),
        sa.Column("link_url",    sa.String(500), nullable=True),
        sa.Column("position",    sa.String(50),  nullable=False),
        sa.Column("sort_order",  sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("is_active",   sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("valid_from",  sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("valid_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at",  sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at",  sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_banners_position",  "banners", ["position"])
    op.create_index("ix_banners_is_active", "banners", ["is_active"])


def downgrade() -> None:
    op.drop_table("banners")
    op.drop_table("system_settings")
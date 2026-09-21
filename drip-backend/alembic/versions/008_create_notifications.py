"""008_create_notifications

Block 9: Notifications
Creates: notifications, notification_preferences, email_log

Revision ID: 008_create_notifications
Revises: 007_create_admin
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008_create_notifications"
down_revision: str = "007_create_admin"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # notifications
    op.create_table(
        "notifications",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type",       sa.String(50),  nullable=False),
        sa.Column("title",      sa.String(200), nullable=False),
        sa.Column("body",       sa.Text,        nullable=False),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("is_read",    sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_notifications_user_id",  "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read",  "notifications", ["is_read"])
    op.create_index("ix_notifications_created_at","notifications", ["created_at"])

    # notification_preferences
    op.create_table(
        "notification_preferences",
        sa.Column("user_id",                  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("order_updates_email",      sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("order_updates_push",       sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("promotions_email",         sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("payout_notifications",     sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("new_review_notifications", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("low_stock_alerts",         sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at",               sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # email_log
    op.create_table(
        "email_log",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("recipient_email", sa.String(254), nullable=False),
        sa.Column("subject",         sa.String(500), nullable=False),
        sa.Column("template_id",     sa.String(100), nullable=True),
        sa.Column("status",          sa.String(20),  nullable=False),
        sa.Column("resend_id",       sa.String(255), nullable=True),
        sa.Column("error_message",   sa.Text,        nullable=True),
        sa.Column("sent_at",         sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_email_log_recipient", "email_log", ["recipient_email"])
    op.create_index("ix_email_log_sent_at",   "email_log", ["sent_at"])


def downgrade() -> None:
    op.drop_table("email_log")
    op.drop_table("notification_preferences")
    op.drop_table("notifications")
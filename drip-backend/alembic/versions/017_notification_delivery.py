"""Add durable notification delivery and canonical preference fields.

Revision ID: 017
Revises: 016
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_preferences",
        sa.Column("email_new_arrivals", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "notification_preferences",
        sa.Column("sms_order_updates", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "notification_preferences",
        sa.Column("whatsapp_order_updates", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column("email_log", sa.Column("delivery_key", sa.String(255), nullable=True))
    op.add_column(
        "email_log", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_unique_constraint("uq_email_log_delivery_key", "email_log", ["delivery_key"])

    op.create_table(
        "notification_outbox",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_key", sa.String(255), nullable=False),
        sa.Column("task_name", sa.String(100), nullable=False),
        sa.Column("args", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("event_key", name="uq_notification_outbox_event_key"),
    )
    op.create_index(
        "ix_notification_outbox_pending",
        "notification_outbox",
        ["published_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_pending", table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_constraint("uq_email_log_delivery_key", "email_log", type_="unique")
    op.drop_column("email_log", "attempts")
    op.drop_column("email_log", "delivery_key")
    op.drop_column("notification_preferences", "whatsapp_order_updates")
    op.drop_column("notification_preferences", "sms_order_updates")
    op.drop_column("notification_preferences", "email_new_arrivals")

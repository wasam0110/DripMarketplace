"""005_create_payments

Block 6: Payments
Creates: payment_status enum, payments, payment_callbacks, refunds

Revision ID: 005_create_payments
Revises: 004_create_orders
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005_create_payments"
down_revision: str = "004_create_orders"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    bind = op.get_bind()

    postgresql.ENUM(
        "pending", "processing", "completed", "failed", "refunded",
        name="payment_status",
    ).create(bind, checkfirst=True)

    # payments
    op.create_table(
        "payments",
        sa.Column("id",                postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id",          postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("method",            sa.String(20),  nullable=False),
        sa.Column("status",            sa.Enum("pending","processing","completed","failed","refunded",
                  name="payment_status", create_type=False), nullable=False, server_default="pending"),
        sa.Column("amount",            sa.Numeric(12, 2), nullable=False),
        sa.Column("currency",          sa.String(3),   nullable=False, server_default="PKR"),
        sa.Column("gateway_reference", sa.String(255), nullable=True),
        sa.Column("gateway_payload",   postgresql.JSONB, nullable=True),
        sa.Column("failure_reason",    sa.String(500), nullable=True),
        sa.Column("paid_at",           sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at",        sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_payments_order", "payments", ["order_id"])
    op.create_index("ix_payments_status",  "payments", ["status"])
    op.create_index("ix_payments_gateway_reference", "payments", ["gateway_reference"])

    # payment_callbacks
    op.create_table(
        "payment_callbacks",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("payment_id",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("gateway",     sa.String(50),   nullable=False),
        sa.Column("raw_payload", postgresql.JSONB, nullable=False),
        sa.Column("is_verified", sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("received_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # refunds (return_id FK added in Block 10)
    op.create_table(
        "refunds",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("payment_id",   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("return_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount",       sa.Numeric(12, 2), nullable=False),
        sa.Column("reason",       sa.Text,         nullable=True),
        sa.Column("gateway_ref",  sa.String(255),  nullable=True),
        sa.Column("processed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at",   sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_check_constraint("ck_refunds_amount_positive", "refunds", "amount > 0")


def downgrade() -> None:
    op.drop_table("refunds")
    op.drop_table("payment_callbacks")
    op.drop_table("payments")
    op.execute("DROP TYPE IF EXISTS payment_status")
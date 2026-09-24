"""Marketplace fixes: authentication versions, refunds, settlement release and analytics.

Revision ID: 012_marketplace_gaps
Revises: 011_create_reviews
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "012_marketplace_gaps"
down_revision = "011_create_reviews"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payouts", sa.Column("transfer_reference", sa.String(255), nullable=True))
    op.add_column("sellers", sa.Column("registration_payment_reference", sa.String(255), nullable=True))
    op.add_column("sellers", sa.Column("registration_paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sellers", sa.Column("registration_paid_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("refunds", sa.Column("idempotency_key", sa.String(100), nullable=True))
    op.create_unique_constraint("uq_refund_request_key", "refunds", ["payment_id", "idempotency_key"])
    op.add_column("commission_ledger", sa.Column("released_at", sa.DateTime(timezone=True), nullable=True))
    # Old releases had no ledger reference. Do not risk releasing those earnings twice.
    # Reconcile legacy pending balances before deliberately reopening any historic entry.
    op.execute("UPDATE commission_ledger SET released_at = settled_at")
    op.create_table("review_votes",
        sa.Column("review_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("helpful", sa.Boolean(), nullable=False))
    op.create_table("analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL")),
        sa.Column("query", sa.String(200)),
        sa.Column("result_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_analytics_events_kind_time", "analytics_events", ["kind", "created_at"])


def downgrade():
    op.drop_column("payouts", "transfer_reference")
    op.drop_column("sellers", "registration_paid_by")
    op.drop_column("sellers", "registration_paid_at")
    op.drop_column("sellers", "registration_payment_reference")
    op.drop_table("review_votes")
    op.drop_table("analytics_events")
    op.drop_column("commission_ledger", "released_at")
    op.drop_constraint("uq_refund_request_key", "refunds", type_="unique")
    op.drop_column("refunds", "idempotency_key")
    op.drop_column("users", "auth_version")

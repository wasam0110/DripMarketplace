"""006_create_wallet

Block 7: Wallet & Commission
Creates: wallet_tx_type, payout_status enums,
         payouts, commission_ledger, wallet_transactions

Revision ID: 006_create_wallet
Revises: 005_create_payments
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006_create_wallet"
down_revision: str = "005_create_payments"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    bind = op.get_bind()

    for name, values in [
        ("wallet_tx_type", [
            "credit_commission","debit_commission","credit_refund",
            "debit_withdrawal","credit_adjustment","debit_adjustment",
        ]),
        ("payout_status", ["requested","approved","processing","completed","rejected"]),
    ]:
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)

    # payouts (must come before wallet_transactions)
    op.create_table(
        "payouts",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("seller_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sellers.id"), nullable=False),
        sa.Column("amount",         sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", sa.String(50),  nullable=False),
        sa.Column("payment_detail", sa.String(255), nullable=False),
        sa.Column("status",         sa.Enum(
            "requested","approved","processing","completed","rejected",
            name="payout_status", create_type=False,
        ), nullable=False, server_default="requested"),
        sa.Column("admin_note",     sa.Text, nullable=True),
        sa.Column("approved_by",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("requested_at",   sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("completed_at",   sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_check_constraint("ck_payouts_amount_min", "payouts", "amount >= 500")
    op.create_index("ix_payouts_seller_id", "payouts", ["seller_id"])
    op.create_index("ix_payouts_status",    "payouts", ["status"])

    # commission_ledger
    op.create_table(
        "commission_ledger",
        sa.Column("id",                postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("seller_order_id",   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("seller_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("seller_id",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sellers.id"), nullable=False),
        sa.Column("gross_amount",      sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_rate",   sa.Numeric(5, 4),  nullable=False),
        sa.Column("commission_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("seller_amount",     sa.Numeric(12, 2), nullable=False),
        sa.Column("settled_at",        sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_commission_seller_order", "commission_ledger", ["seller_order_id"])
    op.create_check_constraint("ck_commission_amounts", "commission_ledger",
                               "commission_amount + seller_amount = gross_amount")

    # wallet_transactions
    op.create_table(
        "wallet_transactions",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("seller_id",       postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sellers.id"), nullable=False),
        sa.Column("type",            sa.Enum(
            "credit_commission","debit_commission","credit_refund",
            "debit_withdrawal","credit_adjustment","debit_adjustment",
            name="wallet_tx_type", create_type=False,
        ), nullable=False),
        sa.Column("amount",          sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_after",   sa.Numeric(12, 2), nullable=False),
        sa.Column("reference",       sa.String(255), nullable=True),
        sa.Column("seller_order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("seller_orders.id"), nullable=True),
        sa.Column("payout_id",       postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("payouts.id"), nullable=True),
        sa.Column("note",            sa.Text, nullable=True),
        sa.Column("created_at",      sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_wallet_transactions_seller_id", "wallet_transactions", ["seller_id"])


def downgrade() -> None:
    op.drop_table("wallet_transactions")
    op.drop_table("commission_ledger")
    op.drop_table("payouts")
    op.execute("DROP TYPE IF EXISTS wallet_tx_type")
    op.execute("DROP TYPE IF EXISTS payout_status")
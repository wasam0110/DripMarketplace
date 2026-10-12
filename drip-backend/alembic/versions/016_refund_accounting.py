"""Persist seller-specific refund allocation and net settlement accounting.

Revision ID: 016
Revises: 015
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


MONEY_COLUMNS = (
    "refunded_gross_amount",
    "reversed_commission_amount",
    "reversed_seller_amount",
    "recovered_seller_amount",
    "settlement_offset_amount",
    "platform_shortfall_amount",
)


def upgrade() -> None:
    for name in MONEY_COLUMNS:
        op.add_column(
            "commission_ledger",
            sa.Column(name, sa.Numeric(12, 2), nullable=False, server_default="0"),
        )
    op.create_check_constraint(
        "ck_commission_refund_amounts_nonnegative",
        "commission_ledger",
        "refunded_gross_amount >= 0 "
        "AND reversed_commission_amount >= 0 "
        "AND reversed_seller_amount >= 0 "
        "AND recovered_seller_amount >= 0 "
        "AND settlement_offset_amount >= 0 "
        "AND platform_shortfall_amount >= 0",
    )
    op.create_check_constraint(
        "ck_commission_refund_amounts_capped",
        "commission_ledger",
        "refunded_gross_amount <= gross_amount "
        "AND reversed_commission_amount <= commission_amount "
        "AND reversed_seller_amount <= seller_amount",
    )

    op.create_table(
        "refund_accounting",
        sa.Column(
            "refund_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("refunds.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("merchandise_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("shipping_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column(
            "commission_reversal_amount", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.Column("seller_reversal_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("recovered_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column(
            "settlement_offset_amount", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.Column(
            "platform_shortfall_amount", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.Column("platform_funded_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("reconciled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "merchandise_amount >= 0 AND shipping_amount >= 0 "
            "AND commission_reversal_amount >= 0 "
            "AND seller_reversal_amount >= 0 AND recovered_amount >= 0 "
            "AND settlement_offset_amount >= 0 AND platform_shortfall_amount >= 0 "
            "AND platform_funded_amount >= 0",
            name="ck_refund_accounting_nonnegative",
        ),
        sa.CheckConstraint(
            "seller_reversal_amount = recovered_amount "
            "+ settlement_offset_amount + platform_shortfall_amount",
            name="ck_refund_accounting_seller_conservation",
        ),
        sa.CheckConstraint(
            "platform_funded_amount = shipping_amount "
            "+ commission_reversal_amount + platform_shortfall_amount",
            name="ck_refund_accounting_platform_conservation",
        ),
    )

    op.create_table(
        "refund_allocations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "refund_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("refund_accounting.refund_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "seller_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("seller_orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "seller_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sellers.id"),
            nullable=False,
        ),
        sa.Column("merchandise_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "commission_reversal_amount", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.Column("seller_reversal_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("recovered_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column(
            "settlement_offset_amount", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.Column(
            "platform_shortfall_amount", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.Column("applied_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("refund_id", "seller_order_id", name="uq_refund_allocation_order"),
        sa.CheckConstraint(
            "merchandise_amount > 0 AND commission_reversal_amount >= 0 "
            "AND seller_reversal_amount >= 0 AND recovered_amount >= 0 "
            "AND settlement_offset_amount >= 0 AND platform_shortfall_amount >= 0",
            name="ck_refund_allocation_nonnegative",
        ),
        sa.CheckConstraint(
            "applied_at IS NULL OR commission_reversal_amount "
            "+ seller_reversal_amount = merchandise_amount",
            name="ck_refund_allocation_merchandise_conservation",
        ),
        sa.CheckConstraint(
            "seller_reversal_amount = recovered_amount "
            "+ settlement_offset_amount + platform_shortfall_amount",
            name="ck_refund_allocation_seller_conservation",
        ),
    )
    op.create_index(
        "ix_refund_allocations_seller_order_id",
        "refund_allocations",
        ["seller_order_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_refund_allocations_seller_order_id", table_name="refund_allocations")
    op.drop_table("refund_allocations")
    op.drop_table("refund_accounting")
    op.drop_constraint(
        "ck_commission_refund_amounts_capped", "commission_ledger", type_="check"
    )
    op.drop_constraint(
        "ck_commission_refund_amounts_nonnegative", "commission_ledger", type_="check"
    )
    for name in reversed(MONEY_COLUMNS):
        op.drop_column("commission_ledger", name)

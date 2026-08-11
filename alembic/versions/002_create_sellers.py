"""002_create_sellers

Block 3: Sellers & Slots
Creates: seller_status enum, sellers, seller_wallets, seller_bank_accounts

Revision ID: 002_create_sellers
Revises: 001_create_users
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_create_sellers"
down_revision: str = "001"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # seller_status enum
    seller_status = postgresql.ENUM(
        "pending_payment", "pending_approval", "active", "suspended", "rejected",
        name="seller_status",
    )
    seller_status.create(op.get_bind(), checkfirst=True)

    # sellers
    op.create_table(
        "sellers",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",          postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("brand_name",       sa.String(100),  nullable=False),
        sa.Column("slug",             sa.String(120),  nullable=False),
        sa.Column("description",      sa.Text,         nullable=True),
        sa.Column("logo_url",         sa.String(500),  nullable=True),
        sa.Column("brand_color",      sa.String(7),    nullable=False, server_default="#DFFF00"),
        sa.Column("return_policy",    sa.Text,         nullable=True),
        sa.Column("whatsapp_number",  sa.String(20),   nullable=True),
        sa.Column("instagram_handle", sa.String(100),  nullable=True),
        sa.Column("status",           sa.Enum(
            "pending_payment", "pending_approval", "active", "suspended", "rejected",
            name="seller_status", create_type=False,
        ), nullable=False, server_default="pending_payment"),
        sa.Column("total_slots",      sa.Integer(),    nullable=False, server_default="50"),
        sa.Column("slots_used",       sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("registration_fee", sa.Numeric(10, 2), nullable=False, server_default="5000.00"),
        sa.Column("rejected_reason",  sa.Text,         nullable=True),
        sa.Column("approved_by",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at",      sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at",       sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at",       sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("deleted_at",       sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_sellers_user_id",    "sellers", ["user_id"])
    op.create_unique_constraint("uq_sellers_brand_name", "sellers", ["brand_name"])
    op.create_unique_constraint("uq_sellers_slug",       "sellers", ["slug"])
    op.create_check_constraint("ck_sellers_slots_used_lte_total", "sellers", "slots_used <= total_slots")
    op.create_check_constraint("ck_sellers_slots_used_gte_zero",  "sellers", "slots_used >= 0")
    op.create_check_constraint("ck_sellers_total_slots_positive", "sellers", "total_slots >= 50")
    op.create_index("ix_sellers_user_id", "sellers", ["user_id"])
    op.create_index("ix_sellers_status",  "sellers", ["status"])
    op.create_index("ix_sellers_slug",    "sellers", ["slug"])

    # seller_wallets
    op.create_table(
        "seller_wallets",
        sa.Column("id",                postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("seller_id",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sellers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("available_balance", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("pending_balance",   sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("total_earned",      sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("total_commission",  sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("updated_at",        sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_seller_wallets_seller", "seller_wallets", ["seller_id"])
    op.create_check_constraint("ck_wallet_available_gte_zero", "seller_wallets", "available_balance >= 0")
    op.create_check_constraint("ck_wallet_pending_gte_zero",   "seller_wallets", "pending_balance >= 0")

    # seller_bank_accounts
    op.create_table(
        "seller_bank_accounts",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("seller_id",        postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bank_name",        sa.String(100), nullable=True),
        sa.Column("account_title",    sa.String(200), nullable=True),
        sa.Column("account_number",   sa.String(50),  nullable=True),
        sa.Column("jazzcash_number",  sa.String(20),  nullable=True),
        sa.Column("easypaisa_number", sa.String(20),  nullable=True),
        sa.Column("is_default",       sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("created_at",       sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_seller_bank_accounts_seller_id", "seller_bank_accounts", ["seller_id"])


def downgrade() -> None:
    op.drop_table("seller_bank_accounts")
    op.drop_table("seller_wallets")
    op.drop_table("sellers")
    op.execute("DROP TYPE IF EXISTS seller_status")
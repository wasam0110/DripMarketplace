"""004_create_orders

Block 5: Cart & Orders
Creates: discount_type, order_status, payment_method, seller_order_status enums,
         coupons, orders, order_addresses, order_items, seller_orders,
         order_status_history, coupon_usages

Revision ID: 004_create_orders
Revises: 003_create_products
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_create_orders"
down_revision: str = "003_create_products"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    bind = op.get_bind()

    # Enums (checkfirst=True — may already exist in Supabase)
    for enum_name, values in [
        ("discount_type",       ["percentage", "fixed"]),
        ("order_status",        ["pending_payment","payment_confirmed","pending_cod_verification",
                                 "processing","shipped","delivered","completed","cancelled","refunded"]),
        ("payment_method",      ["jazzcash","easypaisa","card","cod"]),
        ("seller_order_status", ["pending","processing","shipped","delivered","cancelled","returned"]),
    ]:
        postgresql.ENUM(*values, name=enum_name).create(bind, checkfirst=True)

    # coupons (must come before orders FK)
    op.create_table(
        "coupons",
        sa.Column("id",                    postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("code",                  sa.String(30),  nullable=False),
        sa.Column("discount_type",         sa.Enum("percentage","fixed", name="discount_type", create_type=False), nullable=False),
        sa.Column("discount_value",        sa.Numeric(10,2), nullable=False),
        sa.Column("min_order_amount",      sa.Numeric(10,2), nullable=False, server_default="0"),
        sa.Column("max_uses",              sa.Integer(), nullable=True),
        sa.Column("max_uses_per_customer", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("uses_count",            sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_from",            sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("valid_until",           sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active",             sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at",            sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_coupons_code", "coupons", ["code"])
    op.create_check_constraint("ck_coupons_pct_max",       "coupons", "discount_type != 'percentage' OR discount_value <= 70")
    op.create_check_constraint("ck_coupons_fixed_positive","coupons", "discount_value > 0")

    # orders
    op.create_table(
        "orders",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",         postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_number",    sa.String(20),  nullable=False),
        sa.Column("status",          sa.Enum("pending_payment","payment_confirmed","pending_cod_verification","processing","shipped","delivered","completed","cancelled","refunded", name="order_status", create_type=False), nullable=False, server_default="pending_payment"),
        sa.Column("guest_email",     sa.String(254), nullable=True),
        sa.Column("guest_name",      sa.String(200), nullable=True),
        sa.Column("guest_phone",     sa.String(20),  nullable=True),
        sa.Column("subtotal",        sa.Numeric(12,2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12,2), nullable=False, server_default="0"),
        sa.Column("shipping_fee",    sa.Numeric(10,2), nullable=False, server_default="200"),
        sa.Column("total",           sa.Numeric(12,2), nullable=False),
        sa.Column("payment_method",  sa.Enum("jazzcash","easypaisa","card","cod", name="payment_method", create_type=False), nullable=False),
        sa.Column("coupon_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("coupons.id"), nullable=True),
        sa.Column("notes",           sa.Text, nullable=True),
        sa.Column("created_at",      sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",      sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_orders_number",      "orders", ["order_number"])
    op.create_check_constraint("ck_orders_total_positive","orders", "total > 0")
    op.create_check_constraint("ck_orders_user_or_guest", "orders", "user_id IS NOT NULL OR guest_email IS NOT NULL")
    op.create_index("ix_orders_user_id",      "orders", ["user_id"])
    op.create_index("ix_orders_status",       "orders", ["status"])
    op.create_index("ix_orders_order_number", "orders", ["order_number"])

    # order_addresses
    op.create_table(
        "order_addresses",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_name", sa.String(200), nullable=False),
        sa.Column("phone",          sa.String(20),  nullable=False),
        sa.Column("street",         sa.String(500), nullable=False),
        sa.Column("city",           sa.String(100), nullable=False),
        sa.Column("province",       sa.String(100), nullable=False),
        sa.Column("note",           sa.Text, nullable=True),
    )
    op.create_unique_constraint("uq_order_addresses_order", "order_addresses", ["order_id"])

    # order_items
    op.create_table(
        "order_items",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id",      postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id",            ondelete="RESTRICT"), nullable=False),
        sa.Column("seller_id",     postgresql.UUID(as_uuid=True), sa.ForeignKey("sellers.id"),           nullable=False),
        sa.Column("product_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"),          nullable=False),
        sa.Column("variant_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id"),  nullable=False),
        sa.Column("product_name",  sa.String(200), nullable=False),
        sa.Column("variant_label", sa.String(100), nullable=False),
        sa.Column("unit_price",    sa.Numeric(10,2), nullable=False),
        sa.Column("quantity",      sa.Integer(), nullable=False),
        sa.Column("subtotal",      sa.Numeric(12,2), nullable=False),
    )
    op.create_check_constraint("ck_order_items_qty_positive", "order_items", "quantity > 0")
    op.create_index("ix_order_items_order_id",  "order_items", ["order_id"])
    op.create_index("ix_order_items_seller_id", "order_items", ["seller_id"])

    # seller_orders
    op.create_table(
        "seller_orders",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id",        postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("seller_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("sellers.id"), nullable=False),
        sa.Column("status",          sa.Enum("pending","processing","shipped","delivered","cancelled","returned", name="seller_order_status", create_type=False), nullable=False, server_default="pending"),
        sa.Column("subtotal",        sa.Numeric(12,2), nullable=False),
        sa.Column("tracking_number", sa.String(100), nullable=True),
        sa.Column("courier_name",    sa.String(100), nullable=True),
        sa.Column("shipped_at",      sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("delivered_at",    sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at",      sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",      sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_seller_orders_seller_id", "seller_orders", ["seller_id"])
    op.create_index("ix_seller_orders_order_id",  "seller_orders", ["order_id"])

    # order_status_history
    op.create_table(
        "order_status_history",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id",        postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"),        nullable=True),
        sa.Column("seller_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seller_orders.id"), nullable=True),
        sa.Column("old_status",      sa.String(50), nullable=True),
        sa.Column("new_status",      sa.String(50), nullable=False),
        sa.Column("changed_by",      postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("note",            sa.Text, nullable=True),
        sa.Column("created_at",      sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # coupon_usages
    op.create_table(
        "coupon_usages",
        sa.Column("id",        postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("coupon_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("coupons.id"), nullable=False),
        sa.Column("user_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"),   nullable=False),
        sa.Column("order_id",  postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"),  nullable=False),
        sa.Column("used_at",   sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_coupon_user_order", "coupon_usages", ["coupon_id", "order_id"])


def downgrade() -> None:
    op.drop_table("coupon_usages")
    op.drop_table("order_status_history")
    op.drop_table("seller_orders")
    op.drop_table("order_items")
    op.drop_table("order_addresses")
    op.drop_table("orders")
    op.drop_table("coupons")
    for name in ("seller_order_status","payment_method","order_status","discount_type"):
        op.execute(f"DROP TYPE IF EXISTS {name}")
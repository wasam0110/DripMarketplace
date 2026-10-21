"""Persist successful checkout keys atomically with their orders."""

import sqlalchemy as sa
from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("checkout_key_hash", sa.String(64), nullable=True))
    op.add_column("orders", sa.Column("checkout_request_hash", sa.String(64), nullable=True))
    op.create_index("uq_orders_checkout_key_hash", "orders", ["checkout_key_hash"], unique=True)
    op.create_check_constraint(
        "ck_orders_checkout_hash_pair",
        "orders",
        "(checkout_key_hash IS NULL) = (checkout_request_hash IS NULL)",
    )


def downgrade() -> None:
    # Operationally, stop order creation before downgrade: it removes replay protection.
    op.drop_constraint("ck_orders_checkout_hash_pair", "orders", type_="check")
    op.drop_index("uq_orders_checkout_key_hash", table_name="orders")
    op.drop_column("orders", "checkout_request_hash")
    op.drop_column("orders", "checkout_key_hash")

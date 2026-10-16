"""Persist variant reorder thresholds; existing variants retain threshold five.

Revision ID: 018
Revises: 017
Downgrade discards custom thresholds; export them before any rollback.
"""

import sqlalchemy as sa
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_inventory", sa.Column(
        "reorder_point", sa.Integer(), nullable=False, server_default="5",
    ))
    op.create_check_constraint(
        "ck_inventory_reorder_point", "product_inventory", "reorder_point BETWEEN 0 AND 999999",
    )


def downgrade() -> None:
    op.drop_constraint("ck_inventory_reorder_point", "product_inventory", type_="check")
    op.drop_column("product_inventory", "reorder_point")

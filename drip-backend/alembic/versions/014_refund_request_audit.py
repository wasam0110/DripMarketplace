"""Preserve refund requester identity and index admin refund reads.

Revision ID: 014
Revises: 013
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refunds",
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_refunds_requested_by_users",
        "refunds",
        "users",
        ["requested_by"],
        ["id"],
    )
    # Older rows stored the latest admin actor only. Preserve that value as the
    # best available requester identity; exact historical role separation is unknowable.
    op.execute("UPDATE refunds SET requested_by = processed_by WHERE processed_by IS NOT NULL")
    op.create_index("ix_refunds_payment_id", "refunds", ["payment_id"])
    op.create_index("ix_refunds_processed_at", "refunds", ["processed_at"])


def downgrade() -> None:
    op.drop_index("ix_refunds_processed_at", table_name="refunds")
    op.drop_index("ix_refunds_payment_id", table_name="refunds")
    op.drop_constraint("fk_refunds_requested_by_users", "refunds", type_="foreignkey")
    op.drop_column("refunds", "requested_by")

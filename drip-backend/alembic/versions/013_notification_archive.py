"""Add notification read timestamps and archive state.

Revision ID: 013
Revises: 012
"""

from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012_marketplace_gaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("read_at", sa.DateTime(timezone=True)))
    op.add_column(
        "notifications",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # The original read time is unknown. Start the timestamp at migration time.
    op.execute("UPDATE notifications SET read_at = now() WHERE is_read = true")


def downgrade() -> None:
    op.drop_column("notifications", "is_archived")
    op.drop_column("notifications", "read_at")

"""Allow capability-authorized guest returns.

Revision ID: 015
Revises: 014
"""

from alembic import op
from sqlalchemy.dialects import postgresql

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "returns",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    # PostgreSQL deliberately refuses this downgrade while guest-return rows exist;
    # operators must reconcile those records instead of silently deleting them.
    op.alter_column(
        "returns",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

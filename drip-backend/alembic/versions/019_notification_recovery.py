"""Track delivery completion and one-time legacy preference import.

Existing published events become eligible for idempotent recovery, not assumed sent.
Downgrade loses delivery/import bookkeeping; drain workers and export it first.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notification_preferences", sa.Column(
        "legacy_imported", sa.Boolean(), nullable=False, server_default="false"))
    for name in ("completed_at", "dead_lettered_at"):
        op.add_column("notification_outbox", sa.Column(name, sa.DateTime(timezone=True)))
    op.add_column("notification_outbox", sa.Column(
        "delivery_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("notification_outbox", sa.Column(
        "replay_history", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.create_index("ix_notification_outbox_recovery", "notification_outbox",
                    ["completed_at", "dead_lettered_at", "published_at"])


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_recovery", table_name="notification_outbox")
    for name in ("replay_history", "delivery_attempts", "dead_lettered_at", "completed_at"):
        op.drop_column("notification_outbox", name)
    op.drop_column("notification_preferences", "legacy_imported")

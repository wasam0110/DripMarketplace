"""009_create_returns

Block 10: Returns & Disputes
Creates: return_status, dispute_status enums,
         returns, return_items, disputes, dispute_messages
Also adds return_id FK to refunds table (deferred from Block 6).

Revision ID: 009_create_returns
Revises: 008_create_notifications
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "009_create_returns"
down_revision: str = "008_create_notifications"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    bind = op.get_bind()

    for name, values in [
        ("return_status", ["requested", "approved", "rejected", "received", "refunded"]),
        ("dispute_status", ["open", "under_review", "resolved_customer", "resolved_seller", "closed"]),
    ]:
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM pg_type "
                "WHERE typname = :name"
            ),
            {"name": name},
        ).scalar()

        if not exists:
            postgresql.ENUM(*values, name=name).create(bind)

    # returns
    op.create_table(
        "returns",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id",        postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("seller_order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("seller_orders.id"), nullable=False),
        sa.Column("user_id",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status",          sa.Enum(
            "requested","approved","rejected","received","refunded",
            name="return_status", create_type=False,
        ), nullable=False, server_default="requested"),
        sa.Column("reason",       sa.Text, nullable=False),
        sa.Column("notes",        sa.Text, nullable=True),
        sa.Column("requested_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("resolved_at",  sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_returns_user_id",   "returns", ["user_id"])
    op.create_index("ix_returns_order_id",  "returns", ["order_id"])
    op.create_index("ix_returns_status",    "returns", ["status"])

    # return_items
    op.create_table(
        "return_items",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("return_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("returns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("order_items.id"), nullable=False),
        sa.Column("quantity",      sa.Integer(), nullable=False),
        sa.Column("reason",        sa.Text, nullable=True),
    )
    op.create_index("ix_return_items_return_id", "return_items", ["return_id"])

    # disputes
    op.create_table(
        "disputes",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("return_id",       postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("returns.id"), nullable=False),
        sa.Column("seller_id",       postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sellers.id"), nullable=False),
        sa.Column("user_id",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status",          sa.Enum(
            "open","under_review","resolved_customer","resolved_seller","closed",
            name="dispute_status", create_type=False,
        ), nullable=False, server_default="open"),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.Column("resolved_by",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at",      sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("resolved_at",     sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_disputes_return_id", "disputes", ["return_id"])
    op.create_index("ix_disputes_status",    "disputes", ["status"])

    # dispute_messages
    op.create_table(
        "dispute_messages",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("dispute_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body",       sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_dispute_messages_dispute_id", "dispute_messages", ["dispute_id"])

    # Wire return_id FK on refunds (deferred from Block 6)
    op.create_foreign_key(
        "fk_refunds_return_id",
        "refunds", "returns",
        ["return_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_refunds_return_id", "refunds", type_="foreignkey")
    op.drop_table("dispute_messages")
    op.drop_table("disputes")
    op.drop_table("return_items")
    op.drop_table("returns")
    op.execute("DROP TYPE IF EXISTS dispute_status")
    op.execute("DROP TYPE IF EXISTS return_status")
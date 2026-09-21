from alembic import op

revision      = '010_payfast_methods'
down_revision = '009_create_returns'
branch_labels = None
depends_on    = None

def upgrade() -> None:
    op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'payfast'")

def downgrade() -> None:
    pass

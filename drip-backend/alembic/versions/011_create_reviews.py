from alembic import op

revision      = '011_create_reviews'
down_revision = '010_payfast_methods'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.execute("CREATE TYPE review_status AS ENUM ('pending', 'approved', 'rejected', 'hidden')")
    op.execute("CREATE TABLE IF NOT EXISTS reviews (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE, order_id UUID REFERENCES orders(id) ON DELETE SET NULL, rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5), title VARCHAR(200), body TEXT, status review_status NOT NULL DEFAULT 'pending', is_verified_purchase BOOLEAN NOT NULL DEFAULT false, helpful_count INTEGER NOT NULL DEFAULT 0, unhelpful_count INTEGER NOT NULL DEFAULT 0, admin_note TEXT, moderated_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (user_id, product_id))")
    op.execute("CREATE TABLE IF NOT EXISTS review_images (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE, url VARCHAR(500) NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now())")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reviews_product_id ON reviews (product_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reviews_user_id ON reviews (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reviews_status ON reviews (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_review_images_review_id ON review_images (review_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS review_images")
    op.execute("DROP TABLE IF EXISTS reviews")
    op.execute("DROP TYPE IF EXISTS review_status")
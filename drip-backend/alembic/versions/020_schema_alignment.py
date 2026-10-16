"""Add the two indexes declared by models but absent from migrated databases."""

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_reviews_rating", "reviews", ["rating"])
    op.create_index("ix_sellers_deleted_at", "sellers", ["deleted_at"])
    # Refuse invalid historical rows instead of silently rewriting review data.
    op.create_check_constraint("ck_reviews_helpful_gte_0", "reviews", "helpful_count >= 0")
    op.create_check_constraint("ck_reviews_unhelpful_gte_0", "reviews", "unhelpful_count >= 0")
    op.create_check_constraint("ck_review_images_sort_gte_0", "review_images", "sort_order >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_review_images_sort_gte_0", "review_images", type_="check")
    op.drop_constraint("ck_reviews_unhelpful_gte_0", "reviews", type_="check")
    op.drop_constraint("ck_reviews_helpful_gte_0", "reviews", type_="check")
    op.drop_index("ix_sellers_deleted_at", table_name="sellers")
    op.drop_index("ix_reviews_rating", table_name="reviews")

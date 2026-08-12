"""003_create_products

Block 4: Products & Images
Creates: size_type enum, categories, products, product_images,
         product_variants, product_inventory, tags, product_tags

Revision ID: 003_create_products
Revises: 002_create_sellers
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_create_products"
down_revision: str = "002_create_sellers"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # size_type enum
    size_type_enum = postgresql.ENUM(
        "alpha", "numeric", "one_size", name="size_type"
    )
    size_type_enum.create(op.get_bind(), checkfirst=True)

    # categories
    op.create_table(
        "categories",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("parent_id",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("name",       sa.String(100), nullable=False),
        sa.Column("slug",       sa.String(120), nullable=False),
        sa.Column("image_url",  sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active",  sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_unique_constraint("uq_categories_slug", "categories", ["slug"])

    # products
    op.create_table(
        "products",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("seller_id",        postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sellers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("category_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("name",             sa.String(200),  nullable=False),
        sa.Column("slug",             sa.String(250),  nullable=False),
        sa.Column("description",      sa.Text,         nullable=True),
        sa.Column("price",            sa.Numeric(10,2), nullable=False),
        sa.Column("sale_price",       sa.Numeric(10,2), nullable=True),
        sa.Column("is_published",     sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("admin_hidden",     sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("meta_title",       sa.String(200),  nullable=True),
        sa.Column("meta_description", sa.String(500),  nullable=True),
        sa.Column("avg_rating",       sa.Numeric(3,2),  nullable=False, server_default="0.00"),
        sa.Column("review_count",     sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("view_count",       sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("created_at",       sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at",       sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("deleted_at",       sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_products_slug",          "products", ["slug"])
    op.create_check_constraint("ck_products_price_positive", "products", "price >= 100")
    op.create_check_constraint("ck_products_price_max",      "products", "price <= 500000")
    op.create_check_constraint("ck_products_sale_lt_price",  "products", "sale_price IS NULL OR sale_price < price")
    op.create_check_constraint("ck_products_rating_range",   "products", "avg_rating BETWEEN 0 AND 5")
    op.create_index("ix_products_seller_id",    "products", ["seller_id"])
    op.create_index("ix_products_category_id",  "products", ["category_id"])
    op.create_index("ix_products_is_published", "products", ["is_published"])
    op.create_index("ix_products_deleted_at",   "products", ["deleted_at"])

    # product_images
    op.create_table(
        "product_images",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url",        sa.String(500), nullable=False),
        sa.Column("alt_text",   sa.String(200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])

    # product_variants
    op.create_table(
        "product_variants",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku",            sa.String(100), nullable=False),
        sa.Column("size_type",      sa.Enum("alpha","numeric","one_size",
                  name="size_type", create_type=False), nullable=False),
        sa.Column("size_value",     sa.String(10),  nullable=False),
        sa.Column("colour",         sa.String(50),  nullable=False),
        sa.Column("price_override", sa.Numeric(10,2), nullable=True),
        sa.Column("is_active",      sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at",     sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_product_variants_sku",   "product_variants", ["sku"])
    op.create_unique_constraint("uq_product_variants_combo", "product_variants",
                                ["product_id", "size_value", "colour"])
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])

    # product_inventory
    op.create_table(
        "product_inventory",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stock",      sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved",   sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_inventory_variant",         "product_inventory", ["variant_id"])
    op.create_check_constraint("ck_inventory_stock_gte_zero",    "product_inventory", "stock >= 0")
    op.create_check_constraint("ck_inventory_reserved_gte_zero", "product_inventory", "reserved >= 0")
    op.create_check_constraint("ck_inventory_stock_gte_reserved","product_inventory", "stock >= reserved")

    # tags
    op.create_table(
        "tags",
        sa.Column("id",   postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(50), nullable=False),
    )
    op.create_unique_constraint("uq_tags_name", "tags", ["name"])

    # product_tags (association)
    op.create_table(
        "product_tags",
        sa.Column("product_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id",  ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tags.id",       ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("product_tags")
    op.drop_table("tags")
    op.drop_table("product_inventory")
    op.drop_table("product_variants")
    op.drop_table("product_images")
    op.drop_table("products")
    op.drop_table("categories")
    op.execute("DROP TYPE IF EXISTS size_type")
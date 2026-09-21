from __future__ import annotations

import enum
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    String, Text, Numeric, Boolean, Integer,
    DateTime, Enum as SAEnum, ForeignKey,
    Table, Column, CheckConstraint, UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.seller import Seller


# ── Association table (must be defined before Product and Tag) ─────────────────
product_tags = Table(
    "product_tags",
    Base.metadata,
    Column("product_id", ForeignKey("products.id",  ondelete="CASCADE"), primary_key=True),
    Column("tag_id",     ForeignKey("tags.id",       ondelete="CASCADE"), primary_key=True),
)


class SizeType(str, enum.Enum):
    alpha    = "alpha"
    numeric  = "numeric"
    one_size = "one_size"


class Category(Base):
    __tablename__ = "categories"

    id:         Mapped[UUID]       = mapped_column(primary_key=True, default=uuid4)
    parent_id:  Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    name:       Mapped[str]        = mapped_column(String(100))
    slug:       Mapped[str]        = mapped_column(String(120), unique=True)
    image_url:  Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int]        = mapped_column(Integer, default=0)
    is_active:  Mapped[bool]       = mapped_column(Boolean, default=True, server_default="true")

    parent:   Mapped["Category | None"] = relationship(
                  "Category", back_populates="children",
                  foreign_keys=[parent_id], remote_side="[Category.id]"
              )
    children: Mapped[list["Category"]]  = relationship(
                  "Category", back_populates="parent", foreign_keys=[parent_id]
              )
    products: Mapped[list["Product"]]   = relationship(back_populates="category")


class Product(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 100",                                  name="ck_products_price_positive"),
        CheckConstraint("price <= 500000",                               name="ck_products_price_max"),
        CheckConstraint("sale_price IS NULL OR sale_price < price",      name="ck_products_sale_lt_price"),
        CheckConstraint("avg_rating BETWEEN 0 AND 5",                    name="ck_products_rating_range"),
        Index("ix_products_seller_id",   "seller_id"),
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_is_published","is_published"),
        Index("ix_products_deleted_at",  "deleted_at"),
    )

    id:               Mapped[UUID]           = mapped_column(primary_key=True, default=uuid4)
    seller_id:        Mapped[UUID]           = mapped_column(ForeignKey("sellers.id", ondelete="RESTRICT"))
    category_id:      Mapped[UUID | None]    = mapped_column(ForeignKey("categories.id"))
    name:             Mapped[str]            = mapped_column(String(200))
    slug:             Mapped[str]            = mapped_column(String(250), unique=True)
    description:      Mapped[str | None]     = mapped_column(Text)
    price:            Mapped[Decimal]        = mapped_column(Numeric(10, 2))
    sale_price:       Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    is_published:     Mapped[bool]           = mapped_column(Boolean, default=False, server_default="false")
    admin_hidden:     Mapped[bool]           = mapped_column(Boolean, default=False, server_default="false")
    meta_title:       Mapped[str | None]     = mapped_column(String(200))
    meta_description: Mapped[str | None]     = mapped_column(String(500))
    avg_rating:       Mapped[Decimal]        = mapped_column(Numeric(3, 2), default=Decimal("0.00"), server_default="0.00")
    review_count:     Mapped[int]            = mapped_column(Integer, default=0, server_default="0")
    view_count:       Mapped[int]            = mapped_column(Integer, default=0, server_default="0")

    seller:   Mapped["Seller"]               = relationship(back_populates="products")
    category: Mapped["Category | None"]      = relationship(back_populates="products")
    images:   Mapped[list["ProductImage"]]   = relationship(
                  back_populates="product", cascade="all, delete-orphan",
                  order_by="ProductImage.sort_order"
              )
    variants: Mapped[list["ProductVariant"]] = relationship(
                  back_populates="product", cascade="all, delete-orphan"
              )
    tags:     Mapped[list["Tag"]]            = relationship(
                  secondary=product_tags, back_populates="products"
              )

    @property
    def effective_price(self) -> Decimal:
        return self.sale_price if self.sale_price else self.price

    @property
    def has_stock(self) -> bool:
        return any(
            (v.inventory.available_stock > 0)
            for v in self.variants
            if v.is_active and v.inventory
        )


class ProductImage(Base):
    __tablename__ = "product_images"

    id:         Mapped[UUID]       = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID]       = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    url:        Mapped[str]        = mapped_column(String(500))
    alt_text:   Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int]        = mapped_column(Integer, default=0, server_default="0")
    is_primary: Mapped[bool]       = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default="now()")

    product: Mapped["Product"] = relationship(back_populates="images")


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "size_value", "colour", name="uq_product_variants_combo"),
    )

    id:             Mapped[UUID]           = mapped_column(primary_key=True, default=uuid4)
    product_id:     Mapped[UUID]           = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    sku:            Mapped[str]            = mapped_column(String(100), unique=True)
    size_type:      Mapped[SizeType]       = mapped_column(
                        SAEnum(SizeType, name="size_type", create_type=False)
                    )
    size_value:     Mapped[str]            = mapped_column(String(10))
    colour:         Mapped[str]            = mapped_column(String(50))
    price_override: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    is_active:      Mapped[bool]           = mapped_column(Boolean, default=True, server_default="true")
    created_at:     Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default="now()")

    product:   Mapped["Product"]           = relationship(back_populates="variants")
    inventory: Mapped["ProductInventory"]  = relationship(
                   back_populates="variant", uselist=False, cascade="all, delete-orphan"
               )

    @property
    def effective_price(self) -> Decimal:
        return self.price_override if self.price_override else self.product.price


class ProductInventory(Base):
    __tablename__ = "product_inventory"
    __table_args__ = (
        CheckConstraint("stock >= 0",             name="ck_inventory_stock_gte_zero"),
        CheckConstraint("reserved >= 0",          name="ck_inventory_reserved_gte_zero"),
        CheckConstraint("stock >= reserved",      name="ck_inventory_stock_gte_reserved"),
    )

    id:         Mapped[UUID]     = mapped_column(primary_key=True, default=uuid4)
    variant_id: Mapped[UUID]     = mapped_column(
                    ForeignKey("product_variants.id", ondelete="CASCADE"), unique=True
                )
    stock:      Mapped[int]      = mapped_column(Integer, default=0, server_default="0")
    reserved:   Mapped[int]      = mapped_column(Integer, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    variant: Mapped["ProductVariant"] = relationship(back_populates="inventory")

    @property
    def available_stock(self) -> int:
        return self.stock - self.reserved


class Tag(Base):
    __tablename__ = "tags"

    id:   Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str]  = mapped_column(String(50), unique=True)

    products: Mapped[list["Product"]] = relationship(
                  secondary=product_tags, back_populates="tags"
              )
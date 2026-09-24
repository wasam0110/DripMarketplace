"""
app/models/review.py
────────────────────
Product review domain models.

Models:
  - Review        — customer review for a product
  - ReviewImage   — photos attached to a review
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product
    from app.models.order import Order


class ReviewStatus(str, enum.Enum):
    pending   = "pending"
    approved  = "approved"
    rejected  = "rejected"
    hidden    = "hidden"


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        # One review per customer per product
        UniqueConstraint("user_id", "product_id", name="uq_reviews_user_product"),
        # Rating must be 1–5
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),
        # Helpful counts must be non-negative
        CheckConstraint("helpful_count >= 0",     name="ck_reviews_helpful_gte_0"),
        CheckConstraint("unhelpful_count >= 0",   name="ck_reviews_unhelpful_gte_0"),
        Index("ix_reviews_product_id", "product_id"),
        Index("ix_reviews_user_id",    "user_id"),
        Index("ix_reviews_status",     "status"),
        Index("ix_reviews_rating",     "rating"),
    )

    id:              Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:         Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),    nullable=False)
    product_id:      Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    order_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id",  ondelete="SET NULL"), nullable=True)

    rating:          Mapped[int]              = mapped_column(Integer,      nullable=False)
    title:           Mapped[str | None]       = mapped_column(String(200),  nullable=True)
    body:            Mapped[str | None]       = mapped_column(Text,         nullable=True)

    status:          Mapped[ReviewStatus]     = mapped_column(
                         SAEnum(ReviewStatus, name="review_status", create_type=False),
                         nullable=False, default=ReviewStatus.pending, server_default="pending",
                     )
    is_verified_purchase: Mapped[bool]        = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    helpful_count:   Mapped[int]              = mapped_column(Integer, nullable=False, default=0, server_default="0")
    unhelpful_count: Mapped[int]              = mapped_column(Integer, nullable=False, default=0, server_default="0")

    admin_note:      Mapped[str | None]       = mapped_column(Text, nullable=True)
    moderated_at:    Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user:    Mapped["User"]           = relationship("User",    foreign_keys=[user_id],    lazy="selectin")
    product: Mapped["Product"]        = relationship("Product", foreign_keys=[product_id], lazy="selectin")
    order:   Mapped["Order | None"]   = relationship("Order",   foreign_keys=[order_id],   lazy="selectin")
    images:  Mapped[list["ReviewImage"]] = relationship(
                 "ReviewImage", back_populates="review",
                 cascade="all, delete-orphan", lazy="selectin", order_by="ReviewImage.sort_order",
             )


class ReviewImage(Base):
    __tablename__ = "review_images"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="ck_review_images_sort_gte_0"),
        Index("ix_review_images_review_id", "review_id"),
    )

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)
    url:        Mapped[str]       = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int]       = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    review: Mapped["Review"] = relationship(back_populates="images")


class ReviewVote(Base):
    __tablename__ = "review_votes"
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)

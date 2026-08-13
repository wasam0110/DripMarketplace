from __future__ import annotations

import enum
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    String, Numeric, Boolean, Integer,
    DateTime, Enum as SAEnum, ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DiscountType(str, enum.Enum):
    percentage = "percentage"
    fixed      = "fixed"


class Coupon(Base):
    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint(
            "discount_type != 'percentage' OR discount_value <= 70",
            name="ck_coupons_pct_max",
        ),
        CheckConstraint("discount_value > 0", name="ck_coupons_fixed_positive"),
    )

    id:                    Mapped[UUID]         = mapped_column(primary_key=True, default=uuid4)
    code:                  Mapped[str]          = mapped_column(String(30), unique=True)
    discount_type:         Mapped[DiscountType] = mapped_column(
                               SAEnum(DiscountType, name="discount_type", create_type=False)
                           )
    discount_value:        Mapped[Decimal]      = mapped_column(Numeric(10, 2))
    min_order_amount:      Mapped[Decimal]      = mapped_column(Numeric(10, 2), default=Decimal("0.00"), server_default="0")
    max_uses:              Mapped[int | None]   = mapped_column(Integer)
    max_uses_per_customer: Mapped[int]          = mapped_column(Integer, default=1, server_default="1")
    uses_count:            Mapped[int]          = mapped_column(Integer, default=0, server_default="0")
    valid_from:            Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until:           Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active:             Mapped[bool]         = mapped_column(Boolean, default=True, server_default="true")
    created_at:            Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default="now()")

    usages: Mapped[list["CouponUsage"]] = relationship(back_populates="coupon")


class CouponUsage(Base):
    __tablename__ = "coupon_usages"

    id:        Mapped[UUID]      = mapped_column(primary_key=True, default=uuid4)
    coupon_id: Mapped[UUID]      = mapped_column(ForeignKey("coupons.id"))
    user_id:   Mapped[UUID]      = mapped_column(ForeignKey("users.id"))
    order_id:  Mapped[UUID]      = mapped_column(ForeignKey("orders.id"))
    used_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default="now()")

    coupon: Mapped["Coupon"] = relationship(back_populates="usages")
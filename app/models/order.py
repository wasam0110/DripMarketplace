from __future__ import annotations

import enum
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    String, Text, Numeric, Integer, Boolean,
    DateTime, Enum as SAEnum, ForeignKey,
    CheckConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.seller import Seller
    from app.models.user import User
    from app.models.coupon import Coupon
    from app.models.product import Product, ProductVariant


class OrderStatus(str, enum.Enum):
    pending_payment          = "pending_payment"
    payment_confirmed        = "payment_confirmed"
    pending_cod_verification = "pending_cod_verification"
    processing               = "processing"
    shipped                  = "shipped"
    delivered                = "delivered"
    completed                = "completed"
    cancelled                = "cancelled"
    refunded                 = "refunded"


class PaymentMethod(str, enum.Enum):
    jazzcash  = "jazzcash"
    easypaisa = "easypaisa"
    card      = "card"
    cod       = "cod"


class SellerOrderStatus(str, enum.Enum):
    pending    = "pending"
    processing = "processing"
    shipped    = "shipped"
    delivered  = "delivered"
    cancelled  = "cancelled"
    returned   = "returned"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total > 0",                                    name="ck_orders_total_positive"),
        CheckConstraint("user_id IS NOT NULL OR guest_email IS NOT NULL", name="ck_orders_user_or_guest"),
        Index("ix_orders_user_id",     "user_id"),
        Index("ix_orders_status",      "status"),
        Index("ix_orders_order_number","order_number"),
    )

    id:              Mapped[UUID]           = mapped_column(primary_key=True, default=uuid4)
    user_id:         Mapped[UUID | None]    = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    order_number:    Mapped[str]            = mapped_column(String(20), unique=True)
    status:          Mapped[OrderStatus]    = mapped_column(
                         SAEnum(OrderStatus, name="order_status", create_type=False),
                         default=OrderStatus.pending_payment,
                     )
    guest_email:     Mapped[str | None]     = mapped_column(String(254))
    guest_name:      Mapped[str | None]     = mapped_column(String(200))
    guest_phone:     Mapped[str | None]     = mapped_column(String(20))
    subtotal:        Mapped[Decimal]        = mapped_column(Numeric(12, 2))
    discount_amount: Mapped[Decimal]        = mapped_column(Numeric(12, 2), default=Decimal("0.00"), server_default="0")
    shipping_fee:    Mapped[Decimal]        = mapped_column(Numeric(10, 2), default=Decimal("200.00"), server_default="200")
    total:           Mapped[Decimal]        = mapped_column(Numeric(12, 2))
    payment_method:  Mapped[PaymentMethod]  = mapped_column(
                         SAEnum(PaymentMethod, name="payment_method", create_type=False)
                     )
    coupon_id:       Mapped[UUID | None]    = mapped_column(ForeignKey("coupons.id"))
    notes:           Mapped[str | None]     = mapped_column(Text)

    user:         Mapped["User | None"]        = relationship(back_populates="orders")
    address:      Mapped["OrderAddress"]        = relationship(
                      back_populates="order", uselist=False, cascade="all, delete-orphan"
                  )
    items:        Mapped[list["OrderItem"]]     = relationship(
                      back_populates="order", cascade="all, delete-orphan"
                  )
    seller_orders: Mapped[list["SellerOrder"]]  = relationship(back_populates="order")
    coupon:        Mapped["Coupon | None"]       = relationship()


class OrderAddress(Base):
    __tablename__ = "order_addresses"

    id:             Mapped[UUID]      = mapped_column(primary_key=True, default=uuid4)
    order_id:       Mapped[UUID]      = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True)
    recipient_name: Mapped[str]       = mapped_column(String(200))
    phone:          Mapped[str]       = mapped_column(String(20))
    street:         Mapped[str]       = mapped_column(String(500))
    city:           Mapped[str]       = mapped_column(String(100))
    province:       Mapped[str]       = mapped_column(String(100))
    note:           Mapped[str | None] = mapped_column(Text)

    order: Mapped["Order"] = relationship(back_populates="address")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_qty_positive"),
    )

    id:            Mapped[UUID]    = mapped_column(primary_key=True, default=uuid4)
    order_id:      Mapped[UUID]    = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"))
    seller_id:     Mapped[UUID]    = mapped_column(ForeignKey("sellers.id"))
    product_id:    Mapped[UUID]    = mapped_column(ForeignKey("products.id"))
    variant_id:    Mapped[UUID]    = mapped_column(ForeignKey("product_variants.id"))
    product_name:  Mapped[str]     = mapped_column(String(200))   # snapshot
    variant_label: Mapped[str]     = mapped_column(String(100))   # e.g. "M / Black"
    unit_price:    Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity:      Mapped[int]     = mapped_column(Integer)
    subtotal:      Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order:   Mapped["Order"]  = relationship(back_populates="items")
    seller:  Mapped["Seller"] = relationship()
    product: Mapped["Product"] = relationship()
    variant: Mapped["ProductVariant"] = relationship()


class SellerOrder(Base, TimestampMixin):
    __tablename__ = "seller_orders"
    __table_args__ = (
        Index("ix_seller_orders_seller_id", "seller_id"),
        Index("ix_seller_orders_order_id",  "order_id"),
    )

    id:              Mapped[UUID]              = mapped_column(primary_key=True, default=uuid4)
    order_id:        Mapped[UUID]              = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"))
    seller_id:       Mapped[UUID]              = mapped_column(ForeignKey("sellers.id"))
    status:          Mapped[SellerOrderStatus] = mapped_column(
                         SAEnum(SellerOrderStatus, name="seller_order_status", create_type=False),
                         default=SellerOrderStatus.pending,
                     )
    subtotal:        Mapped[Decimal]           = mapped_column(Numeric(12, 2))
    tracking_number: Mapped[str | None]        = mapped_column(String(100))
    courier_name:    Mapped[str | None]        = mapped_column(String(100))
    shipped_at:      Mapped[datetime | None]   = mapped_column(DateTime(timezone=True))
    delivered_at:    Mapped[datetime | None]   = mapped_column(DateTime(timezone=True))

    order:  Mapped["Order"]  = relationship(back_populates="seller_orders")
    seller: Mapped["Seller"] = relationship(back_populates="seller_orders")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id:              Mapped[UUID]       = mapped_column(primary_key=True, default=uuid4)
    order_id:        Mapped[UUID | None] = mapped_column(ForeignKey("orders.id"))
    seller_order_id: Mapped[UUID | None] = mapped_column(ForeignKey("seller_orders.id"))
    old_status:      Mapped[str | None]  = mapped_column(String(50))
    new_status:      Mapped[str]         = mapped_column(String(50))
    changed_by:      Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    note:            Mapped[str | None]  = mapped_column(Text)
    created_at:      Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default="now()")
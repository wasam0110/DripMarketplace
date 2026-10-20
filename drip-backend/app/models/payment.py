"""models / payment.

SQLAlchemy persistence definitions shared by repositories and services.
"""

from __future__ import annotations

from sqlalchemy import Index as SchemaIndex

from sqlalchemy import text as sql_text

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PaymentStatus(str, enum.Enum):
    pending    = "pending"
    processing = "processing"
    completed  = "completed"
    failed     = "failed"
    refunded   = "refunded"


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        SchemaIndex("ix_payments_gateway_reference", "gateway_reference"),
        SchemaIndex("ix_payments_status", "status"),
    )

    id:                Mapped[UUID]              = mapped_column(primary_key=True, default=uuid4, server_default=sql_text("gen_random_uuid()"))
    order_id:          Mapped[UUID]              = mapped_column(
                           ForeignKey("orders.id", ondelete="RESTRICT"), unique=True
                       )
    method:            Mapped[str]               = mapped_column(String(20))
    status:            Mapped[PaymentStatus]     = mapped_column(
                           SAEnum(PaymentStatus, name="payment_status", create_type=False),
                           default=PaymentStatus.pending, server_default="pending",
                       )
    amount:            Mapped[Decimal]           = mapped_column(Numeric(12, 2))
    currency:          Mapped[str]               = mapped_column(String(3), default="PKR", server_default="PKR")
    gateway_reference: Mapped[str | None]        = mapped_column(String(255))
    gateway_payload:   Mapped[dict | None]       = mapped_column(JSONB)
    failure_reason:    Mapped[str | None]        = mapped_column(String(500))
    paid_at:           Mapped[datetime | None]   = mapped_column(DateTime(timezone=True))
    created_at:        Mapped[datetime]          = mapped_column(
                           DateTime(timezone=True), server_default="now()"
                       )

    order:     Mapped["Order"]              = relationship("Order")
    callbacks: Mapped[list["PaymentCallback"]] = relationship(
                   back_populates="payment", cascade="all, delete-orphan"
               )
    refunds:   Mapped[list["Refund"]]       = relationship(
                   back_populates="payment", cascade="all, delete-orphan"
               )


class PaymentCallback(Base):
    __tablename__ = "payment_callbacks"

    id:          Mapped[UUID]        = mapped_column(primary_key=True, default=uuid4, server_default=sql_text("gen_random_uuid()"))
    payment_id:  Mapped[UUID | None] = mapped_column(ForeignKey("payments.id"))
    gateway:     Mapped[str]         = mapped_column(String(50))
    raw_payload: Mapped[dict]        = mapped_column(JSONB)
    is_verified: Mapped[bool]        = mapped_column(Boolean, default=False, server_default="false")
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    payment: Mapped["Payment | None"] = relationship(back_populates="callbacks")


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_refunds_amount_positive"),
        UniqueConstraint("payment_id", "idempotency_key", name="uq_refund_request_key"),
        Index("ix_refunds_payment_id", "payment_id"),
        Index("ix_refunds_processed_at", "processed_at"),
    )

    id:           Mapped[UUID]       = mapped_column(primary_key=True, default=uuid4, server_default=sql_text("gen_random_uuid()"))
    payment_id:   Mapped[UUID]       = mapped_column(ForeignKey("payments.id"))
    # return_id FK added in Block 10 when returns table exists
    return_id:    Mapped[UUID | None] = mapped_column(ForeignKey("returns.id", name="fk_refunds_return_id"))
    idempotency_key: Mapped[str | None] = mapped_column(String(100))
    amount:       Mapped[Decimal]    = mapped_column(Numeric(12, 2))
    reason:       Mapped[str | None] = mapped_column(Text)
    gateway_ref:  Mapped[str | None] = mapped_column(String(255))
    requested_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    processed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    payment: Mapped["Payment"] = relationship(back_populates="refunds")
    accounting: Mapped["RefundAccounting | None"] = relationship(
        back_populates="refund", uselist=False
    )


if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.wallet import RefundAccounting

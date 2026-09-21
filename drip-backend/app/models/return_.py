from __future__ import annotations

import enum
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Integer, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ReturnStatus(str, enum.Enum):
    requested = "requested"
    approved  = "approved"
    rejected  = "rejected"
    received  = "received"
    refunded  = "refunded"


class DisputeStatus(str, enum.Enum):
    open               = "open"
    under_review       = "under_review"
    resolved_customer  = "resolved_customer"
    resolved_seller    = "resolved_seller"
    closed             = "closed"


class Return(Base):
    __tablename__ = "returns"

    id:             Mapped[UUID]          = mapped_column(primary_key=True, default=uuid4)
    order_id:       Mapped[UUID]          = mapped_column(ForeignKey("orders.id"))
    seller_order_id:Mapped[UUID]          = mapped_column(ForeignKey("seller_orders.id"))
    user_id:        Mapped[UUID]          = mapped_column(ForeignKey("users.id"))
    status:         Mapped[ReturnStatus]  = mapped_column(
                        SAEnum(ReturnStatus, name="return_status", create_type=False),
                        default=ReturnStatus.requested,
                    )
    reason:         Mapped[str]           = mapped_column(Text)
    notes:          Mapped[str | None]    = mapped_column(Text)
    requested_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default="now()")
    resolved_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items:   Mapped[list["ReturnItem"]]  = relationship(back_populates="return_", cascade="all, delete-orphan")
    dispute: Mapped["Dispute | None"]    = relationship(back_populates="return_", uselist=False)


class ReturnItem(Base):
    __tablename__ = "return_items"

    id:            Mapped[UUID]      = mapped_column(primary_key=True, default=uuid4)
    return_id:     Mapped[UUID]      = mapped_column(ForeignKey("returns.id", ondelete="CASCADE"))
    order_item_id: Mapped[UUID]      = mapped_column(ForeignKey("order_items.id"))
    quantity:      Mapped[int]       = mapped_column(Integer)
    reason:        Mapped[str | None] = mapped_column(Text)

    return_: Mapped["Return"] = relationship(back_populates="items")


class Dispute(Base):
    __tablename__ = "disputes"

    id:              Mapped[UUID]          = mapped_column(primary_key=True, default=uuid4)
    return_id:       Mapped[UUID]          = mapped_column(ForeignKey("returns.id"))
    seller_id:       Mapped[UUID]          = mapped_column(ForeignKey("sellers.id"))
    user_id:         Mapped[UUID]          = mapped_column(ForeignKey("users.id"))
    status:          Mapped[DisputeStatus] = mapped_column(
                         SAEnum(DisputeStatus, name="dispute_status", create_type=False),
                         default=DisputeStatus.open,
                     )
    resolution_note: Mapped[str | None]    = mapped_column(Text)
    resolved_by:     Mapped[UUID | None]   = mapped_column(ForeignKey("users.id"))
    created_at:      Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default="now()")
    resolved_at:     Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    return_:  Mapped["Return"]                  = relationship(back_populates="dispute")
    messages: Mapped[list["DisputeMessage"]]    = relationship(back_populates="dispute", cascade="all, delete-orphan")


class DisputeMessage(Base):
    __tablename__ = "dispute_messages"

    id:         Mapped[UUID]     = mapped_column(primary_key=True, default=uuid4)
    dispute_id: Mapped[UUID]     = mapped_column(ForeignKey("disputes.id", ondelete="CASCADE"))
    sender_id:  Mapped[UUID]     = mapped_column(ForeignKey("users.id"))
    body:       Mapped[str]      = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    dispute: Mapped["Dispute"] = relationship(back_populates="messages")
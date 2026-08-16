from __future__ import annotations

import enum
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    String, Text, Numeric, DateTime,
    Enum as SAEnum, ForeignKey, CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.seller import Seller


class WalletTxType(str, enum.Enum):
    credit_commission  = "credit_commission"
    debit_commission   = "debit_commission"
    credit_refund      = "credit_refund"
    debit_withdrawal   = "debit_withdrawal"
    credit_adjustment  = "credit_adjustment"
    debit_adjustment   = "debit_adjustment"


class PayoutStatus(str, enum.Enum):
    requested  = "requested"
    approved   = "approved"
    processing = "processing"
    completed  = "completed"
    rejected   = "rejected"


class CommissionLedger(Base):
    __tablename__ = "commission_ledger"
    __table_args__ = (
        CheckConstraint(
            "commission_amount + seller_amount = gross_amount",
            name="ck_commission_amounts",
        ),
    )

    id:                Mapped[UUID]    = mapped_column(primary_key=True, default=uuid4)
    seller_order_id:   Mapped[UUID]    = mapped_column(
                           ForeignKey("seller_orders.id", ondelete="RESTRICT"), unique=True
                       )
    seller_id:         Mapped[UUID]    = mapped_column(ForeignKey("sellers.id"))
    gross_amount:      Mapped[Decimal] = mapped_column(Numeric(12, 2))
    commission_rate:   Mapped[Decimal] = mapped_column(Numeric(5, 4))   # e.g. 0.1500
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    seller_amount:     Mapped[Decimal] = mapped_column(Numeric(12, 2))
    settled_at:        Mapped[datetime] = mapped_column(
                           DateTime(timezone=True), server_default="now()"
                       )

    seller:       Mapped["Seller"]      = relationship()
    seller_order: Mapped["SellerOrder"] = relationship()


class Payout(Base):
    __tablename__ = "payouts"
    __table_args__ = (
        CheckConstraint("amount >= 500", name="ck_payouts_amount_min"),
    )

    id:             Mapped[UUID]          = mapped_column(primary_key=True, default=uuid4)
    seller_id:      Mapped[UUID]          = mapped_column(ForeignKey("sellers.id"))
    amount:         Mapped[Decimal]       = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str]           = mapped_column(String(50))
    payment_detail: Mapped[str]           = mapped_column(String(255))
    status:         Mapped[PayoutStatus]  = mapped_column(
                        SAEnum(PayoutStatus, name="payout_status", create_type=False),
                        default=PayoutStatus.requested,
                    )
    admin_note:     Mapped[str | None]    = mapped_column(Text)
    approved_by:    Mapped[UUID | None]   = mapped_column(ForeignKey("users.id"))
    requested_at:   Mapped[datetime]      = mapped_column(
                        DateTime(timezone=True), server_default="now()"
                    )
    completed_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    seller: Mapped["Seller"] = relationship(back_populates="payouts")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id:              Mapped[UUID]         = mapped_column(primary_key=True, default=uuid4)
    seller_id:       Mapped[UUID]         = mapped_column(ForeignKey("sellers.id"))
    type:            Mapped[WalletTxType] = mapped_column(
                         SAEnum(WalletTxType, name="wallet_tx_type", create_type=False)
                     )
    amount:          Mapped[Decimal]      = mapped_column(Numeric(12, 2))
    balance_after:   Mapped[Decimal]      = mapped_column(Numeric(12, 2))
    reference:       Mapped[str | None]   = mapped_column(String(255))
    seller_order_id: Mapped[UUID | None]  = mapped_column(ForeignKey("seller_orders.id"))
    payout_id:       Mapped[UUID | None]  = mapped_column(ForeignKey("payouts.id"))
    note:            Mapped[str | None]   = mapped_column(Text)
    created_at:      Mapped[datetime]     = mapped_column(
                         DateTime(timezone=True), server_default="now()"
                     )

    seller:       Mapped["Seller"]             = relationship(back_populates="wallet_transactions")
    seller_order: Mapped["SellerOrder | None"] = relationship()
    payout:       Mapped["Payout | None"]      = relationship()
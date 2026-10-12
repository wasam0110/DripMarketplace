from __future__ import annotations

import enum
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    String, Text, Numeric, DateTime,
    Enum as SAEnum, ForeignKey, CheckConstraint, Index, UniqueConstraint,
)
from sqlalchemy.ext.hybrid import hybrid_property
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
        CheckConstraint(
            "refunded_gross_amount >= 0 "
            "AND reversed_commission_amount >= 0 "
            "AND reversed_seller_amount >= 0 "
            "AND recovered_seller_amount >= 0 "
            "AND settlement_offset_amount >= 0 "
            "AND platform_shortfall_amount >= 0",
            name="ck_commission_refund_amounts_nonnegative",
        ),
        CheckConstraint(
            "refunded_gross_amount <= gross_amount "
            "AND reversed_commission_amount <= commission_amount "
            "AND reversed_seller_amount <= seller_amount",
            name="ck_commission_refund_amounts_capped",
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
    refunded_gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    reversed_commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    reversed_seller_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    recovered_seller_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    settlement_offset_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    platform_shortfall_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_at:        Mapped[datetime] = mapped_column(
                           DateTime(timezone=True), server_default="now()"
                       )

    seller:       Mapped["Seller"]      = relationship()
    seller_order: Mapped["SellerOrder"] = relationship()

    @hybrid_property
    def net_gross_amount(self) -> Decimal:
        return self.gross_amount - self.refunded_gross_amount

    @net_gross_amount.expression
    def net_gross_amount(cls):
        return cls.gross_amount - cls.refunded_gross_amount

    @hybrid_property
    def net_commission_amount(self) -> Decimal:
        return self.commission_amount - self.reversed_commission_amount

    @net_commission_amount.expression
    def net_commission_amount(cls):
        return cls.commission_amount - cls.reversed_commission_amount

    @hybrid_property
    def net_seller_amount(self) -> Decimal:
        return self.seller_amount - self.reversed_seller_amount

    @net_seller_amount.expression
    def net_seller_amount(cls):
        return cls.seller_amount - cls.reversed_seller_amount


class RefundAccounting(Base):
    __tablename__ = "refund_accounting"
    __table_args__ = (
        CheckConstraint(
            "merchandise_amount >= 0 AND shipping_amount >= 0 "
            "AND commission_reversal_amount >= 0 "
            "AND seller_reversal_amount >= 0 "
            "AND recovered_amount >= 0 "
            "AND settlement_offset_amount >= 0 "
            "AND platform_shortfall_amount >= 0 "
            "AND platform_funded_amount >= 0",
            name="ck_refund_accounting_nonnegative",
        ),
        CheckConstraint(
            "seller_reversal_amount = recovered_amount "
            "+ settlement_offset_amount + platform_shortfall_amount",
            name="ck_refund_accounting_seller_conservation",
        ),
        CheckConstraint(
            "platform_funded_amount = shipping_amount "
            "+ commission_reversal_amount + platform_shortfall_amount",
            name="ck_refund_accounting_platform_conservation",
        ),
    )

    refund_id: Mapped[UUID] = mapped_column(
        ForeignKey("refunds.id", ondelete="CASCADE"), primary_key=True
    )
    merchandise_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    commission_reversal_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), server_default="0"
    )
    seller_reversal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    recovered_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    settlement_offset_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), server_default="0"
    )
    platform_shortfall_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), server_default="0"
    )
    platform_funded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    refund: Mapped["Refund"] = relationship(back_populates="accounting")
    allocations: Mapped[list["RefundAllocation"]] = relationship(
        back_populates="accounting", cascade="all, delete-orphan"
    )


class RefundAllocation(Base):
    __tablename__ = "refund_allocations"
    __table_args__ = (
        UniqueConstraint("refund_id", "seller_order_id", name="uq_refund_allocation_order"),
        CheckConstraint(
            "merchandise_amount > 0 "
            "AND commission_reversal_amount >= 0 "
            "AND seller_reversal_amount >= 0 "
            "AND recovered_amount >= 0 "
            "AND settlement_offset_amount >= 0 "
            "AND platform_shortfall_amount >= 0",
            name="ck_refund_allocation_nonnegative",
        ),
        CheckConstraint(
            "applied_at IS NULL OR commission_reversal_amount "
            "+ seller_reversal_amount = merchandise_amount",
            name="ck_refund_allocation_merchandise_conservation",
        ),
        CheckConstraint(
            "seller_reversal_amount = recovered_amount "
            "+ settlement_offset_amount + platform_shortfall_amount",
            name="ck_refund_allocation_seller_conservation",
        ),
        Index("ix_refund_allocations_seller_order_id", "seller_order_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    refund_id: Mapped[UUID] = mapped_column(
        ForeignKey("refund_accounting.refund_id", ondelete="CASCADE")
    )
    seller_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("seller_orders.id", ondelete="RESTRICT")
    )
    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"))
    merchandise_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    commission_reversal_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    seller_reversal_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    recovered_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    settlement_offset_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    platform_shortfall_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0"
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    accounting: Mapped["RefundAccounting"] = relationship(back_populates="allocations")
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
    transfer_reference: Mapped[str | None] = mapped_column(String(255))
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
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.order import SellerOrder
    from app.models.payment import Refund

from __future__ import annotations
import enum
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    String, Text, Numeric, Boolean, Integer,
    DateTime, Enum as SAEnum, ForeignKey, CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user import User


class SellerStatus(str, enum.Enum):
    pending_payment  = "pending_payment"
    pending_approval = "pending_approval"
    active           = "active"
    suspended        = "suspended"
    rejected         = "rejected"


class Seller(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sellers"
    __table_args__ = (
        CheckConstraint("slots_used <= total_slots", name="ck_sellers_slots_used_lte_total"),
        CheckConstraint("slots_used >= 0",           name="ck_sellers_slots_used_gte_zero"),
        CheckConstraint("total_slots >= 50",         name="ck_sellers_total_slots_positive"),
    )

    id:               Mapped[UUID]           = mapped_column(primary_key=True, default=uuid4)
    user_id:          Mapped[UUID]           = mapped_column(ForeignKey("users.id"), unique=True)
    brand_name:       Mapped[str]            = mapped_column(String(100), unique=True)
    slug:             Mapped[str]            = mapped_column(String(120), unique=True)
    description:      Mapped[str | None]     = mapped_column(Text)
    logo_url:         Mapped[str | None]     = mapped_column(String(500))
    brand_color:      Mapped[str]            = mapped_column(String(7), default="#DFFF00")
    return_policy:    Mapped[str | None]     = mapped_column(Text)
    whatsapp_number:  Mapped[str | None]     = mapped_column(String(20))
    instagram_handle: Mapped[str | None]     = mapped_column(String(100))
    status:           Mapped[SellerStatus]   = mapped_column(
                          SAEnum(SellerStatus, name="seller_status"),
                          default=SellerStatus.pending_payment,
                      )
    total_slots:      Mapped[int]            = mapped_column(Integer, default=50)
    slots_used:       Mapped[int]            = mapped_column(Integer, default=0)
    registration_fee: Mapped[Decimal]        = mapped_column(Numeric(10, 2), default=Decimal("5000.00"))
    rejected_reason:  Mapped[str | None]     = mapped_column(Text)
    approved_by:      Mapped[UUID | None]    = mapped_column(ForeignKey("users.id"))
    approved_at:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user:          Mapped["User"]                      = relationship(
                       "User", back_populates="seller", foreign_keys=[user_id]
                   )
    wallet:        Mapped["SellerWallet"]              = relationship(
                       back_populates="seller", uselist=False, cascade="all, delete-orphan"
                   )
    bank_accounts: Mapped[list["SellerBankAccount"]]  = relationship(
                       back_populates="seller", cascade="all, delete-orphan"
                   )
    # These relationships are wired here so Block 4/5 models slot straight in
    products:            Mapped[list["Product"]]           = relationship(back_populates="seller")


    @property
    def slots_available(self) -> int:
        return self.total_slots - self.slots_used

    @property
    def is_active(self) -> bool:
        return self.status == SellerStatus.active


class SellerWallet(Base):
    __tablename__ = "seller_wallets"

    id:                Mapped[UUID]     = mapped_column(primary_key=True, default=uuid4)
    seller_id:         Mapped[UUID]     = mapped_column(ForeignKey("sellers.id"), unique=True)
    available_balance: Mapped[Decimal]  = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    pending_balance:   Mapped[Decimal]  = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total_earned:      Mapped[Decimal]  = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total_commission:  Mapped[Decimal]  = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    updated_at:        Mapped[datetime] = mapped_column(
                           DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow
                       )

    seller: Mapped["Seller"] = relationship(back_populates="wallet")


class SellerBankAccount(Base):
    __tablename__ = "seller_bank_accounts"

    id:               Mapped[UUID]       = mapped_column(primary_key=True, default=uuid4)
    seller_id:        Mapped[UUID]       = mapped_column(
                          ForeignKey("sellers.id", ondelete="CASCADE")
                      )
    bank_name:        Mapped[str | None] = mapped_column(String(100))
    account_title:    Mapped[str | None] = mapped_column(String(200))
    account_number:   Mapped[str | None] = mapped_column(String(50))
    jazzcash_number:  Mapped[str | None] = mapped_column(String(20))
    easypaisa_number: Mapped[str | None] = mapped_column(String(20))
    is_default:       Mapped[bool]       = mapped_column(Boolean, default=False)
    created_at:       Mapped[datetime]   = mapped_column(
                          DateTime(timezone=True), server_default="now()"
                      )

    seller: Mapped["Seller"] = relationship(back_populates="bank_accounts")
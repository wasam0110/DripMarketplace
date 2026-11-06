"""schemas / wallet.

Validated request and response contracts used by API routes and services.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import settings


class WalletSummaryResponse(BaseModel):
    available_balance: Decimal
    pending_balance:   Decimal
    total_earned:      Decimal
    total_commission:  Decimal
    minimum_withdrawal_amount: Decimal
    maximum_withdrawal_amount: Decimal


class WalletTransactionResponse(BaseModel):
    id:              UUID
    type:            str
    amount:          Decimal
    balance_after:   Decimal
    reference:       Optional[str]
    note:            Optional[str]
    created_at:      datetime

    model_config = {"from_attributes": True}


class PaginatedTransactions(BaseModel):
    data:        list[WalletTransactionResponse]
    total:       int
    page:        int
    per_page:    int
    total_pages: int


class WithdrawalRequest(BaseModel):
    amount: Decimal = Field(
        ge=settings.MIN_WITHDRAWAL_AMOUNT,
        le=settings.MAX_WITHDRAWAL_AMOUNT,
        max_digits=12,
        decimal_places=2,
    )
    bank_account_id: UUID
    note:            Optional[str] = Field(default=None, max_length=300)


class PayoutResponse(BaseModel):
    id:             UUID
    amount:         Decimal
    payment_method: str
    payment_detail: str
    status:         str
    admin_note:     Optional[str]
    requested_at:   datetime
    completed_at:   Optional[datetime]
    transfer_reference: str | None = None

    model_config = {"from_attributes": True}


class PaginatedPayouts(BaseModel):
    data:        list[PayoutResponse]
    total:       int
    page:        int
    total_pages: int


class CommissionEntryResponse(BaseModel):
    id:                UUID
    seller_order_id:   UUID
    gross_amount:      Decimal
    commission_rate:   float
    commission_amount: Decimal
    seller_amount:     Decimal
    original_gross_amount: Decimal
    original_commission_amount: Decimal
    original_seller_amount: Decimal
    refunded_gross_amount: Decimal
    reversed_commission_amount: Decimal
    reversed_seller_amount: Decimal
    recovered_seller_amount: Decimal
    settlement_offset_amount: Decimal
    platform_shortfall_amount: Decimal
    released_at: datetime | None
    settled_at:        datetime

    model_config = {"from_attributes": True}


class CommissionSummary(BaseModel):
    total_gross:      Decimal
    total_commission: Decimal
    total_net:        Decimal
    original_gross: Decimal
    original_commission: Decimal
    original_net: Decimal
    total_refunded_gross: Decimal
    total_reversed_commission: Decimal
    total_reversed_seller: Decimal
    total_recovered_seller: Decimal
    total_settlement_offset: Decimal
    total_platform_shortfall: Decimal


class CommissionBreakdownResponse(BaseModel):
    data:    list[CommissionEntryResponse]
    summary: CommissionSummary
    total:   int
    page:    int


class PayoutReview(BaseModel):
    expected_status: str
    expected_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    expected_seller_id: UUID
    expected_payment_method: str
    expected_payment_detail: str
    expected_admin_note: str | None


class AdminPayoutDetailResponse(PayoutResponse):
    seller_id: UUID
    last_action_by: UUID | None
    available_actions: list[str]


class AdminPayoutActionRequest(BaseModel):
    admin_note: Optional[str] = Field(default=None, max_length=500)
    review: PayoutReview | None = None


class CompletePayoutRequest(AdminPayoutActionRequest):
    reference: str = Field(min_length=3, max_length=255)


class AdminWalletOverviewResponse(BaseModel):
    total_available_balance: Decimal
    total_pending_balance:   Decimal
    total_payouts_pending:   int
    total_payouts_completed: int

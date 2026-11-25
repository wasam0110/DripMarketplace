"""schemas / wallet.

Validated request and response contracts used by API routes and services.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.money import PKRResponseAmount


class WalletSummaryResponse(BaseModel):
    available_balance: PKRResponseAmount
    pending_balance:   PKRResponseAmount
    total_earned:      PKRResponseAmount
    total_commission:  PKRResponseAmount
    minimum_withdrawal_amount: PKRResponseAmount
    maximum_withdrawal_amount: PKRResponseAmount


class WalletTransactionResponse(BaseModel):
    id:              UUID
    type:            str
    amount:          PKRResponseAmount
    balance_after:   PKRResponseAmount
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
    amount:         PKRResponseAmount
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
    gross_amount:      PKRResponseAmount
    commission_rate:   float
    commission_amount: PKRResponseAmount
    seller_amount:     PKRResponseAmount
    original_gross_amount: PKRResponseAmount
    original_commission_amount: PKRResponseAmount
    original_seller_amount: PKRResponseAmount
    refunded_gross_amount: PKRResponseAmount
    reversed_commission_amount: PKRResponseAmount
    reversed_seller_amount: PKRResponseAmount
    recovered_seller_amount: PKRResponseAmount
    settlement_offset_amount: PKRResponseAmount
    platform_shortfall_amount: PKRResponseAmount
    released_at: datetime | None
    settled_at:        datetime

    model_config = {"from_attributes": True}


class CommissionSummary(BaseModel):
    total_gross:      PKRResponseAmount
    total_commission: PKRResponseAmount
    total_net:        PKRResponseAmount
    original_gross: PKRResponseAmount
    original_commission: PKRResponseAmount
    original_net: PKRResponseAmount
    total_refunded_gross: PKRResponseAmount
    total_reversed_commission: PKRResponseAmount
    total_reversed_seller: PKRResponseAmount
    total_recovered_seller: PKRResponseAmount
    total_settlement_offset: PKRResponseAmount
    total_platform_shortfall: PKRResponseAmount


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
    total_available_balance: PKRResponseAmount
    total_pending_balance:   PKRResponseAmount
    total_payouts_pending:   int
    total_payouts_completed: int

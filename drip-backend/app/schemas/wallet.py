from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WalletSummaryResponse(BaseModel):
    available_balance: int
    pending_balance:   int
    total_earned:      int
    total_commission:  int


class WalletTransactionResponse(BaseModel):
    id:              UUID
    type:            str
    amount:          int
    balance_after:   int
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
    amount:          int = Field(ge=500, le=200_000)
    bank_account_id: UUID
    note:            Optional[str] = Field(default=None, max_length=300)


class PayoutResponse(BaseModel):
    id:             UUID
    amount:         int
    payment_method: str
    payment_detail: str
    status:         str
    admin_note:     Optional[str]
    requested_at:   datetime
    completed_at:   Optional[datetime]

    model_config = {"from_attributes": True}


class PaginatedPayouts(BaseModel):
    data:        list[PayoutResponse]
    total:       int
    page:        int
    total_pages: int


class CommissionEntryResponse(BaseModel):
    id:                UUID
    seller_order_id:   UUID
    gross_amount:      int
    commission_rate:   float
    commission_amount: int
    seller_amount:     int
    settled_at:        datetime

    model_config = {"from_attributes": True}


class CommissionSummary(BaseModel):
    total_gross:      int
    total_commission: int
    total_net:        int


class CommissionBreakdownResponse(BaseModel):
    data:    list[CommissionEntryResponse]
    summary: CommissionSummary
    total:   int
    page:    int


class AdminPayoutActionRequest(BaseModel):
    admin_note: Optional[str] = Field(default=None, max_length=500)


class AdminWalletOverviewResponse(BaseModel):
    total_available_balance: int
    total_pending_balance:   int
    total_payouts_pending:   int
    total_payouts_completed: int
"""
app/schemas/payment.py — PayFast + COD only.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.order import PaymentMethod


class InitiatePaymentRequest(BaseModel):
    order_id: UUID


class PayFastCheckoutResponse(BaseModel):
    """Returned to the frontend so it can build a form POST to PayFast."""

    payment_id: UUID
    checkout_url: str  # PayFast checkout page URL
    payload: dict[str, str]  # Pre-signed form fields to POST
    expires_at: datetime | None = None


class PaymentInitResponse(BaseModel):
    payment_id: UUID
    method: str
    # PayFast fields
    checkout_url: str | None = None
    payfast_payload: dict | None = None
    # COD has no redirect
    expires_at: datetime | None = None


class PaymentStatusResponse(BaseModel):
    order_id: UUID
    payment_id: UUID
    status: str
    method: str
    amount: Decimal
    gateway_reference: str | None
    paid_at: datetime | None


class RetryPaymentRequest(BaseModel):
    payment_method: PaymentMethod


class RefundRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=5, max_length=500)


class RefundResponse(BaseModel):
    status: str = "pending"
    processed_at: datetime | None = None
    refund_id: UUID
    payment_id: UUID
    amount: Decimal
    reason: str
    gateway_ref: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminRefundRowResponse(BaseModel):
    refund_id: UUID
    payment_id: UUID
    order_id: UUID
    order_number: str
    return_id: UUID | None
    status: Literal["pending", "completed"]
    amount: Decimal
    reason: str
    transfer_reference: str | None
    requested_by: UUID | None
    confirmed_by: UUID | None
    requested_at: datetime
    processed_at: datetime | None


class PaginatedRefunds(BaseModel):
    data: list[AdminRefundRowResponse]
    total: int
    page: int


class RefundHistoryEvent(BaseModel):
    event: Literal["requested", "completed"]
    occurred_at: datetime
    actor_id: UUID | None
    transfer_reference: str | None = None


class RefundPaymentBalanceResponse(BaseModel):
    payment_id: UUID
    order_id: UUID
    order_number: str
    payment_status: str
    payment_method: str
    payment_amount: Decimal
    pending_refund_amount: Decimal
    completed_refund_amount: Decimal
    reserved_refund_amount: Decimal
    remaining_refundable_amount: Decimal
    can_request_refund: bool


class AdminRefundDetailResponse(AdminRefundRowResponse):
    payment: RefundPaymentBalanceResponse
    history: list[RefundHistoryEvent]


class PaymentRefundHistoryResponse(RefundPaymentBalanceResponse):
    refunds: list[AdminRefundRowResponse]


class GatewayStatusResponse(BaseModel):
    payfast: str
    cod: str


class PayFastReconcileResponse(BaseModel):
    order_id: UUID
    payment_id: UUID
    provider_status: str
    local_status: str
    transaction_id: str | None = None
    matched: bool
    detail: str


class PaymentRowResponse(BaseModel):
    id: UUID
    order_id: UUID
    order_number: str
    method: str
    status: str
    amount: Decimal
    gateway_reference: str | None
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedPayments(BaseModel):
    data: list[PaymentRowResponse]
    total: int
    page: int


class TransferConfirmationRequest(BaseModel):
    reference: str = Field(min_length=3, max_length=255)

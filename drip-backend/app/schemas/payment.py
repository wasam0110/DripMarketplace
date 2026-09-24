"""
app/schemas/payment.py — PayFast + COD only.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from app.models.order import PaymentMethod


class InitiatePaymentRequest(BaseModel):
    order_id: UUID


class PayFastCheckoutResponse(BaseModel):
    """Returned to the frontend so it can build a form POST to PayFast."""
    payment_id:   UUID
    checkout_url: str                   # PayFast checkout page URL
    payload:      dict[str, str]        # Pre-signed form fields to POST
    expires_at:   Optional[datetime] = None


class PaymentInitResponse(BaseModel):
    payment_id:           UUID
    method:               str
    # PayFast fields
    checkout_url:         Optional[str]         = None
    payfast_payload:      Optional[dict]        = None
    # COD has no redirect
    expires_at:           Optional[datetime]    = None


class PaymentStatusResponse(BaseModel):
    order_id:          UUID
    payment_id:        UUID
    status:            str
    method:            str
    amount:            Decimal
    gateway_reference: Optional[str]
    paid_at:           Optional[datetime]


class RetryPaymentRequest(BaseModel):
    payment_method: PaymentMethod


class RefundRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=5, max_length=500)


class RefundResponse(BaseModel):
    status: str = "pending"
    processed_at: datetime | None = None
    refund_id:   UUID
    payment_id:  UUID
    amount:      Decimal
    reason:      str
    gateway_ref: Optional[str]
    created_at:  datetime

    model_config = {"from_attributes": True}


class GatewayStatusResponse(BaseModel):
    payfast: str
    cod:     str


class PaymentRowResponse(BaseModel):
    id:                UUID
    order_id:          UUID
    order_number:      str
    method:            str
    status:            str
    amount:            Decimal
    gateway_reference: Optional[str]
    paid_at:           Optional[datetime]
    created_at:        datetime

    model_config = {"from_attributes": True}


class PaginatedPayments(BaseModel):
    data:  list[PaymentRowResponse]
    total: int
    page:  int


class TransferConfirmationRequest(BaseModel):
    reference: str = Field(min_length=3, max_length=255)

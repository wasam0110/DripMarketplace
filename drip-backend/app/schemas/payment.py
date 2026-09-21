"""
app/schemas/payment.py — PayFast + COD only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
    amount:            int
    gateway_reference: Optional[str]
    paid_at:           Optional[datetime]


class RetryPaymentRequest(BaseModel):
    payment_method: str = Field(pattern="^(payfast|cod)$")


class RefundRequest(BaseModel):
    amount: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=500)


class RefundResponse(BaseModel):
    refund_id:   UUID
    payment_id:  UUID
    amount:      int
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
    amount:            int
    gateway_reference: Optional[str]
    paid_at:           Optional[datetime]
    created_at:        datetime

    model_config = {"from_attributes": True}


class PaginatedPayments(BaseModel):
    data:  list[PaymentRowResponse]
    total: int
    page:  int

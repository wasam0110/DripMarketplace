from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InitiatePaymentRequest(BaseModel):
    order_id: UUID


class PaymentInitResponse(BaseModel):
    payment_id:           UUID
    method:               str
    payment_url:          Optional[str] = None
    stripe_client_secret: Optional[str] = None
    expires_at:           Optional[datetime] = None


class PaymentStatusResponse(BaseModel):
    order_id:          UUID
    payment_id:        UUID
    status:            str
    method:            str
    amount:            int
    gateway_reference: Optional[str]
    paid_at:           Optional[datetime]


class RetryPaymentRequest(BaseModel):
    payment_method: str = Field(pattern="^(jazzcash|easypaisa|card|cod)$")


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
    jazzcash:  str
    easypaisa: str
    stripe:    str


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
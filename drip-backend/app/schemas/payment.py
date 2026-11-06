"""
app/schemas/payment.py — PayFast + COD only.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, ValidationInfo, field_validator

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
    attempt_id: UUID | None = None
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
    expected_remaining_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )

    @field_validator("reason", "idempotency_key")
    @classmethod
    def clean_request_text(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None:
            return None
        value = value.strip()
        minimum = 5 if info.field_name == "reason" else 8
        allowed = "\n\r\t" if info.field_name == "reason" else ""
        if len(value) < minimum or any(
            (ord(char) < 32 and char not in allowed) or ord(char) == 127 for char in value
        ):
            raise ValueError("Use meaningful text without control characters")
        return value


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


class RefundAllocationResponse(BaseModel):
    seller_order_id: UUID
    seller_id: UUID
    merchandise_amount: Decimal
    commission_rate: Decimal | None
    commission_reversal_amount: Decimal
    seller_reversal_amount: Decimal
    recovered_amount: Decimal
    settlement_offset_amount: Decimal
    platform_shortfall_amount: Decimal
    reconciled: bool


class RefundAccountingResponse(BaseModel):
    merchandise_amount: Decimal
    shipping_amount: Decimal
    commission_reversal_amount: Decimal
    seller_reversal_amount: Decimal
    recovered_amount: Decimal
    settlement_offset_amount: Decimal
    platform_shortfall_amount: Decimal
    platform_funded_amount: Decimal
    reconciled: bool
    allocations: list[RefundAllocationResponse]


class AdminRefundRowResponse(BaseModel):
    refund_id: UUID
    payment_id: UUID
    order_id: UUID
    order_number: str
    return_id: UUID | None
    status: Literal["pending", "completed"]
    amount: Decimal
    currency: str
    reason: str
    transfer_reference: str | None
    requested_by: UUID | None
    confirmed_by: UUID | None
    requested_at: datetime
    processed_at: datetime | None
    accounting: RefundAccountingResponse | None = None


class PaginatedRefunds(BaseModel):
    data: list[AdminRefundRowResponse]
    total: int
    page: int
    per_page: int = 25
    total_pages: int = 1


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
    currency: str
    pending_refund_amount: Decimal
    completed_refund_amount: Decimal
    reserved_refund_amount: Decimal
    remaining_refundable_amount: Decimal
    can_request_refund: bool


class AdminRefundDetailResponse(AdminRefundRowResponse):
    payment: RefundPaymentBalanceResponse
    history: list[RefundHistoryEvent]
    can_confirm_refund: bool
    confirmation_blockers: list[str]
    linked_return_status: str | None = None


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
    currency: str
    gateway_reference: str | None
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedPayments(BaseModel):
    data: list[PaymentRowResponse]
    total: int
    page: int
    per_page: int = 25
    total_pages: int = 1


class AdminPaymentDetailResponse(PaymentRowResponse):
    currency: str
    order_status: str
    order_updated_at: datetime
    can_record_cod_collection: bool
    collection_blockers: list[str]
    collection_recorded_by: UUID | None = None


class CODCollectionRequest(BaseModel):
    reference: str = Field(min_length=3, max_length=255)
    expected_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    expected_order_updated_at: AwareDatetime | None = None

    @field_validator("reference")
    @classmethod
    def clean_reference(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3 or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Use a reference of 3–255 characters without control characters")
        return value


class CODCollectionResponse(BaseModel):
    payment_id: UUID
    order_id: UUID
    order_number: str
    status: Literal["completed"] = "completed"
    amount: Decimal
    currency: Literal["PKR"] = "PKR"
    reference: str
    paid_at: datetime
    recorded_by: UUID | None = None


class TransferConfirmationRequest(BaseModel):
    reference: str = Field(min_length=3, max_length=255)


class RefundConfirmationRequest(TransferConfirmationRequest):
    expected_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    expected_payment_id: UUID | None = None
    expected_return_id: UUID | None = None

    @field_validator("reference")
    @classmethod
    def clean_reference(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3 or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Use a reference of 3–255 characters without control characters")
        return value

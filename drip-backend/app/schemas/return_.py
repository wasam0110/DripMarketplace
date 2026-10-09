from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReturnItemRequest(BaseModel):
    order_item_id: UUID
    quantity:      int = Field(ge=1)
    reason:        Optional[str] = Field(default=None, max_length=500)


class CreateReturnRequest(BaseModel):
    seller_order_id: UUID
    reason:          str           = Field(min_length=10, max_length=1000)
    items:           list[ReturnItemRequest] = Field(min_length=1)
    notes:           Optional[str] = Field(default=None, max_length=500)


class ReturnItemResponse(BaseModel):
    id:            UUID
    order_item_id: UUID
    quantity:      int
    reason:        Optional[str]

    model_config = {"from_attributes": True}


class ReturnRowResponse(BaseModel):
    id:              UUID
    order_id:        UUID
    seller_order_id: UUID
    status:          str
    reason:          str
    item_count:      int
    requested_at:    datetime
    resolved_at:     Optional[datetime]

    model_config = {"from_attributes": True}


class ReturnDetailResponse(ReturnRowResponse):
    notes: Optional[str]
    items: list[ReturnItemResponse]


class AdminReturnCustomerResponse(BaseModel):
    user_id: Optional[UUID]
    is_guest: bool
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]


class AdminReturnSellerResponse(BaseModel):
    seller_id: UUID
    brand_name: str


class AdminReturnOrderResponse(BaseModel):
    order_id: UUID
    order_number: str
    status: str
    payment_method: str
    subtotal: Decimal
    discount_amount: Decimal
    shipping_fee: Decimal
    total: Decimal
    payment_id: Optional[UUID]
    payment_status: Optional[str]


class AdminReturnItemResponse(BaseModel):
    id: UUID
    order_item_id: UUID
    product_id: UUID
    variant_id: UUID
    product_name: str
    variant_label: str
    unit_price: Decimal
    purchased_quantity: int
    requested_quantity: int
    line_subtotal: Decimal
    reason: Optional[str]


class AdminReturnRefundResponse(BaseModel):
    refund_id: UUID
    status: str
    amount: Decimal
    transfer_reference: Optional[str]
    requested_at: datetime
    processed_at: Optional[datetime]


class AdminReturnDisputeResponse(BaseModel):
    dispute_id: UUID
    status: str


class AdminReturnDetailResponse(ReturnRowResponse):
    notes: Optional[str]
    customer: AdminReturnCustomerResponse
    seller: AdminReturnSellerResponse
    order: AdminReturnOrderResponse
    items: list[AdminReturnItemResponse]
    estimated_refund_amount: Decimal
    available_actions: list[str]
    refund: Optional[AdminReturnRefundResponse]
    dispute: Optional[AdminReturnDisputeResponse]


class SellerReturnDetailResponse(ReturnRowResponse):
    notes: Optional[str]
    order_number: str
    items: list[AdminReturnItemResponse]
    estimated_refund_amount: Decimal
    available_actions: list[str]
    refund_status: Optional[str]
    dispute_status: Optional[str]


class PaginatedReturns(BaseModel):
    data:        list[ReturnRowResponse]
    total:       int
    page:        int
    total_pages: int


class OpenDisputeRequest(BaseModel):
    message: str = Field(min_length=10, max_length=2000)


class AddDisputeMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class DisputeMessageResponse(BaseModel):
    id:         UUID
    sender_id:  UUID
    body:       str
    created_at: datetime

    model_config = {"from_attributes": True}


class DisputeDetailResponse(BaseModel):
    id:              UUID
    return_id:       UUID
    seller_id:       UUID
    status:          str
    resolution_note: Optional[str]
    created_at:      datetime
    resolved_at:     Optional[datetime]
    messages:        list[DisputeMessageResponse]

    model_config = {"from_attributes": True}


class AdminReturnActionRequest(BaseModel):
    admin_note: Optional[str] = Field(default=None, max_length=500)


class ResolveDisputeRequest(BaseModel):
    in_favor_of:     str  = Field(pattern="^(customer|seller)$")
    resolution_note: str  = Field(min_length=10, max_length=1000)

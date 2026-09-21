from __future__ import annotations

from uuid import UUID
from datetime import datetime
from typing import Optional

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
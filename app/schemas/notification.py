from __future__ import annotations

from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id:         UUID
    type:       str
    title:      str
    body:       str
    action_url: Optional[str]
    is_read:    bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    data:         list[NotificationResponse]
    unread_count: int
    total:        int
    page:         int


class NotificationPreferencesResponse(BaseModel):
    order_updates_email:      bool
    order_updates_push:       bool
    promotions_email:         bool
    payout_notifications:     bool
    new_review_notifications: bool
    low_stock_alerts:         bool

    model_config = {"from_attributes": True}


class UpdatePreferencesRequest(BaseModel):
    order_updates_email:      Optional[bool] = None
    order_updates_push:       Optional[bool] = None
    promotions_email:         Optional[bool] = None
    payout_notifications:     Optional[bool] = None
    new_review_notifications: Optional[bool] = None
    low_stock_alerts:         Optional[bool] = None


class BroadcastRequest(BaseModel):
    title:      str  = Field(min_length=1, max_length=200)
    body:       str  = Field(min_length=1, max_length=1000)
    audience:   str  = Field(pattern="^(all|customers|sellers)$")
    action_url: Optional[str] = Field(default=None, max_length=500)


class BroadcastResponse(BaseModel):
    recipient_count: int
    task_id:         str


class EmailLogResponse(BaseModel):
    id:              UUID
    recipient_email: str
    subject:         str
    template_id:     Optional[str]
    status:          str
    resend_id:       Optional[str]
    error_message:   Optional[str]
    sent_at:         datetime

    model_config = {"from_attributes": True}


class MarkReadResponse(BaseModel):
    updated_count: int
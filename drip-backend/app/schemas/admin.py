from __future__ import annotations

from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Dashboard ─────────────────────────────────────────────────────────────────

class AdminDashboardResponse(BaseModel):
    period:           str
    total_gmv:        int
    platform_revenue: int
    slot_revenue:     int
    total_revenue:    int
    total_orders:     int
    active_sellers:   int
    pending_sellers:  int
    cod_unverified:   int
    pending_payouts:  int
    new_customers:    int


# ── Sellers ───────────────────────────────────────────────────────────────────

class AdminSellerRowResponse(BaseModel):
    id:                UUID
    brand_name:        str
    status:            str
    slots_used:        int
    total_slots:       int
    product_count:     int
    total_gmv:         int
    platform_cut:      int
    available_balance: int
    joined_at:         datetime

    model_config = {"from_attributes": True}


class AdminSellerDetailResponse(AdminSellerRowResponse):
    slug:             str
    description:      Optional[str]
    whatsapp_number:  Optional[str]
    instagram_handle: Optional[str]
    logo_url:         Optional[str]
    return_policy:    Optional[str]
    pending_balance:  int
    registration_fee: int
    rejected_reason:  Optional[str]


class RejectSellerRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)


class SuspendSellerRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)


class PaginatedAdminSellers(BaseModel):
    data:        list[AdminSellerRowResponse]
    total:       int
    page:        int
    per_page:    int
    total_pages: int


# ── Orders ────────────────────────────────────────────────────────────────────

class AdminOrderRowResponse(BaseModel):
    id:             UUID
    order_number:   str
    status:         str
    customer_name:  str
    seller_count:   int
    subtotal:       int
    total:          int
    commission:     int
    payment_method: str
    created_at:     datetime

    model_config = {"from_attributes": True}


class OrderTotals(BaseModel):
    total_gmv:        int
    total_commission: int
    order_count:      int


class PaginatedAdminOrders(BaseModel):
    data:   list[AdminOrderRowResponse]
    totals: OrderTotals
    total:  int
    page:   int


# ── COD Queue ─────────────────────────────────────────────────────────────────

class CODQueueItem(BaseModel):
    order_id:          UUID
    order_number:      str
    customer_name:     str
    customer_phone:    str
    total:             int
    brand_names:       list[str]
    placed_at:         datetime
    expires_at:        datetime
    minutes_remaining: int


class CODVerifyRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=500)


# ── Banners ───────────────────────────────────────────────────────────────────

class BannerResponse(BaseModel):
    id:          UUID
    title:       str
    image_url:   str
    link_url:    Optional[str]
    position:    str
    sort_order:  int
    is_active:   bool
    valid_from:  Optional[datetime]
    valid_until: Optional[datetime]
    created_at:  datetime

    model_config = {"from_attributes": True}


# ── Settings ──────────────────────────────────────────────────────────────────

class UpdateSettingsRequest(BaseModel):
    commission_rate:         Optional[float] = Field(default=None, ge=0, le=1)
    registration_fee:        Optional[int]   = Field(default=None, ge=0)
    extra_slot_price:        Optional[int]   = Field(default=None, ge=0)
    free_shipping_threshold: Optional[int]   = Field(default=None, ge=0)
    standard_shipping_fee:   Optional[int]   = Field(default=None, ge=0)
    cod_timeout_minutes:     Optional[int]   = Field(default=None, ge=5, le=1440)
    wallet_hold_days:        Optional[int]   = Field(default=None, ge=0, le=30)


class PlatformSettingsResponse(BaseModel):
    commission_rate:         float
    registration_fee:        int
    extra_slot_price:        int
    free_shipping_threshold: int
    standard_shipping_fee:   int
    cod_timeout_minutes:     int
    wallet_hold_days:        int
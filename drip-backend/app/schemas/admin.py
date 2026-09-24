from __future__ import annotations
from decimal import Decimal

from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Dashboard ─────────────────────────────────────────────────────────────────

class AdminDashboardResponse(BaseModel):
    period:           str
    total_gmv:        Decimal
    platform_revenue: Decimal
    slot_revenue:     Decimal
    total_revenue:    Decimal
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
    total_gmv:         Decimal
    platform_cut:      Decimal
    available_balance: Decimal
    joined_at:         datetime

    model_config = {"from_attributes": True}


class AdminSellerDetailResponse(AdminSellerRowResponse):
    slug:             str
    description:      Optional[str]
    whatsapp_number:  Optional[str]
    instagram_handle: Optional[str]
    logo_url:         Optional[str]
    return_policy:    Optional[str]
    pending_balance:  Decimal
    registration_fee: Decimal
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
    subtotal:       Decimal
    total:          Decimal
    commission:     Decimal
    payment_method: str
    created_at:     datetime

    model_config = {"from_attributes": True}


class OrderTotals(BaseModel):
    total_gmv:        Decimal
    total_commission: Decimal
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
    total:             Decimal
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
    commission_rate:         float = Field(ge=0, le=1)
    registration_fee:        int = Field(ge=0)
    extra_slot_price:        int = Field(ge=0)
    free_shipping_threshold: int = Field(ge=0)
    standard_shipping_fee:   int = Field(ge=0)
    cod_timeout_minutes:     int = Field(ge=5, le=1440)
    wallet_hold_days:        int = Field(ge=0, le=30)

class UpdateBannerRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    link_url: str | None = Field(default=None, max_length=500)
    position: str | None = Field(default=None, pattern="^(homepage_hero|homepage_secondary|category_top)$")
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class SellerRegistrationPaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reference: str = Field(min_length=3, max_length=255)

"""schemas / admin.

Validated request and response contracts used by API routes and services.
"""

from __future__ import annotations
from decimal import Decimal

from uuid import UUID
from datetime import datetime
from typing import Optional
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.schemas.order import OrderDetailResponse, ShippingAddressResponse


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
    registration_amount_due: Decimal
    registration_paid_at: datetime | None
    registration_payment_reference: str | None
    registration_paid_by: UUID | None
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
    per_page: int = Field(default=25, ge=1, le=100)
    total_pages: int = Field(default=1, ge=1)


class AdminOrderDetailResponse(OrderDetailResponse):
    """Read-only operational detail; never exposes checkout or guest-access secrets."""

    address: ShippingAddressResponse | None
    customer_name: str
    user_id: UUID | None
    commission: Decimal


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
    updated_at: datetime


class CODVerifyRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=500)
    expected_updated_at: AwareDatetime | None = None
    expected_expires_at: AwareDatetime | None = None

    @field_validator("note")
    @classmethod
    def normalize_cod_note(cls, value: str | None) -> str | None:
        """Keep the recorded decision note trimmed and free of control characters."""
        if value is None:
            return None
        value = value.strip()
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Use a COD note without control characters")
        return value or None


class CODDecisionResponse(BaseModel):
    order_id: UUID
    order_number: str
    status: str
    message: str


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
    updated_at:  datetime

    model_config = {"from_attributes": True}


# ── Settings ──────────────────────────────────────────────────────────────────

class UpdateSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_settings: PlatformSettingsResponse | None = None
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
    sort_order: int | None = Field(default=None, ge=0, le=2_147_483_647)
    is_active: bool | None = None
    valid_from: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None
    expected_updated_at: AwareDatetime | None = None

    @field_validator("title")
    @classmethod
    def validate_banner_title(cls, value: str | None) -> str | None:
        """Keep banner headings usable after trimming."""
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Banner title cannot be blank")
        return value

    @field_validator("link_url")
    @classmethod
    def validate_banner_link(cls, value: str | None) -> str | None:
        """Allow local absolute paths or credential-free HTTPS destinations only."""
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if (
            any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
            or "\\" in value
        ):
            raise ValueError("Use an HTTPS or site-relative banner link")
        if value.startswith("/") and not value.startswith("//"):
            return value
        try:
            parsed = urlsplit(value)
            if (
                parsed.scheme == "https" and parsed.hostname
                and not parsed.username and not parsed.password
            ):
                _ = parsed.port
                return value
        except ValueError:
            pass
        raise ValueError("Use an HTTPS or site-relative banner link")


class SellerRegistrationPaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reference: str = Field(min_length=3, max_length=255)

    @field_validator("reference")
    @classmethod
    def validate_reference(cls, value: str) -> str:
        """Store a usable transfer reference without whitespace-only receipts."""
        value = value.strip()
        if len(value) < 3 or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Use a reference of 3-255 characters without control characters")
        return value

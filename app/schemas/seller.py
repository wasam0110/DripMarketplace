from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional
import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ── Registration ───────────────────────────────────────────────────────────────

class SellerRegistrationRequest(BaseModel):
    email:            EmailStr
    password:         str          = Field(min_length=8, max_length=128)
    first_name:       str          = Field(min_length=1, max_length=100)
    last_name:        Optional[str] = Field(default=None, max_length=100)
    brand_name:       str          = Field(min_length=2, max_length=100)
    description:      str          = Field(min_length=10, max_length=2000)
    return_policy:    str          = Field(min_length=10, max_length=1000)
    whatsapp_number:  str          = Field(max_length=20)
    instagram_handle: Optional[str] = Field(default=None, max_length=100)
    extra_slots:      int          = Field(default=0, ge=0, le=10_000)

    @field_validator("whatsapp_number")
    @classmethod
    def validate_pk_phone(cls, v: str) -> str:
        if not re.match(r"^(\+92|0)?3[0-9]{9}$", v):
            raise ValueError("Must be a valid Pakistani mobile number (03XXXXXXXXX or +923XXXXXXXXX)")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


class SellerRegistrationResponse(BaseModel):
    seller_id: UUID
    message:   str


# ── Slot Pricing ───────────────────────────────────────────────────────────────

class SlotPricingResponse(BaseModel):
    registration_fee: int = 5000
    base_slots:       int = 50
    extra_slots:      int
    extra_slot_price: int = 50
    extra_cost:       int
    total_cost:       int
    total_slots:      int


class SlotPurchaseRequest(BaseModel):
    quantity:       int = Field(ge=1, le=10_000)
    payment_method: str = Field(pattern="^(jazzcash|easypaisa|wallet)$")


class SlotPurchaseResponse(BaseModel):
    slots_purchased:     int
    new_total_slots:     int
    new_slots_available: int
    amount_charged:      int


# ── Profile ───────────────────────────────────────────────────────────────────

class SellerProfileResponse(BaseModel):
    id:               UUID
    brand_name:       str
    slug:             str
    description:      Optional[str]
    logo_url:         Optional[str]
    brand_color:      str
    return_policy:    Optional[str]
    whatsapp_number:  Optional[str]
    instagram_handle: Optional[str]
    status:           str
    total_slots:      int
    slots_used:       int
    slots_available:  int
    joined_at:        datetime

    model_config = {"from_attributes": True}


class SellerProfileUpdateRequest(BaseModel):
    description:      Optional[str] = Field(default=None, max_length=2000)
    return_policy:    Optional[str] = Field(default=None, max_length=1000)
    whatsapp_number:  Optional[str] = Field(default=None, max_length=20)
    instagram_handle: Optional[str] = Field(default=None, max_length=100)
    brand_color:      Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")

    @model_validator(mode="after")
    def at_least_one_field(self) -> "SellerProfileUpdateRequest":
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided")
        return self


class LogoUploadResponse(BaseModel):
    logo_url: str


# ── Dashboard ─────────────────────────────────────────────────────────────────

class OrderStatusBreakdown(BaseModel):
    pending:    int = 0
    processing: int = 0
    shipped:    int = 0
    delivered:  int = 0
    cancelled:  int = 0


class SellerDashboardResponse(BaseModel):
    period:            str
    gross_revenue:     int
    commission_paid:   int
    net_earnings:      int
    order_count:       int
    product_count:     int
    slots_used:        int
    slots_available:   int
    pending_balance:   int
    available_balance: int
    status_breakdown:  OrderStatusBreakdown


# ── Orders (shapes only — logic wired in Block 5) ─────────────────────────────

class SellerOrderRow(BaseModel):
    id:             UUID
    order_number:   str
    status:         str
    subtotal:       int
    net_amount:     int
    payment_method: str
    cod_verified:   bool
    item_count:     int
    created_at:     datetime

    model_config = {"from_attributes": True}


class ShippingAddressSchema(BaseModel):
    street:   str
    city:     str
    province: str


class OrderItemSchema(BaseModel):
    product_name:      str
    variant_label:     str
    unit_price:        int
    quantity:          int
    subtotal:          int


class SellerOrderDetailResponse(SellerOrderRow):
    customer_name:     str
    customer_phone:    str
    shipping_address:  ShippingAddressSchema
    items:             list[OrderItemSchema]
    tracking_number:   Optional[str]
    courier_name:      Optional[str]
    commission_rate:   float
    commission_amount: int


class UpdateOrderStatusRequest(BaseModel):
    status:          str = Field(pattern="^(processing|shipped|delivered)$")
    tracking_number: Optional[str] = Field(default=None, max_length=100)
    courier_name:    Optional[str] = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def tracking_required_for_shipped(self) -> "UpdateOrderStatusRequest":
        if self.status == "shipped" and not self.tracking_number:
            raise ValueError("tracking_number is required when status is 'shipped'")
        return self


# ── Bank Accounts ─────────────────────────────────────────────────────────────

class CreateBankAccountRequest(BaseModel):
    bank_name:        Optional[str] = Field(default=None, max_length=100)
    account_title:    Optional[str] = Field(default=None, max_length=200)
    account_number:   Optional[str] = Field(default=None, max_length=50)
    jazzcash_number:  Optional[str] = Field(default=None, max_length=20)
    easypaisa_number: Optional[str] = Field(default=None, max_length=20)
    is_default:       bool = False

    @model_validator(mode="after")
    def at_least_one_payment_method(self) -> "CreateBankAccountRequest":
        has_bank = bool(self.bank_name and self.account_number)
        has_jazz = bool(self.jazzcash_number)
        has_easy = bool(self.easypaisa_number)
        if not (has_bank or has_jazz or has_easy):
            raise ValueError(
                "Provide either (bank_name + account_number), jazzcash_number, or easypaisa_number"
            )
        return self


class BankAccountResponse(BaseModel):
    id:               UUID
    bank_name:        Optional[str]
    account_title:    Optional[str]
    account_number:   Optional[str]
    jazzcash_number:  Optional[str]
    easypaisa_number: Optional[str]
    is_default:       bool
    created_at:       datetime

    model_config = {"from_attributes": True}


# ── Analytics (shape only — data wired in Block 10) ───────────────────────────

class RevenueDayRow(BaseModel):
    date:        str
    gross:       int
    commission:  int
    net:         int
    order_count: int


class RevenueAnalyticsResponse(BaseModel):
    period:      str
    granularity: str
    data:        list[RevenueDayRow]


# ── Pagination ────────────────────────────────────────────────────────────────

class PagePagination(BaseModel):
    page:        int
    per_page:    int
    total:       int
    total_pages: int


class PaginatedSellerOrders(BaseModel):
    data:       list[SellerOrderRow]
    pagination: PagePagination
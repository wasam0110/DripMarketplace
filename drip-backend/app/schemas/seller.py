from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Annotated, Optional, Literal
import re

from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator, model_validator

from app.schemas.money import PKRResponseAmount


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
    amount_due: Decimal = Decimal("5000.00")
    seller_id: UUID
    message:   str


# ── Slot Pricing ───────────────────────────────────────────────────────────────

SlotMoney = Annotated[
    Decimal,
    Field(ge=0, decimal_places=2, allow_inf_nan=False,
          description="PKR major units, serialized as a two-decimal string; not integer paisa."),
]


class SlotPricingResponse(BaseModel):
    registration_fee: SlotMoney = Decimal("5000.00")
    base_slots:       int = 50
    extra_slots:      int
    extra_slot_price: SlotMoney = Decimal("50.00")
    extra_cost:       SlotMoney
    total_cost:       SlotMoney
    total_slots:      int

    @field_serializer(
        "registration_fee", "extra_slot_price", "extra_cost", "total_cost", when_used="json"
    )
    def serialize_money(self, value: Decimal) -> str:
        return format(value, ".2f")


class SlotPurchaseRequest(BaseModel):
    quantity:       int = Field(ge=1, le=10_000)
    payment_method: Literal["wallet"]


class SlotPurchaseResponse(BaseModel):
    slots_purchased:     int
    new_total_slots:     int
    new_slots_available: int
    amount_charged:      SlotMoney

    @field_serializer("amount_charged", when_used="json")
    def serialize_money(self, value: Decimal) -> str:
        return format(value, ".2f")


# ── Profile ───────────────────────────────────────────────────────────────────

class SellerProfileResponse(BaseModel):
    registration_amount_due: Decimal = Decimal("5000.00")
    registration_paid_at: datetime | None = None
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
    returned:   int = 0


class SellerDashboardResponse(BaseModel):
    period:            str
    gross_revenue:     Decimal
    commission_paid:   Decimal
    net_earnings:      Decimal
    order_count:       int
    product_count:     int
    slots_used:        int
    slots_available:   int
    pending_balance:   Decimal
    available_balance: Decimal
    status_breakdown:  OrderStatusBreakdown


# ── Seller fulfilment reads (the existing live payload) ────────────────────────

class SellerOrderRow(BaseModel):
    id:             UUID
    order_id:       UUID
    order_number:   str
    status:         str
    subtotal:       PKRResponseAmount
    tracking_number: Optional[str]
    courier_name:    Optional[str]
    shipped_at:      Optional[datetime]
    delivered_at:    Optional[datetime]
    created_at:     datetime

    model_config = {"from_attributes": True}

    @field_serializer("shipped_at", "delivered_at", "created_at", when_used="json")
    def serialize_order_time(self, value: datetime | None) -> str | None:
        # Keep the existing service's ISO offset spelling (including +00:00, not Z).
        return value.isoformat() if value is not None else None


class ShippingAddressSchema(BaseModel):
    recipient_name: str
    phone:    str
    street:   str
    city:     str
    province: str
    note:     Optional[str]


class OrderItemSchema(BaseModel):
    product_name:      str
    variant_label:     str
    unit_price:        PKRResponseAmount
    quantity:          int
    subtotal:          PKRResponseAmount


class SellerOrderDetailResponse(SellerOrderRow):
    shipping_address:  ShippingAddressSchema
    items:             list[OrderItemSchema]


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
    is_default:       bool = False

    @model_validator(mode="after")
    def at_least_one_payment_method(self) -> "CreateBankAccountRequest":
        if not (self.bank_name and self.account_number):
            raise ValueError(
                "Provide both bank_name and account_number"
            )
        return self


class BankAccountResponse(BaseModel):
    id:               UUID
    bank_name:        Optional[str]
    account_title:    Optional[str]
    account_number:   Optional[str]
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

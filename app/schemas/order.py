from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
import re


# ── Address ───────────────────────────────────────────────────────────────────

class ShippingAddressInput(BaseModel):
    recipient_name: str  = Field(min_length=2, max_length=200)
    phone:          str  = Field(max_length=20)
    street:         str  = Field(min_length=5, max_length=500)
    city:           str  = Field(min_length=2, max_length=100)
    province:       str  = Field(min_length=2, max_length=100)
    note:           Optional[str] = Field(default=None, max_length=500)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^(\+92|0)?3[0-9]{9}$", v):
            raise ValueError("Must be a valid Pakistani mobile number")
        return v


class ShippingAddressResponse(BaseModel):
    recipient_name: str
    phone:          str
    street:         str
    city:           str
    province:       str
    note:           Optional[str]

    model_config = {"from_attributes": True}


# ── Cart ──────────────────────────────────────────────────────────────────────

class CartItemInput(BaseModel):
    variant_id: UUID
    quantity:   int = Field(ge=1, le=100)


class CartItemResponse(BaseModel):
    variant_id:   UUID
    product_id:   UUID
    product_name: str
    brand_name:   str
    brand_color:  str
    primary_image: Optional[str]
    size:         str
    colour:       str
    unit_price:   int
    quantity:     int
    subtotal:     int
    available_stock: int
    seller_id:    UUID


class SellerCartGroup(BaseModel):
    seller_id:   UUID
    brand_name:  str
    brand_color: str
    items:       list[CartItemResponse]
    group_subtotal: int


class CartResponse(BaseModel):
    items:             list[CartItemResponse]
    grouped_by_seller: list[SellerCartGroup]
    item_count:        int
    subtotal:          int
    shipping_fee:      int
    total:             int


class AddToCartRequest(BaseModel):
    variant_id: UUID
    quantity:   int = Field(ge=1, le=100)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=0, le=100)


class SyncCartRequest(BaseModel):
    items: list[CartItemInput]


# ── Order creation ────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    """For authenticated users — items come from Redis cart."""
    shipping_address: ShippingAddressInput
    payment_method:   str = Field(pattern="^(jazzcash|easypaisa|card|cod)$")
    coupon_code:      Optional[str] = Field(default=None, max_length=30)
    notes:            Optional[str] = Field(default=None, max_length=500)


class CreateGuestOrderRequest(CreateOrderRequest):
    """Guest checkout — must supply items and personal details."""
    guest_email: EmailStr
    guest_name:  str  = Field(min_length=2, max_length=200)
    guest_phone: str  = Field(max_length=20)
    items:       list[CartItemInput] = Field(min_length=1)

    @field_validator("guest_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^(\+92|0)?3[0-9]{9}$", v):
            raise ValueError("Must be a valid Pakistani mobile number")
        return v


class CreateOrderResponse(BaseModel):
    order_id:      UUID
    order_number:  str
    status:        str
    total:         int
    payment_method: str
    payment_url:   Optional[str] = None   # JazzCash/Easypaisa/Stripe — wired in Block 6
    whatsapp_url:  Optional[str] = None   # COD verification link


# ── Order detail ──────────────────────────────────────────────────────────────

class OrderItemResponse(BaseModel):
    id:            UUID
    seller_id:     UUID
    product_id:    UUID
    variant_id:    UUID
    product_name:  str
    variant_label: str
    unit_price:    int
    quantity:      int
    subtotal:      int

    model_config = {"from_attributes": True}


class SellerOrderResponse(BaseModel):
    id:              UUID
    seller_id:       UUID
    brand_name:      str
    status:          str
    subtotal:        int
    tracking_number: Optional[str]
    courier_name:    Optional[str]
    shipped_at:      Optional[datetime]
    delivered_at:    Optional[datetime]

    model_config = {"from_attributes": True}


class OrderDetailResponse(BaseModel):
    id:              UUID
    order_number:    str
    status:          str
    payment_method:  str
    subtotal:        int
    discount_amount: int
    shipping_fee:    int
    total:           int
    notes:           Optional[str]
    address:         ShippingAddressResponse
    items:           list[OrderItemResponse]
    seller_orders:   list[SellerOrderResponse]
    created_at:      datetime

    model_config = {"from_attributes": True}


class OrderRowResponse(BaseModel):
    id:           UUID
    order_number: str
    status:       str
    total:        int
    item_count:   int
    created_at:   datetime

    model_config = {"from_attributes": True}


class PageInfo(BaseModel):
    page:        int
    per_page:    int
    total:       int
    total_pages: int


class PaginatedOrders(BaseModel):
    data:       list[OrderRowResponse]
    pagination: PageInfo


# ── Cancel ────────────────────────────────────────────────────────────────────

class CancelOrderRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


# ── Coupon ────────────────────────────────────────────────────────────────────

class ValidateCouponRequest(BaseModel):
    code:     str = Field(min_length=1, max_length=30)
    subtotal: int = Field(ge=1)


class CouponValidationResponse(BaseModel):
    code:            str
    discount_type:   str
    discount_value:  int
    discount_amount: int
    new_subtotal:    int


# ── Seller order management ───────────────────────────────────────────────────

class UpdateSellerOrderRequest(BaseModel):
    status:          str = Field(pattern="^(processing|shipped|delivered)$")
    tracking_number: Optional[str] = Field(default=None, max_length=100)
    courier_name:    Optional[str] = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def tracking_required_for_shipped(self) -> "UpdateSellerOrderRequest":
        if self.status == "shipped" and not self.tracking_number:
            raise ValueError("tracking_number required when status is 'shipped'")
        return self


# ── Tracking (public, no auth) ────────────────────────────────────────────────

class OrderTrackingResponse(BaseModel):
    order_number:  str
    status:        str
    seller_orders: list[SellerOrderResponse]
    created_at:    datetime
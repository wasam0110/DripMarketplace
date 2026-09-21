"""
app/schemas/user.py
────────────────────
Pydantic v2 schemas for the Customer / User API.

  - Profile read/update
  - Address CRUD
  - Review CRUD
  - Wishlist
  - Account settings
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import field_validator, model_validator

from app.schemas.common import DRIPBaseModel, DRIPResponseModel

_PHONE = re.compile(r"^(\+92|0092|0)?3[0-9]{9}$")


# ── Profile ───────────────────────────────────────────────────────────────────

class UserProfileResponse(DRIPResponseModel):
    id:                  UUID
    email:               str
    first_name:          Optional[str]
    last_name:           Optional[str]
    phone:               Optional[str]
    avatar_url:          Optional[str]
    has_verified_email:  bool
    is_2fa_enabled:      bool
    last_login_at:       Optional[datetime]
    created_at:          datetime


class UpdateProfileRequest(DRIPBaseModel):
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    phone:      Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 1 or len(v) > 100:
            raise ValueError("Name must be between 1 and 100 characters.")
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError("Name contains invalid characters.")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not _PHONE.match(v):
            raise ValueError("Enter a valid Pakistani mobile number (03XXXXXXXXX).")
        return v


class ChangePasswordRequest(DRIPBaseModel):
    current_password: str
    new_password:     str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(v) > 128:
            raise ValueError("Password is too long (max 128 characters).")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number.")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match.")
        return self


class AvatarUploadResponse(DRIPResponseModel):
    avatar_url: str


# ── Addresses ─────────────────────────────────────────────────────────────────

class AddressResponse(DRIPResponseModel):
    id:         UUID
    label:      Optional[str]
    street:     str
    city:       str
    province:   str
    is_default: bool
    created_at: datetime


class CreateAddressRequest(DRIPBaseModel):
    label:      Optional[str] = None
    street:     str
    city:       str
    province:   str
    is_default: bool = False

    @field_validator("street")
    @classmethod
    def validate_street(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Street address must be at least 10 characters.")
        if len(v) > 500:
            raise ValueError("Street address is too long (max 500 characters).")
        return v

    @field_validator("city", "province")
    @classmethod
    def validate_location(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Must be at least 2 characters.")
        if len(v) > 100:
            raise ValueError("Too long (max 100 characters).")
        return v

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 50:
            raise ValueError("Label is too long (max 50 characters).")
        return v


class UpdateAddressRequest(DRIPBaseModel):
    label:      Optional[str]  = None
    street:     Optional[str]  = None
    city:       Optional[str]  = None
    province:   Optional[str]  = None
    is_default: Optional[bool] = None


# ── Reviews ───────────────────────────────────────────────────────────────────

class ReviewImageResponse(DRIPResponseModel):
    id:         UUID
    url:        str
    sort_order: int


class ReviewAuthorResponse(DRIPResponseModel):
    id:         UUID
    first_name: Optional[str]
    last_name:  Optional[str]
    avatar_url: Optional[str]


class ReviewResponse(DRIPResponseModel):
    id:                   UUID
    user:                 ReviewAuthorResponse
    product_id:           UUID
    rating:               int
    title:                Optional[str]
    body:                 Optional[str]
    status:               str
    is_verified_purchase: bool
    helpful_count:        int
    unhelpful_count:      int
    images:               list[ReviewImageResponse]
    created_at:           datetime
    updated_at:           datetime


class CreateReviewRequest(DRIPBaseModel):
    product_id: UUID
    order_id:   Optional[UUID] = None
    rating:     int
    title:      Optional[str]  = None
    body:       Optional[str]  = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5.")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 200:
            raise ValueError("Title must be 200 characters or fewer.")
        return v

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("Review body must be 2000 characters or fewer.")
        return v


class UpdateReviewRequest(DRIPBaseModel):
    rating: Optional[int] = None
    title:  Optional[str] = None
    body:   Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Rating must be between 1 and 5.")
        return v


class ReviewHelpfulRequest(DRIPBaseModel):
    helpful: bool  # True = helpful, False = unhelpful


class PaginatedReviews(DRIPResponseModel):
    data:     list[ReviewResponse]
    total:    int
    page:     int
    per_page: int
    pages:    int
    avg_rating: Optional[float]
    rating_breakdown: dict[int, int]   # {5: 42, 4: 18, ...}


# ── Wishlist ──────────────────────────────────────────────────────────────────

class WishlistItemResponse(DRIPResponseModel):
    id:            UUID
    product_id:    UUID
    product_name:  str
    product_slug:  str
    product_image: Optional[str]
    price:         int
    sale_price:    Optional[int]
    is_in_stock:   bool
    added_at:      datetime


class WishlistResponse(DRIPResponseModel):
    items: list[WishlistItemResponse]
    total: int


class AddToWishlistRequest(DRIPBaseModel):
    product_id: UUID


# ── Account settings ──────────────────────────────────────────────────────────

class NotificationPreferencesResponse(DRIPResponseModel):
    email_order_updates:  bool
    email_promotions:     bool
    email_new_arrivals:   bool
    sms_order_updates:    bool
    whatsapp_order_updates: bool


class UpdateNotificationPreferencesRequest(DRIPBaseModel):
    email_order_updates:    Optional[bool] = None
    email_promotions:       Optional[bool] = None
    email_new_arrivals:     Optional[bool] = None
    sms_order_updates:      Optional[bool] = None
    whatsapp_order_updates: Optional[bool] = None


class DeleteAccountRequest(DRIPBaseModel):
    password:       str
    confirm_phrase: str   # must equal "DELETE MY ACCOUNT"

    @field_validator("confirm_phrase")
    @classmethod
    def validate_phrase(cls, v: str) -> str:
        if v.strip() != "DELETE MY ACCOUNT":
            raise ValueError('Type "DELETE MY ACCOUNT" exactly to confirm.')
        return v.strip()

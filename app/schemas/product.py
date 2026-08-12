from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional
import re

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Variant ────────────────────────────────────────────────────────────────────

class CreateVariantRequest(BaseModel):
    size_type:      str     = Field(pattern="^(alpha|numeric|one_size)$")
    size_value:     str     = Field(min_length=1, max_length=10)
    colour:         str     = Field(min_length=1, max_length=50)
    stock:          int     = Field(ge=0)
    price_override: Optional[int] = Field(default=None, ge=100, le=500_000)
    sku:            Optional[str] = Field(default=None, max_length=100)


class VariantWithStockResponse(BaseModel):
    id:              UUID
    sku:             str
    size_type:       str
    size_value:      str
    colour:          str
    price:           int
    stock:           int
    available_stock: int
    is_active:       bool

    model_config = {"from_attributes": True}


# ── Product create / update ────────────────────────────────────────────────────

class CreateProductRequest(BaseModel):
    name:             str           = Field(min_length=2, max_length=200)
    description:      str           = Field(min_length=10, max_length=5000)
    price:            int           = Field(ge=100, le=500_000)
    sale_price:       Optional[int] = Field(default=None, ge=100, le=500_000)
    category_id:      Optional[UUID] = None
    is_published:     bool          = False
    meta_title:       Optional[str] = Field(default=None, max_length=200)
    meta_description: Optional[str] = Field(default=None, max_length=500)
    variants:         list[CreateVariantRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def sale_must_be_less_than_price(self) -> "CreateProductRequest":
        if self.sale_price and self.sale_price >= self.price:
            raise ValueError("sale_price must be less than price")
        return self


class UpdateProductRequest(BaseModel):
    name:             Optional[str] = Field(default=None, min_length=2, max_length=200)
    description:      Optional[str] = Field(default=None, min_length=10, max_length=5000)
    price:            Optional[int] = Field(default=None, ge=100, le=500_000)
    sale_price:       Optional[int] = Field(default=None, ge=100, le=500_000)
    category_id:      Optional[UUID] = None
    meta_title:       Optional[str] = Field(default=None, max_length=200)
    meta_description: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def at_least_one(self) -> "UpdateProductRequest":
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided")
        return self


# ── Images ────────────────────────────────────────────────────────────────────

class ProductImageResponse(BaseModel):
    id:         UUID
    url:        str
    alt_text:   Optional[str]
    sort_order: int
    is_primary: bool

    model_config = {"from_attributes": True}


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryResponse(BaseModel):
    id:   UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


# ── Seller summary ────────────────────────────────────────────────────────────

class SellerSummaryResponse(BaseModel):
    id:              UUID
    brand_name:      str
    slug:            str
    logo_url:        Optional[str]
    brand_color:     str
    return_policy:   Optional[str]
    whatsapp_number: Optional[str]
    avg_rating:      float = 0.0

    model_config = {"from_attributes": True}


# ── Public catalogue ──────────────────────────────────────────────────────────

class ProductCardResponse(BaseModel):
    id:            UUID
    seller_id:     UUID
    brand_name:    str
    brand_color:   str
    name:          str
    slug:          str
    price:         int
    sale_price:    Optional[int]
    primary_image: Optional[str]
    colours:       list[str]
    alpha_sizes:   list[str]
    numeric_sizes: list[str]
    avg_rating:    float
    review_count:  int
    is_new:        bool
    has_stock:     bool

    model_config = {"from_attributes": True}


class ProductDetailResponse(ProductCardResponse):
    description:      Optional[str]
    meta_title:       Optional[str]
    meta_description: Optional[str]
    images:           list[ProductImageResponse]
    variants:         list[VariantWithStockResponse]
    seller:           SellerSummaryResponse
    category:         Optional[CategoryResponse]
    created_at:       datetime


class CursorPagination(BaseModel):
    next_cursor: Optional[str]
    has_next:    bool
    limit:       int


class CataloguePage(BaseModel):
    data:       list[ProductCardResponse]
    pagination: CursorPagination


# ── Seller product management ─────────────────────────────────────────────────

class SellerProductRowResponse(BaseModel):
    id:           UUID
    name:         str
    slug:         str
    category:     Optional[str]
    price:        int
    total_stock:  int
    is_published: bool
    avg_rating:   float
    review_count: int
    image_count:  int

    model_config = {"from_attributes": True}


class SlotInfoResponse(BaseModel):
    total_slots:     int
    slots_used:      int
    slots_available: int


class SellerProductsPage(BaseModel):
    data:      list[SellerProductRowResponse]
    slot_info: SlotInfoResponse


class UploadImagesResponse(BaseModel):
    images: list[ProductImageResponse]


# ── Search ────────────────────────────────────────────────────────────────────

class SearchSuggestion(BaseModel):
    id:            UUID
    name:          str
    primary_image: Optional[str]
    price:         int
    brand_name:    str


class BrandSuggestion(BaseModel):
    id:         UUID
    brand_name: str
    logo_url:   Optional[str]
    slug:       str


class SearchSuggestionsResponse(BaseModel):
    products: list[SearchSuggestion]
    brands:   list[BrandSuggestion]
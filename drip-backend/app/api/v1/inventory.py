"""
app/api/v1/inventory.py
────────────────────────
Inventory management endpoints.

Seller routes:
  - GET  /inventory                 — list all variants with stock levels
  - GET  /inventory/{variant_id}    — single variant stock detail
  - PUT  /inventory/{variant_id}    — set absolute stock
  - POST /inventory/{variant_id}/adjust — relative stock adjustment (+/-)
  - GET  /inventory/low-stock       — variants below reorder threshold

Admin routes:
  - GET  /admin/inventory           — platform-wide stock view (all sellers)
  - POST /admin/inventory/bulk-update — bulk stock correction
"""

from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import field_validator

from app.api.deps import get_db, CurrentSeller, CurrentAdmin
from app.schemas.common import DRIPBaseModel, DRIPResponseModel
from app.repositories.inventory_repo import InventoryRepository

router = APIRouter(tags=["inventory"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ── Schemas (inline — inventory-specific, no shared domain) ──────────────────

class VariantStockResponse(DRIPResponseModel):
    variant_id:       UUID
    product_id:       UUID
    product_name:     str
    sku:              Optional[str]
    size:             Optional[str]
    colour:           Optional[str]
    stock:            int
    reserved:         int
    available:        int           # stock - reserved
    reorder_point:    int
    is_low_stock:     bool
    last_restocked_at: Optional[str]


class PaginatedVariantStock(DRIPResponseModel):
    data:      list[VariantStockResponse]
    total:     int
    page:      int
    per_page:  int
    pages:     int


class SetStockRequest(DRIPBaseModel):
    stock:         int
    reorder_point: Optional[int] = None

    @field_validator("stock")
    @classmethod
    def stock_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Stock cannot be negative.")
        if v > 999_999:
            raise ValueError("Stock cannot exceed 999,999 units.")
        return v

    @field_validator("reorder_point")
    @classmethod
    def reorder_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Reorder point cannot be negative.")
        return v


class AdjustStockRequest(DRIPBaseModel):
    delta:  int     # positive = add, negative = remove
    reason: str

    @field_validator("delta")
    @classmethod
    def delta_in_range(cls, v: int) -> int:
        if v == 0:
            raise ValueError("Delta cannot be zero.")
        if abs(v) > 10_000:
            raise ValueError("Adjustment cannot exceed ±10,000 units.")
        return v

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Reason must be at least 3 characters.")
        if len(v) > 200:
            raise ValueError("Reason must be 200 characters or fewer.")
        return v


class StockAdjustmentResponse(DRIPResponseModel):
    variant_id:    UUID
    previous_stock: int
    new_stock:     int
    delta:         int
    reason:        str


class BulkStockUpdateItem(DRIPBaseModel):
    variant_id: UUID
    stock:      int
    reason:     Optional[str] = None

    @field_validator("stock")
    @classmethod
    def stock_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Stock cannot be negative.")
        return v


class BulkStockUpdateRequest(DRIPBaseModel):
    updates: list[BulkStockUpdateItem]

    @field_validator("updates")
    @classmethod
    def validate_updates(cls, v: list) -> list:
        if len(v) == 0:
            raise ValueError("At least one update is required.")
        if len(v) > 500:
            raise ValueError("Cannot update more than 500 variants at once.")
        return v


class BulkStockUpdateResponse(DRIPResponseModel):
    updated:  int
    failed:   int
    errors:   list[dict]    # [{variant_id, error}]


class LowStockResponse(DRIPResponseModel):
    data:  list[VariantStockResponse]
    total: int


# ══════════════════════════════════════════════════════════════════════════════
# SELLER — Inventory management for own products
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/seller/inventory", response_model=PaginatedVariantStock)
async def list_seller_inventory(
    db:             DB,
    current_seller: CurrentSeller,
    product_id:     Optional[UUID] = Query(default=None),
    low_stock_only: bool           = Query(default=False),
    q:              Optional[str]  = Query(default=None, max_length=100),
    page:           int            = Query(default=1, ge=1),
    per_page:       int            = Query(default=50, ge=1, le=200),
) -> PaginatedVariantStock:
    """
    List all product variants and their current stock levels for the
    authenticated seller.
    """
    from app.services.inventory_service import InventoryService
    return await InventoryService(db).list_seller_inventory(
        seller_id=current_seller["seller_id"],
        product_id=product_id,
        low_stock_only=low_stock_only,
        q=q,
        page=page,
        per_page=per_page,
    )


@router.get("/seller/inventory/low-stock", response_model=LowStockResponse)
async def get_low_stock_alerts(
    db:             DB,
    current_seller: CurrentSeller,
) -> LowStockResponse:
    """
    Return all variants whose current stock is at or below the reorder point.
    Useful for restock dashboard widget.
    """
    from app.services.inventory_service import InventoryService
    return await InventoryService(db).get_low_stock(seller_id=current_seller["seller_id"])


@router.get("/seller/inventory/{variant_id}", response_model=VariantStockResponse)
async def get_variant_stock(
    variant_id:     UUID,
    db:             DB,
    current_seller: CurrentSeller,
) -> VariantStockResponse:
    """Get stock details for a single variant owned by this seller."""
    from app.services.inventory_service import InventoryService
    return await InventoryService(db).get_variant_stock(
        variant_id=variant_id, seller_id=current_seller["seller_id"]
    )


@router.put("/seller/inventory/{variant_id}", response_model=VariantStockResponse)
async def set_variant_stock(
    variant_id:     UUID,
    payload:        SetStockRequest,
    db:             DB,
    current_seller: CurrentSeller,
) -> VariantStockResponse:
    """
    Set the absolute stock quantity for a variant. Use this for manual stock
    corrections after a physical count.
    """
    from app.services.inventory_service import InventoryService
    return await InventoryService(db).set_stock(
        variant_id=variant_id,
        seller_id=current_seller["seller_id"],
        stock=payload.stock,
        reorder_point=payload.reorder_point,
    )


@router.post("/seller/inventory/{variant_id}/adjust", response_model=StockAdjustmentResponse)
async def adjust_variant_stock(
    variant_id:     UUID,
    payload:        AdjustStockRequest,
    db:             DB,
    current_seller: CurrentSeller,
) -> StockAdjustmentResponse:
    """
    Apply a relative stock adjustment (e.g. +50 for a restock, -3 for
    a damaged-goods writeoff). Negative delta cannot take stock below 0.
    """
    from app.services.inventory_service import InventoryService
    return await InventoryService(db).adjust_stock(
        variant_id=variant_id,
        seller_id=current_seller["seller_id"],
        delta=payload.delta,
        reason=payload.reason,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — Platform-wide inventory view
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/inventory", response_model=PaginatedVariantStock)
async def admin_list_inventory(
    db:            DB,
    current_admin: CurrentAdmin,
    seller_id:     Optional[UUID] = Query(default=None),
    product_id:    Optional[UUID] = Query(default=None),
    low_stock_only: bool          = Query(default=False),
    q:             Optional[str]  = Query(default=None, max_length=100),
    page:          int            = Query(default=1, ge=1),
    per_page:      int            = Query(default=50, ge=1, le=200),
) -> PaginatedVariantStock:
    """Admin: View inventory across all sellers with optional filters."""
    from app.services.inventory_service import InventoryService
    return await InventoryService(db).admin_list_inventory(
        seller_id=seller_id,
        product_id=product_id,
        low_stock_only=low_stock_only,
        q=q,
        page=page,
        per_page=per_page,
    )


@router.post("/admin/inventory/bulk-update", response_model=BulkStockUpdateResponse)
async def admin_bulk_update_inventory(
    payload:       BulkStockUpdateRequest,
    db:            DB,
    current_admin: CurrentAdmin,
) -> BulkStockUpdateResponse:
    """
    Admin: Bulk-correct stock levels across any variants. Used after CSV
    import or a multi-seller warehouse audit. Errors are collected and
    returned rather than rolling back the whole batch.
    """
    from app.services.inventory_service import InventoryService
    return await InventoryService(db).bulk_update_stock(updates=payload.updates)

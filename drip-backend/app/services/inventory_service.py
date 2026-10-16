"""
app/services/inventory_service.py
───────────────────────────────────
Business logic for inventory management:
  - List, get, set, and adjust stock for product variants
  - Low-stock alert queries
  - Admin bulk-update

Note: Stock lives in ProductInventory (one-to-one with ProductVariant).
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.core.logging import get_logger
from app.models.product import Product, ProductVariant, ProductInventory
from app.repositories.inventory_repo import InventoryRepository

logger = get_logger(__name__)



class InventoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db   = db
        self.repo = InventoryRepository(db)

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _get_inventory_for_seller(
        self, variant_id: uuid.UUID, seller_id: uuid.UUID
    ) -> tuple[ProductInventory, ProductVariant, Product]:
        """Load inventory + variant + product, assert seller ownership."""
        stmt = (
            select(ProductInventory, ProductVariant, Product)
            .join(ProductVariant, ProductVariant.id == ProductInventory.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(
                ProductInventory.variant_id == variant_id,
                Product.seller_id == seller_id,
                Product.deleted_at.is_(None),
            )
        )
        row = (await self.db.execute(stmt.with_for_update(of=ProductInventory))).first()
        if row is None:
            raise NotFoundError("ProductVariant")
        return row.ProductInventory, row.ProductVariant, row.Product

    @staticmethod
    def _to_schema(
        inv: ProductInventory,
        variant: ProductVariant,
        product: Product,
    ) -> dict:
        available = inv.stock - inv.reserved
        return dict(
            variant_id=variant.id,
            product_id=variant.product_id,
            product_name=product.name,
            sku=variant.sku,
            size=variant.size_value,
            colour=variant.colour,
            stock=inv.stock,
            reserved=inv.reserved,
            available=available,
            reorder_point=inv.reorder_point,
            is_low_stock=available <= inv.reorder_point,
            last_restocked_at=inv.updated_at.isoformat() if inv.updated_at else None,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SELLER ENDPOINTS
    # ══════════════════════════════════════════════════════════════════════════

    async def list_seller_inventory(
        self,
        seller_id:      uuid.UUID,
        product_id:     Optional[uuid.UUID],
        low_stock_only: bool,
        q:              Optional[str],
        page:           int,
        per_page:       int,
    ):
        from app.api.v1.inventory import PaginatedVariantStock, VariantStockResponse

        stmt = (
            select(ProductInventory, ProductVariant, Product)
            .join(ProductVariant, ProductVariant.id == ProductInventory.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(Product.seller_id == seller_id, Product.deleted_at.is_(None))
        )
        if product_id:
            stmt = stmt.where(ProductVariant.product_id == product_id)
        if q:
            stmt = stmt.where(
                Product.name.ilike(f"%{q}%") | ProductVariant.sku.ilike(f"%{q}%")
            )
        if low_stock_only:
            stmt = stmt.where(
                (ProductInventory.stock - ProductInventory.reserved) <= ProductInventory.reorder_point
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * per_page
        rows   = (await self.db.execute(stmt.offset(offset).limit(per_page))).all()

        data = [
            VariantStockResponse(**self._to_schema(row.ProductInventory, row.ProductVariant, row.Product))
            for row in rows
        ]
        return PaginatedVariantStock(
            data=data, total=total, page=page, per_page=per_page,
            pages=math.ceil(total / per_page) if total else 0,
        )

    async def get_low_stock(self, seller_id: uuid.UUID):
        from app.api.v1.inventory import LowStockResponse, VariantStockResponse

        stmt = (
            select(ProductInventory, ProductVariant, Product)
            .join(ProductVariant, ProductVariant.id == ProductInventory.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(
                Product.seller_id == seller_id,
                Product.deleted_at.is_(None),
                (ProductInventory.stock - ProductInventory.reserved) <= ProductInventory.reorder_point,
            )
            .order_by((ProductInventory.stock - ProductInventory.reserved).asc())
        )
        rows = (await self.db.execute(stmt)).all()
        data = [
            VariantStockResponse(**self._to_schema(row.ProductInventory, row.ProductVariant, row.Product))
            for row in rows
        ]
        return LowStockResponse(data=data, total=len(data))

    async def get_variant_stock(self, variant_id: uuid.UUID, seller_id: uuid.UUID):
        from app.api.v1.inventory import VariantStockResponse

        inv, variant, product = await self._get_inventory_for_seller(variant_id, seller_id)
        return VariantStockResponse(**self._to_schema(inv, variant, product))

    async def set_stock(
        self,
        variant_id:    uuid.UUID,
        seller_id:     uuid.UUID,
        stock:         int,
        reorder_point: Optional[int],
    ):
        from app.api.v1.inventory import VariantStockResponse

        inv, variant, product = await self._get_inventory_for_seller(variant_id, seller_id)
        if stock < inv.reserved:
            raise BusinessRuleError("Stock cannot fall below reserved units")
        if reorder_point is not None and not 0 <= reorder_point <= 999_999:
            raise BusinessRuleError("Reorder point must be between 0 and 999,999")
        values = {"stock": stock, "updated_at": datetime.now(UTC)}
        if reorder_point is not None:
            values["reorder_point"] = reorder_point
        await self.db.execute(
            update(ProductInventory)
            .where(ProductInventory.variant_id == variant_id)
            .values(**values)
        )
        await self.db.commit()
        await self.db.refresh(inv)
        logger.info("stock_set", variant_id=str(variant_id), new_stock=stock)
        return VariantStockResponse(**self._to_schema(inv, variant, product))

    async def adjust_stock(
        self,
        variant_id: uuid.UUID,
        seller_id:  uuid.UUID,
        delta:      int,
        reason:     str,
    ):
        from app.api.v1.inventory import StockAdjustmentResponse

        inv, variant, product = await self._get_inventory_for_seller(variant_id, seller_id)
        prev_stock = inv.stock
        new_stock  = prev_stock + delta

        if new_stock < inv.reserved:
            raise BusinessRuleError(
                f"Adjustment would fall below reserved stock "
                f"(current={prev_stock}, delta={delta})."
            )

        await self.db.execute(
            update(ProductInventory)
            .where(ProductInventory.variant_id == variant_id)
            .values(stock=new_stock, updated_at=datetime.now(UTC))
        )
        await self.db.commit()
        logger.info(
            "stock_adjusted",
            variant_id=str(variant_id), delta=delta,
            prev=prev_stock, new=new_stock, reason=reason,
        )
        return StockAdjustmentResponse(
            variant_id=variant_id,
            previous_stock=prev_stock,
            new_stock=new_stock,
            delta=delta,
            reason=reason,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # ADMIN
    # ══════════════════════════════════════════════════════════════════════════

    async def admin_list_inventory(
        self,
        seller_id:      Optional[uuid.UUID],
        product_id:     Optional[uuid.UUID],
        low_stock_only: bool,
        q:              Optional[str],
        page:           int,
        per_page:       int,
    ):
        from app.api.v1.inventory import PaginatedVariantStock, VariantStockResponse

        stmt = (
            select(ProductInventory, ProductVariant, Product)
            .join(ProductVariant, ProductVariant.id == ProductInventory.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(Product.deleted_at.is_(None))
        )
        if seller_id:
            stmt = stmt.where(Product.seller_id == seller_id)
        if product_id:
            stmt = stmt.where(ProductVariant.product_id == product_id)
        if q:
            stmt = stmt.where(
                Product.name.ilike(f"%{q}%") | ProductVariant.sku.ilike(f"%{q}%")
            )
        if low_stock_only:
            stmt = stmt.where(
                (ProductInventory.stock - ProductInventory.reserved) <= ProductInventory.reorder_point
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * per_page
        rows   = (await self.db.execute(stmt.offset(offset).limit(per_page))).all()

        data = [
            VariantStockResponse(**self._to_schema(row.ProductInventory, row.ProductVariant, row.Product))
            for row in rows
        ]
        return PaginatedVariantStock(
            data=data, total=total, page=page, per_page=per_page,
            pages=math.ceil(total / per_page) if total else 0,
        )

    async def bulk_update_stock(self, updates: list):
        from app.api.v1.inventory import BulkStockUpdateRequest, BulkStockUpdateResponse

        # Validate internal callers too, before any writes or row locks.
        batch = BulkStockUpdateRequest(updates=updates).updates
        updated = 0
        failures = {}
        try:
            # Overlapping bulk requests acquire row locks in the same order.
            for item in sorted(batch, key=lambda item: item.variant_id):
                try:
                    # PostgreSQL aborts a transaction after a statement error.
                    # Isolate recoverable row errors without losing earlier rows.
                    async with self.db.begin_nested():
                        result = await self.db.execute(
                            update(ProductInventory)
                            .where(
                                ProductInventory.variant_id == item.variant_id,
                                ProductInventory.reserved <= item.stock,
                            )
                            .values(stock=item.stock, updated_at=datetime.now(UTC))
                        )
                    if result.rowcount == 0:
                        failures[item.variant_id] = "Variant not found or stock is below reserved units"
                    else:
                        updated += 1
                except (IntegrityError, DataError):
                    failures[item.variant_id] = "Inventory update failed"
            await self.db.commit()
        except Exception:
            # Disconnects, deadlocks, programming errors and failed commits are
            # not ordinary row failures. Never report uncommitted successes.
            await self.db.rollback()
            raise

        errors = [
            {"variant_id": str(item.variant_id), "error": failures[item.variant_id]}
            for item in batch if item.variant_id in failures
        ]
        logger.info("bulk_stock_update", updated=updated, failed=len(errors))
        return BulkStockUpdateResponse(updated=updated, failed=len(errors), errors=errors)

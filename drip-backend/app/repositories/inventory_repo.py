"""repositories / inventory repo.

Database operations used by services within their transaction boundaries.
"""

from __future__ import annotations

from uuid import UUID
from typing import Optional
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import ProductInventory
from app.core.exceptions import BusinessRuleError


class InventoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        """Bind InventoryRepository to its injected dependencies for subsequent operations."""
        self.db = db

    async def create(self, variant_id: UUID, stock: int = 0) -> ProductInventory:
        """Insert a inventory record and return it within the caller's transaction."""
        inv = ProductInventory(variant_id=variant_id, stock=stock)
        self.db.add(inv)
        await self.db.flush()
        return inv

    async def get_by_variant(self, variant_id: UUID) -> Optional[ProductInventory]:
        """Look up a inventory record by variant; return None when absent."""
        result = await self.db.execute(
            select(ProductInventory).where(ProductInventory.variant_id == variant_id)
        )
        return result.scalar_one_or_none()

    async def update_stock(self, variant_id: UUID, stock: int) -> None:
        """Set on-hand inventory within the caller's transaction."""
        await self.db.execute(
            update(ProductInventory)
            .where(ProductInventory.variant_id == variant_id)
            .values(stock=stock, updated_at=datetime.utcnow())
        )

    async def reserve(self, variant_id: UUID, quantity: int) -> bool:
        """
        Atomically reserve stock. Returns False if insufficient stock.
        Called by order service (Block 5).
        """
        result = await self.db.execute(
            update(ProductInventory)
            .where(
                ProductInventory.variant_id == variant_id,
                ProductInventory.stock - ProductInventory.reserved >= quantity,
            )
            .values(
                reserved=ProductInventory.reserved + quantity,
                updated_at=datetime.utcnow(),
            )
            .returning(ProductInventory.id)
        )
        return result.scalar_one_or_none() is not None

    async def release(self, variant_id: UUID, quantity: int) -> None:
        """Release reserved stock back (order cancelled)."""
        await self.db.execute(
            update(ProductInventory)
            .where(
                ProductInventory.variant_id == variant_id,
                ProductInventory.reserved >= quantity,
            )
            .values(
                reserved=ProductInventory.reserved - quantity,
                updated_at=datetime.utcnow(),
            )
        )

    async def deduct(self, variant_id: UUID, quantity: int) -> None:
        """Deduct reserved → confirmed sale (order delivered)."""
        result = await self.db.execute(
            update(ProductInventory)
            .where(ProductInventory.variant_id == variant_id, ProductInventory.reserved >= quantity, ProductInventory.stock >= quantity)
            .values(
                stock=ProductInventory.stock - quantity,
                reserved=ProductInventory.reserved - quantity,
                updated_at=datetime.utcnow(),
            )
        )
        if result.rowcount != 1:
            raise BusinessRuleError("Reserved inventory is inconsistent; contact support")

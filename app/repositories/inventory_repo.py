from __future__ import annotations

from uuid import UUID
from typing import Optional
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import ProductInventory


class InventoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, variant_id: UUID, stock: int = 0) -> ProductInventory:
        inv = ProductInventory(variant_id=variant_id, stock=stock)
        self.db.add(inv)
        await self.db.flush()
        return inv

    async def get_by_variant(self, variant_id: UUID) -> Optional[ProductInventory]:
        result = await self.db.execute(
            select(ProductInventory).where(ProductInventory.variant_id == variant_id)
        )
        return result.scalar_one_or_none()

    async def update_stock(self, variant_id: UUID, stock: int) -> None:
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
        await self.db.execute(
            update(ProductInventory)
            .where(ProductInventory.variant_id == variant_id)
            .values(
                stock=ProductInventory.stock - quantity,
                reserved=ProductInventory.reserved - quantity,
                updated_at=datetime.utcnow(),
            )
        )
from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import (
    Order, OrderAddress, OrderItem, SellerOrder,
    OrderStatusHistory, OrderStatus, SellerOrderStatus,
)


class OrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> Order:
        order = Order(**kwargs)
        self.db.add(order)
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def create_address(self, order_id: UUID, **kwargs) -> OrderAddress:
        addr = OrderAddress(order_id=order_id, **kwargs)
        self.db.add(addr)
        await self.db.flush()
        return addr

    async def create_item(self, **kwargs) -> OrderItem:
        item = OrderItem(**kwargs)
        self.db.add(item)
        await self.db.flush()
        return item

    async def add_status_history(
        self,
        order_id: Optional[UUID] = None,
        seller_order_id: Optional[UUID] = None,
        old_status: Optional[str] = None,
        new_status: str = "",
        changed_by: Optional[UUID] = None,
        note: Optional[str] = None,
    ) -> None:
        hist = OrderStatusHistory(
            order_id=order_id,
            seller_order_id=seller_order_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            note=note,
        )
        self.db.add(hist)

    async def get_by_id(
        self, order_id: UUID, *, user_id: Optional[UUID] = None
    ) -> Optional[Order]:
        q = select(Order).options(
            selectinload(Order.address),
            selectinload(Order.items),
            selectinload(Order.seller_orders).selectinload(SellerOrder.seller),
        ).where(Order.id == order_id)

        if user_id:
            q = q.where(Order.user_id == user_id)

        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_by_number(self, order_number: str) -> Optional[Order]:
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.address),
                selectinload(Order.seller_orders).selectinload(SellerOrder.seller),
            )
            .where(Order.order_number == order_number)
        )
        return result.scalar_one_or_none()

    async def get_customer_orders(
        self, user_id: UUID, page: int = 1, per_page: int = 10
    ) -> tuple[Sequence[Order], int]:
        count_q = select(func.count(Order.id)).where(Order.user_id == user_id)
        total   = (await self.db.execute(count_q)).scalar_one()

        q = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
            .order_by(desc(Order.created_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def update_status(
        self,
        order_id: UUID,
        status: OrderStatus,
        changed_by: Optional[UUID] = None,
        note: Optional[str] = None,
    ) -> None:
        old_order = await self.db.execute(
            select(Order.status).where(Order.id == order_id)
        )
        old_status = old_order.scalar_one_or_none()

        await self.db.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await self.add_status_history(
            order_id=order_id,
            old_status=old_status.value if old_status else None,
            new_status=status.value,
            changed_by=changed_by,
            note=note,
        )

    async def number_exists(self, order_number: str) -> bool:
        result = await self.db.execute(
            select(Order.id).where(Order.order_number == order_number)
        )
        return result.scalar_one_or_none() is not None


class SellerOrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> SellerOrder:
        so = SellerOrder(**kwargs)
        self.db.add(so)
        await self.db.flush()
        await self.db.refresh(so)
        return so

    async def get_by_id(
        self, seller_order_id: UUID, seller_id: UUID
    ) -> Optional[SellerOrder]:
        result = await self.db.execute(
            select(SellerOrder)
            .options(
                selectinload(SellerOrder.order).selectinload(Order.address),
                selectinload(SellerOrder.order).selectinload(Order.items),
                selectinload(SellerOrder.seller),
            )
            .where(
                SellerOrder.id == seller_order_id,
                SellerOrder.seller_id == seller_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_seller(
        self,
        seller_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> tuple[Sequence[SellerOrder], int]:
        q = select(SellerOrder).where(SellerOrder.seller_id == seller_id)
        if status and status != "all":
            q = q.where(SellerOrder.status == SellerOrderStatus(status))

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = (
            q.options(
                selectinload(SellerOrder.order).selectinload(Order.items),
                selectinload(SellerOrder.order).selectinload(Order.address),
            )
            .order_by(desc(SellerOrder.created_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def update_status(
        self,
        seller_order_id: UUID,
        status: SellerOrderStatus,
        tracking_number: Optional[str] = None,
        courier_name: Optional[str] = None,
    ) -> None:
        values: dict = {"status": status, "updated_at": datetime.utcnow()}
        if tracking_number:
            values["tracking_number"] = tracking_number
        if courier_name:
            values["courier_name"] = courier_name
        if status == SellerOrderStatus.shipped:
            values["shipped_at"] = datetime.utcnow()
        if status == SellerOrderStatus.delivered:
            values["delivered_at"] = datetime.utcnow()

        await self.db.execute(
            update(SellerOrder)
            .where(SellerOrder.id == seller_order_id)
            .values(**values)
        )
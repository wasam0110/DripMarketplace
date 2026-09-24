from __future__ import annotations

import json
from uuid import UUID
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.product import ProductVariant, ProductInventory, Product
from app.models.seller import Seller
from app.schemas.order import (
    CartResponse, CartItemResponse, SellerCartGroup, AddToCartRequest,
)

CART_TTL       = 7 * 24 * 3600   # 7 days
from app.core.config import settings
SHIPPING_FREE = settings.FREE_SHIPPING_THRESHOLD
SHIPPING_FEE = settings.STANDARD_SHIPPING_FEE


def _cart_key(user_id: UUID) -> str:
    return f"cart:{user_id}"


class CartService:
    def __init__(self, db: AsyncSession, redis) -> None:
        self.db    = db
        self.redis = redis

    async def get_cart(self, user_id: UUID) -> CartResponse:
        raw = await self.redis.hgetall(_cart_key(user_id))
        if not raw:
            return self._empty_cart()

        variant_ids = [UUID(k.decode() if isinstance(k, bytes) else k) for k in raw]
        quantities  = {
            UUID(k.decode() if isinstance(k, bytes) else k): int(v)
            for k, v in raw.items()
        }

        result = await self.db.execute(
            select(ProductVariant)
            .options(
                selectinload(ProductVariant.product).selectinload(Product.seller),
                selectinload(ProductVariant.product).selectinload(Product.images),
                selectinload(ProductVariant.inventory),
            )
            .where(ProductVariant.id.in_(variant_ids), ProductVariant.is_active.is_(True))
        )
        variants = {v.id: v for v in result.scalars().all()}

        items: list[CartItemResponse] = []
        for vid, qty in quantities.items():
            v = variants.get(vid)
            if not v or not v.product.is_published or v.product.admin_hidden or v.product.deleted_at or not v.product.seller.is_active or v.product.seller.deleted_at:
                await self.redis.hdel(_cart_key(user_id), str(vid))
                continue

            p             = v.product
            inv           = v.inventory
            primary_image = next((i.url for i in p.images if i.is_primary), None)
            price         = v.price_override if v.price_override is not None else p.effective_price

            items.append(CartItemResponse(
                variant_id      = v.id,
                product_id      = p.id,
                product_name    = p.name,
                brand_name      = p.seller.brand_name,
                brand_color     = p.seller.brand_color,
                primary_image   = primary_image,
                size            = v.size_value,
                colour          = v.colour,
                unit_price      = price,
                quantity        = qty,
                subtotal        = price * qty,
                available_stock = inv.available_stock if inv else 0,
                seller_id       = p.seller_id,
            ))

        from app.services.platform_settings import get_platform_settings
        policy = await get_platform_settings(self.db)
        return self._build_cart_response(items, free_threshold=policy.free_shipping_threshold, shipping_fee=policy.standard_shipping_fee)

    async def add_item(self, user_id: UUID, payload: AddToCartRequest) -> CartResponse:
        variant = await self._get_variant(payload.variant_id)
        inv     = variant.inventory
        if not inv or inv.available_stock < payload.quantity:
            raise BusinessRuleError(
                f"Only {inv.available_stock if inv else 0} units available"
            )

        existing    = await self.redis.hget(_cart_key(user_id), str(payload.variant_id))
        current_qty = int(existing) if existing else 0
        new_qty     = current_qty + payload.quantity

        if new_qty > 100 or new_qty > (inv.available_stock if inv else 0):
            raise BusinessRuleError("Cannot add more than available stock")

        await self.redis.hset(_cart_key(user_id), str(payload.variant_id), new_qty)
        from app.models.analytics import AnalyticsEvent
        self.db.add(AnalyticsEvent(kind="add_to_cart", product_id=variant.product_id))
        await self.db.commit()
        await self.redis.expire(_cart_key(user_id), CART_TTL)
        return await self.get_cart(user_id)

    async def update_item(
        self, user_id: UUID, variant_id: UUID, quantity: int
    ) -> CartResponse:
        if quantity == 0:
            await self.redis.hdel(_cart_key(user_id), str(variant_id))
        else:
            variant = await self._get_variant(variant_id)
            inv     = variant.inventory
            if not inv or inv.available_stock < quantity:
                raise BusinessRuleError(
                    f"Only {inv.available_stock if inv else 0} units available"
                )
            await self.redis.hset(_cart_key(user_id), str(variant_id), quantity)
            await self.redis.expire(_cart_key(user_id), CART_TTL)
        return await self.get_cart(user_id)

    async def remove_item(self, user_id: UUID, variant_id: UUID) -> None:
        await self.redis.hdel(_cart_key(user_id), str(variant_id))

    async def clear(self, user_id: UUID) -> None:
        await self.redis.delete(_cart_key(user_id))

    async def sync(self, user_id: UUID, local_items: list[dict]) -> CartResponse:
        for item in local_items:
            vid      = str(item["variant_id"])
            qty      = item["quantity"]
            existing = await self.redis.hget(_cart_key(user_id), vid)
            current  = int(existing) if existing else 0
            await self.redis.hset(_cart_key(user_id), vid, max(current, qty))
        await self.redis.expire(_cart_key(user_id), CART_TTL)
        return await self.get_cart(user_id)

    async def get_raw_items(self, user_id: UUID) -> dict[UUID, int]:
        raw = await self.redis.hgetall(_cart_key(user_id))
        return {
            UUID(k.decode() if isinstance(k, bytes) else k): int(v)
            for k, v in raw.items()
        }

    async def _get_variant(self, variant_id: UUID) -> ProductVariant:
        result = await self.db.execute(
            select(ProductVariant)
            .options(
                selectinload(ProductVariant.inventory),
                selectinload(ProductVariant.product).selectinload(Product.seller),
            )
            .where(ProductVariant.id == variant_id, ProductVariant.is_active.is_(True))
        )
        v = result.scalar_one_or_none()
        if not v or not v.product.is_published or v.product.admin_hidden or v.product.deleted_at or not v.product.seller.is_active or v.product.seller.deleted_at:
            raise NotFoundError(f"Variant {variant_id} not found or unavailable")
        return v

    @staticmethod
    def _empty_cart() -> CartResponse:
        return CartResponse(
            items=[], grouped_by_seller=[], item_count=0,
            subtotal=0, shipping_fee=0, total=0,
        )

    @staticmethod
    def _build_cart_response(items: list[CartItemResponse], *, free_threshold=SHIPPING_FREE, shipping_fee=SHIPPING_FEE) -> CartResponse:
        subtotal = sum(i.subtotal for i in items)
        shipping = 0 if not items or subtotal >= free_threshold else shipping_fee

        groups: dict[UUID, SellerCartGroup] = {}
        for item in items:
            if item.seller_id not in groups:
                groups[item.seller_id] = SellerCartGroup(
                    seller_id      = item.seller_id,
                    brand_name     = item.brand_name,
                    brand_color    = item.brand_color,
                    items          = [],
                    group_subtotal = 0,
                )
            groups[item.seller_id].items.append(item)
            groups[item.seller_id].group_subtotal += item.subtotal

        return CartResponse(
            items             = items,
            grouped_by_seller = list(groups.values()),
            item_count        = sum(i.quantity for i in items),
            subtotal          = subtotal,
            shipping_fee      = shipping,
            total             = subtotal + shipping,
        )

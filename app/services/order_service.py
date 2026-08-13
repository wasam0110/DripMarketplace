from __future__ import annotations

import random
import string
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.models.order import Order, OrderStatus, PaymentMethod, SellerOrderStatus
from app.models.product import ProductVariant
from app.repositories.order_repo import OrderRepository, SellerOrderRepository
from app.repositories.inventory_repo import InventoryRepository
from app.services.cart_service import CartService, SHIPPING_FREE, SHIPPING_FEE
from app.services.coupon_service import CouponService
from app.schemas.order import (
    CreateOrderRequest, CreateGuestOrderRequest, CreateOrderResponse,
    OrderDetailResponse, OrderItemResponse, SellerOrderResponse,
    ShippingAddressResponse, PaginatedOrders, OrderRowResponse, PageInfo,
    CancelOrderRequest, UpdateSellerOrderRequest,
)

MAX_COD_AMOUNT = Decimal("25000")


def _generate_order_number() -> str:
    now    = datetime.utcnow()
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"DRIP-{now.strftime('%Y%m')}-{suffix}"


def _whatsapp_url(order_number: str, drip_number: str) -> str:
    msg = f"VERIFY+{order_number}"
    return f"https://wa.me/{drip_number}?text={msg}"


CANCELLABLE_STATUSES = {
    OrderStatus.pending_payment,
    OrderStatus.pending_cod_verification,
    OrderStatus.processing,
}


class OrderService:
    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db         = db
        self.redis      = redis
        self.order_repo = OrderRepository(db)
        self.so_repo    = SellerOrderRepository(db)
        self.inv_repo   = InventoryRepository(db)

    # ── Place Order (authenticated) ────────────────────────────────────────────

    async def create_order(
        self,
        user_id: UUID,
        payload: CreateOrderRequest,
    ) -> CreateOrderResponse:
        cart_svc = CartService(self.db, self.redis)
        raw_cart = await cart_svc.get_raw_items(user_id)

        if not raw_cart:
            raise BusinessRuleError("Your cart is empty")

        return await self._build_order(
            payload       = payload,
            variant_qtys  = raw_cart,
            user_id       = user_id,
            cart_svc      = cart_svc,
        )

    # ── Place Order (guest) ────────────────────────────────────────────────────

    async def create_guest_order(
        self, payload: CreateGuestOrderRequest
    ) -> CreateOrderResponse:
        variant_qtys = {item.variant_id: item.quantity for item in payload.items}

        return await self._build_order(
            payload      = payload,
            variant_qtys = variant_qtys,
            user_id      = None,
            cart_svc     = None,
            guest_email  = payload.guest_email,
            guest_name   = payload.guest_name,
            guest_phone  = payload.guest_phone,
        )

    # ── Core order builder ─────────────────────────────────────────────────────

    async def _build_order(
        self,
        payload:      CreateOrderRequest,
        variant_qtys: dict[UUID, int],
        user_id:      Optional[UUID],
        cart_svc:     Optional[CartService],
        guest_email:  Optional[str] = None,
        guest_name:   Optional[str] = None,
        guest_phone:  Optional[str] = None,
    ) -> CreateOrderResponse:
        # 1. Fetch + validate all variants
        variants = await self._fetch_and_validate_variants(variant_qtys)

        # 2. Build line items with pricing snapshots
        line_items = []
        seller_subtotals: dict[UUID, Decimal] = {}
        subtotal = Decimal("0")

        for variant, qty in variants:
            product = variant.product
            price   = variant.price_override if variant.price_override else product.price
            line_subtotal = price * qty
            subtotal     += line_subtotal

            label = f"{variant.size_value} / {variant.colour}"
            primary = next((i.url for i in product.images if i.is_primary), None)

            line_items.append({
                "seller_id":     product.seller_id,
                "product_id":    product.id,
                "variant_id":    variant.id,
                "product_name":  product.name,
                "variant_label": label,
                "unit_price":    price,
                "quantity":      qty,
                "subtotal":      line_subtotal,
            })
            seller_subtotals[product.seller_id] = (
                seller_subtotals.get(product.seller_id, Decimal("0")) + line_subtotal
            )

        # 3. Coupon
        discount = Decimal("0")
        coupon_svc = CouponService(self.db)
        coupon_id  = None

        # 4. Shipping
        shipping_fee = Decimal("0") if subtotal >= SHIPPING_FREE else Decimal(str(SHIPPING_FEE))

        # 5. COD limit
        pm = PaymentMethod(payload.payment_method)
        if pm == PaymentMethod.cod and (subtotal - discount) > MAX_COD_AMOUNT:
            raise BusinessRuleError(
                f"COD is not available for orders above PKR {int(MAX_COD_AMOUNT):,}"
            )

        total = subtotal - discount + shipping_fee

        # 6. Unique order number
        order_number = _generate_order_number()
        while await self.order_repo.number_exists(order_number):
            order_number = _generate_order_number()

        # 7. Status
        if pm == PaymentMethod.cod:
            status = OrderStatus.pending_cod_verification
        else:
            status = OrderStatus.pending_payment

        # 8. Create Order
        order = await self.order_repo.create(
            user_id        = user_id,
            order_number   = order_number,
            status         = status,
            guest_email    = guest_email,
            guest_name     = guest_name,
            guest_phone    = guest_phone,
            subtotal       = subtotal,
            discount_amount= discount,
            shipping_fee   = shipping_fee,
            total          = total,
            payment_method = pm,
            coupon_id      = coupon_id,
            notes          = payload.notes,
        )

        # 9. Address
        addr = payload.shipping_address
        await self.order_repo.create_address(
            order.id,
            recipient_name = addr.recipient_name,
            phone          = addr.phone,
            street         = addr.street,
            city           = addr.city,
            province       = addr.province,
            note           = addr.note,
        )

        # 10. Order items
        for li in line_items:
            await self.order_repo.create_item(order_id=order.id, **li)

        # 11. Seller orders
        for seller_id, sub in seller_subtotals.items():
            await self.so_repo.create(
                order_id=order.id, seller_id=seller_id, subtotal=sub
            )

        # 12. Reserve inventory (atomic per variant)
        for variant, qty in variants:
            success = await self.inv_repo.reserve(variant.id, qty)
            if not success:
                raise BusinessRuleError(
                    f"Stock changed during checkout for {variant.sku}. Please refresh your cart."
                )

        # 13. Apply coupon (record usage) if provided
        if payload.coupon_code and user_id:
            discount = await coupon_svc.apply_to_order(
                payload.coupon_code, subtotal, user_id, order.id
            )

        # 14. Clear cart
        if cart_svc and user_id:
            await cart_svc.clear(user_id)

        # 15. Enqueue tasks (Block 5 ARQ tasks — deferred import to avoid circular)
        if pm == PaymentMethod.cod:
            await self._enqueue_cod_timeout(str(order.id))

        await self.db.commit()

        # 16. Build response
        from app.core.config import settings
        whatsapp_url = None
        if pm == PaymentMethod.cod:
            drip_wa = getattr(settings, "DRIP_WHATSAPP_NUMBER", "923001234567")
            whatsapp_url = _whatsapp_url(order_number, drip_wa)

        return CreateOrderResponse(
            order_id      = order.id,
            order_number  = order_number,
            status        = status.value,
            total         = int(total),
            payment_method= pm.value,
            whatsapp_url  = whatsapp_url,
            payment_url   = None,  # Wired in Block 6
        )

    # ── Get order ──────────────────────────────────────────────────────────────

    async def get_order(self, order_id: UUID, user_id: UUID) -> OrderDetailResponse:
        order = await self.order_repo.get_by_id(order_id, user_id=user_id)
        if not order:
            raise NotFoundError("Order not found")
        return self._to_detail(order)

    async def get_order_by_number(
        self, order_number: str, email: str
    ) -> OrderDetailResponse:
        order = await self.order_repo.get_by_number(order_number)
        if not order:
            raise NotFoundError("Order not found")
        if order.guest_email and order.guest_email.lower() != email.lower():
            raise NotFoundError("Order not found")
        return self._to_detail(order)

    async def get_customer_orders(
        self, user_id: UUID, page: int = 1
    ) -> PaginatedOrders:
        orders, total = await self.order_repo.get_customer_orders(user_id, page)
        total_pages   = max(1, (total + 9) // 10)
        return PaginatedOrders(
            data=[
                OrderRowResponse(
                    id           = o.id,
                    order_number = o.order_number,
                    status       = o.status.value,
                    total        = int(o.total),
                    item_count   = sum(i.quantity for i in o.items),
                    created_at   = o.created_at,
                )
                for o in orders
            ],
            pagination=PageInfo(page=page, per_page=10, total=total, total_pages=total_pages),
        )

    # ── Cancel ─────────────────────────────────────────────────────────────────

    async def cancel_order(
        self,
        order_id: UUID,
        user_id: UUID,
        payload: CancelOrderRequest,
    ) -> dict:
        order = await self.order_repo.get_by_id(order_id, user_id=user_id)
        if not order:
            raise NotFoundError("Order not found")
        if order.status not in CANCELLABLE_STATUSES:
            raise BusinessRuleError(
                f"Order cannot be cancelled at status '{order.status.value}'"
            )

        # Release inventory
        for item in order.items:
            await self.inv_repo.release(item.variant_id, item.quantity)

        # Cancel all seller orders
        for so in order.seller_orders:
            await self.so_repo.update_status(so.id, SellerOrderStatus.cancelled)

        await self.order_repo.update_status(
            order_id,
            OrderStatus.cancelled,
            changed_by=user_id,
            note=payload.reason,
        )
        await self.db.commit()
        return {"message": "Order cancelled. Inventory has been released."}

    # ── Seller order management ────────────────────────────────────────────────

    async def get_seller_orders(
        self,
        seller_id: UUID,
        status: str = "all",
        page: int = 1,
    ) -> dict:
        seller_orders, total = await self.so_repo.get_by_seller(seller_id, status, page)
        total_pages = max(1, (total + 24) // 25)
        return {
            "data": [self._to_seller_order_response(so) for so in seller_orders],
            "pagination": {"page": page, "per_page": 25, "total": total, "total_pages": total_pages},
        }

    async def get_seller_order_detail(
        self, seller_id: UUID, seller_order_id: UUID
    ) -> dict:
        so = await self.so_repo.get_by_id(seller_order_id, seller_id)
        if not so:
            raise NotFoundError("Seller order not found")
        return self._to_seller_order_response(so, include_items=True)

    async def update_seller_order_status(
        self,
        seller_id: UUID,
        seller_order_id: UUID,
        payload: UpdateSellerOrderRequest,
    ) -> dict:
        so = await self.so_repo.get_by_id(seller_order_id, seller_id)
        if not so:
            raise NotFoundError("Seller order not found")

        await self.so_repo.update_status(
            seller_order_id,
            SellerOrderStatus(payload.status),
            tracking_number=payload.tracking_number,
            courier_name=payload.courier_name,
        )
        await self.db.commit()
        return {"message": f"Seller order status updated to '{payload.status}'"}

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _fetch_and_validate_variants(
        self, variant_qtys: dict[UUID, int]
    ) -> list[tuple]:
        result = await self.db.execute(
            select(ProductVariant)
            .options(
                selectinload(ProductVariant.product).selectinload(
                    __import__("app.models.product", fromlist=["Product"]).Product.images
                ),
                selectinload(ProductVariant.inventory),
            )
            .where(
                ProductVariant.id.in_(list(variant_qtys)),
                ProductVariant.is_active.is_(True),
            )
        )
        variants = result.scalars().all()

        if len(variants) != len(variant_qtys):
            raise BusinessRuleError("One or more items are no longer available")

        validated = []
        for v in variants:
            qty = variant_qtys[v.id]
            inv = v.inventory
            if not inv or inv.available_stock < qty:
                raise BusinessRuleError(
                    f"Insufficient stock for {v.product.name} — "
                    f"{v.size_value}/{v.colour}. "
                    f"Available: {inv.available_stock if inv else 0}"
                )
            validated.append((v, qty))
        return validated

    async def _enqueue_cod_timeout(self, order_id: str) -> None:
        """Enqueue a 30-min COD verification timeout task."""
        try:
            from arq import create_pool
            from arq.connections import RedisSettings
            from app.core.config import settings
            pool = await create_pool(RedisSettings.from_dsn(str(settings.REDIS_URL)))
            await pool.enqueue_job("cod_verification_timeout", order_id, _defer_by=1800)
            await pool.aclose()
        except Exception:
            pass  # Non-critical — task will be retried on next worker start

    @staticmethod
    def _to_detail(order: Order) -> OrderDetailResponse:
        return OrderDetailResponse(
            id              = order.id,
            order_number    = order.order_number,
            status          = order.status.value,
            payment_method  = order.payment_method.value,
            subtotal        = int(order.subtotal),
            discount_amount = int(order.discount_amount),
            shipping_fee    = int(order.shipping_fee),
            total           = int(order.total),
            notes           = order.notes,
            address         = ShippingAddressResponse(
                recipient_name = order.address.recipient_name,
                phone          = order.address.phone,
                street         = order.address.street,
                city           = order.address.city,
                province       = order.address.province,
                note           = order.address.note,
            ) if order.address else None,
            items=[
                OrderItemResponse(
                    id=i.id, seller_id=i.seller_id, product_id=i.product_id,
                    variant_id=i.variant_id, product_name=i.product_name,
                    variant_label=i.variant_label, unit_price=int(i.unit_price),
                    quantity=i.quantity, subtotal=int(i.subtotal),
                )
                for i in order.items
            ],
            seller_orders=[
                SellerOrderResponse(
                    id=so.id, seller_id=so.seller_id,
                    brand_name=so.seller.brand_name if so.seller else "",
                    status=so.status.value, subtotal=int(so.subtotal),
                    tracking_number=so.tracking_number, courier_name=so.courier_name,
                    shipped_at=so.shipped_at, delivered_at=so.delivered_at,
                )
                for so in order.seller_orders
            ],
            created_at=order.created_at,
        )

    @staticmethod
    def _to_seller_order_response(so, include_items: bool = False) -> dict:
        base = {
            "id":             str(so.id),
            "order_id":       str(so.order_id),
            "order_number":   so.order.order_number if so.order else "",
            "status":         so.status.value,
            "subtotal":       int(so.subtotal),
            "tracking_number": so.tracking_number,
            "courier_name":   so.courier_name,
            "shipped_at":     so.shipped_at.isoformat() if so.shipped_at else None,
            "delivered_at":   so.delivered_at.isoformat() if so.delivered_at else None,
            "created_at":     so.created_at.isoformat(),
        }
        if include_items and so.order:
            base["shipping_address"] = {
                "recipient_name": so.order.address.recipient_name if so.order.address else "",
                "phone":          so.order.address.phone if so.order.address else "",
                "city":           so.order.address.city if so.order.address else "",
                "province":       so.order.address.province if so.order.address else "",
            }
            base["items"] = [
                {
                    "product_name":  i.product_name,
                    "variant_label": i.variant_label,
                    "unit_price":    int(i.unit_price),
                    "quantity":      i.quantity,
                    "subtotal":      int(i.subtotal),
                }
                for i in so.order.items
                if i.seller_id == so.seller_id
            ]
        return base
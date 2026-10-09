from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.coupon import CouponUsage
from app.models.order import Order, OrderStatus, PaymentMethod, SellerOrder, SellerOrderStatus
from app.models.product import Product, ProductVariant
from app.models.seller import Seller, SellerStatus
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.order_repo import OrderRepository, SellerOrderRepository
from app.schemas.order import (
    CancelOrderRequest,
    CartItemInput,
    CartItemResponse,
    CreateGuestOrderRequest,
    CreateOrderRequest,
    CreateOrderResponse,
    GuestCheckoutQuoteRequest,
    GuestCheckoutQuoteResponse,
    OrderDetailResponse,
    OrderItemResponse,
    OrderRowResponse,
    PageInfo,
    PaginatedOrders,
    PaymentMethodAvailability,
    SellerOrderResponse,
    ShippingAddressResponse,
    UpdateSellerOrderRequest,
)
from app.services.cart_service import CartService
from app.services.coupon_service import CouponService
from app.services.order_access import authorized_order, create_guest_token


def _generate_order_number() -> str:
    now = datetime.utcnow()
    suffix = "".join([secrets.choice(string.ascii_uppercase + string.digits) for _ in range(9)])
    return f"WHZ-{now.strftime('%Y%m')}-{suffix}"


def _whatsapp_url(order_number: str, drip_number: str) -> str:
    msg = f"VERIFY+{order_number}"
    return f"https://wa.me/{drip_number}?text={msg}"


CANCELLABLE_STATUSES = {
    OrderStatus.pending_payment,
    OrderStatus.pending_cod_verification,
    OrderStatus.processing,
}


@dataclass(frozen=True)
class _CheckoutLine:
    variant: ProductVariant
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    primary_image: str | None


@dataclass(frozen=True)
class _CheckoutCalculation:
    lines: list[_CheckoutLine]
    seller_subtotals: dict[UUID, Decimal]
    subtotal: Decimal
    shipping_fee: Decimal
    free_shipping_threshold: Decimal
    cod_timeout_minutes: int

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.shipping_fee


class OrderService:
    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.order_repo = OrderRepository(db)
        self.so_repo = SellerOrderRepository(db)
        self.inv_repo = InventoryRepository(db)

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
            payload=payload,
            variant_qtys=raw_cart,
            user_id=user_id,
            cart_svc=cart_svc,
        )

    # ── Place Order (guest) ────────────────────────────────────────────────────

    async def create_guest_order(self, payload: CreateGuestOrderRequest) -> CreateOrderResponse:
        variant_qtys = self._merge_items(payload.items)

        return await self._build_order(
            payload=payload,
            variant_qtys=variant_qtys,
            user_id=None,
            cart_svc=None,
            guest_email=payload.guest_email,
            guest_name=payload.guest_name,
            guest_phone=payload.guest_phone,
        )

    async def quote_guest_checkout(
        self, payload: GuestCheckoutQuoteRequest
    ) -> GuestCheckoutQuoteResponse:
        """Return current guest pricing and payment capabilities without reserving stock."""
        if payload.coupon_code:
            raise BusinessRuleError("Sign in to use a coupon")

        calculation = await self._calculate_checkout(self._merge_items(payload.items))
        total = calculation.total
        cod_available = total <= Decimal(settings.MAX_COD_ORDER_AMOUNT)
        payment_methods = [
            PaymentMethodAvailability(
                method=PaymentMethod.cod,
                available=cod_available,
                unavailable_reason=None
                if cod_available
                else f"COD is not available for orders above PKR {settings.MAX_COD_ORDER_AMOUNT:,}",
            ),
            PaymentMethodAvailability(
                method=PaymentMethod.payfast,
                available=settings.PAYFAST_ENABLED,
                unavailable_reason=None
                if settings.PAYFAST_ENABLED
                else "Online payments are currently unavailable",
            ),
        ]
        return GuestCheckoutQuoteResponse(
            items=[
                CartItemResponse(
                    variant_id=line.variant.id,
                    product_id=line.variant.product.id,
                    product_name=line.variant.product.name,
                    brand_name=line.variant.product.seller.brand_name,
                    brand_color=line.variant.product.seller.brand_color,
                    primary_image=line.primary_image,
                    size=line.variant.size_value,
                    colour=line.variant.colour,
                    unit_price=line.unit_price,
                    quantity=line.quantity,
                    subtotal=line.subtotal,
                    available_stock=line.variant.inventory.available_stock,
                    seller_id=line.variant.product.seller_id,
                )
                for line in calculation.lines
            ],
            item_count=sum(line.quantity for line in calculation.lines),
            subtotal=calculation.subtotal,
            discount_amount=Decimal("0"),
            shipping_fee=calculation.shipping_fee,
            total=total,
            free_shipping_threshold=calculation.free_shipping_threshold,
            amount_until_free_shipping=max(
                calculation.free_shipping_threshold - calculation.subtotal, Decimal("0")
            ),
            payment_methods=payment_methods,
        )

    # ── Core order builder ─────────────────────────────────────────────────────

    async def _build_order(
        self,
        payload: CreateOrderRequest,
        variant_qtys: dict[UUID, int],
        user_id: Optional[UUID],
        cart_svc: Optional[CartService],
        guest_email: Optional[str] = None,
        guest_name: Optional[str] = None,
        guest_phone: Optional[str] = None,
    ) -> CreateOrderResponse:
        # 1-2. Validate stock and snapshot current prices/runtime shipping.
        calculation = await self._calculate_checkout(variant_qtys)
        subtotal = calculation.subtotal

        # 3. Coupon
        discount = Decimal("0")
        coupon_svc = CouponService(self.db)
        coupon_id = None
        if payload.coupon_code:
            if not user_id:
                raise BusinessRuleError("Sign in to use a coupon")
            coupon = await coupon_svc._get_valid_coupon(
                payload.coupon_code, subtotal, user_id, lock=True
            )
            discount = coupon_svc._calc_discount(coupon, subtotal)
            coupon_id = coupon.id

        # 4. Shipping
        shipping_fee = calculation.shipping_fee

        # 5. COD limit
        pm = PaymentMethod(payload.payment_method)
        if pm == PaymentMethod.payfast and not settings.PAYFAST_ENABLED:
            raise BusinessRuleError("Online payments are unavailable; choose COD")
        if (
            pm == PaymentMethod.cod
            and (subtotal - discount + shipping_fee) > settings.MAX_COD_ORDER_AMOUNT
        ):
            raise BusinessRuleError(
                f"COD is not available for orders above PKR {settings.MAX_COD_ORDER_AMOUNT:,}"
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
            user_id=user_id,
            order_number=order_number,
            status=status,
            guest_email=guest_email,
            guest_name=guest_name,
            guest_phone=guest_phone,
            subtotal=subtotal,
            discount_amount=discount,
            shipping_fee=shipping_fee,
            total=total,
            payment_method=pm,
            coupon_id=coupon_id,
            notes=payload.notes,
        )

        # 9. Address
        addr = payload.shipping_address
        await self.order_repo.create_address(
            order.id,
            recipient_name=addr.recipient_name,
            phone=addr.phone,
            street=addr.street,
            city=addr.city,
            province=addr.province,
            note=addr.note,
        )

        # 10. Order items
        for line in calculation.lines:
            variant = line.variant
            product = variant.product
            await self.order_repo.create_item(
                order_id=order.id,
                seller_id=product.seller_id,
                product_id=product.id,
                variant_id=variant.id,
                product_name=product.name,
                variant_label=f"{variant.size_value} / {variant.colour}",
                unit_price=line.unit_price,
                quantity=line.quantity,
                subtotal=line.subtotal,
            )

        # Allocate the platform coupon proportionally; the final share absorbs rounding.
        remaining_discount = discount
        for index, (seller_id, sub) in enumerate(calculation.seller_subtotals.items()):
            share = (
                remaining_discount
                if index == len(calculation.seller_subtotals) - 1
                else (discount * sub / subtotal).quantize(Decimal("0.01"))
            )
            remaining_discount -= share
            await self.so_repo.create(order_id=order.id, seller_id=seller_id, subtotal=sub - share)

        # 12. Reserve inventory (atomic per variant)
        for line in calculation.lines:
            success = await self.inv_repo.reserve(line.variant.id, line.quantity)
            if not success:
                raise BusinessRuleError(
                    f"Stock changed during checkout for {line.variant.sku}. "
                    "Please refresh your cart."
                )

        if coupon_id:
            self.db.add(CouponUsage(coupon_id=coupon_id, user_id=user_id, order_id=order.id))
            coupon.uses_count += 1
        await self.db.commit()

        # Redis is a separate store; never clear the cart before the SQL commit.
        if cart_svc and user_id:
            try:
                await cart_svc.clear(user_id)
            except Exception:
                from app.core.logging import get_logger

                get_logger(__name__).warning("checkout.cart_clear_failed", order_id=str(order.id))
        if pm == PaymentMethod.cod:
            await self._enqueue_cod_timeout(
                str(order.id), calculation.cod_timeout_minutes
            )

        # 16. Build response
        whatsapp_url = None
        if pm == PaymentMethod.cod:
            drip_wa = getattr(settings, "DRIP_WHATSAPP_NUMBER", "923001234567")
            whatsapp_url = _whatsapp_url(order_number, drip_wa)

        return CreateOrderResponse(
            order_id=order.id,
            order_number=order_number,
            status=status.value,
            total=total,
            guest_token=create_guest_token(order.id) if user_id is None else None,
            payment_method=pm.value,
            whatsapp_url=whatsapp_url,
            payment_url=None,  # Wired in Block 6
        )

    # ── Get order ──────────────────────────────────────────────────────────────

    async def get_order(self, order_id: UUID, user_id: UUID) -> OrderDetailResponse:
        order = await self.order_repo.get_by_id(order_id, user_id=user_id)
        if not order:
            raise NotFoundError("Order not found")
        return self._to_detail(order)

    async def get_order_by_number(
        self,
        order_number: str,
        email: str | None = None,
        user_id: UUID | None = None,
        guest_token: str | None = None,
    ) -> OrderDetailResponse:
        if user_id is None and not guest_token:
            from app.core.exceptions import AuthenticationError

            raise AuthenticationError("Sign in or provide a guest order token")
        order = await self.order_repo.get_by_number(order_number)
        if not order:
            raise NotFoundError("Order not found")
        order = await authorized_order(self.db, order.id, user_id, guest_token)
        return self._to_detail(order)

    async def get_customer_orders(self, user_id: UUID, page: int = 1) -> PaginatedOrders:
        orders, total = await self.order_repo.get_customer_orders(user_id, page)
        total_pages = max(1, (total + 9) // 10)
        return PaginatedOrders(
            data=[
                OrderRowResponse(
                    id=o.id,
                    order_number=o.order_number,
                    status=o.status.value,
                    total=o.total,
                    item_count=sum(i.quantity for i in o.items),
                    created_at=o.created_at,
                )
                for o in orders
            ],
            pagination=PageInfo(page=page, per_page=10, total=total, total_pages=total_pages),
        )

    # ── Cancel ─────────────────────────────────────────────────────────────────

    async def cancel_order(
        self,
        order_id: UUID,
        user_id: UUID | None,
        payload: CancelOrderRequest,
        guest_token: str | None = None,
    ) -> dict:
        order = await authorized_order(
            self.db, order_id, user_id, guest_token, lock=True
        )
        if order.status not in CANCELLABLE_STATUSES:
            raise BusinessRuleError(f"Order cannot be cancelled at status '{order.status.value}'")

        if any(
            so.status not in (SellerOrderStatus.pending, SellerOrderStatus.processing)
            for so in order.seller_orders
        ):
            raise BusinessRuleError("A dispatched order must use the returns process")
        from app.models.payment import Payment, PaymentStatus

        paid = await self.db.scalar(
            select(Payment.id).where(
                Payment.order_id == order.id,
                Payment.status.in_([PaymentStatus.completed, PaymentStatus.refunded]),
            )
        )
        if paid:
            raise BusinessRuleError("Contact support to cancel and refund a paid order")
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
            "pagination": {
                "page": page,
                "per_page": 25,
                "total": total,
                "total_pages": total_pages,
            },
        }

    async def get_seller_order_detail(self, seller_id: UUID, seller_order_id: UUID) -> dict:
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

        # Lock the parent before refreshing all fulfilment state. This serializes brands.
        order = await self.order_repo.get_by_id(so.order_id, for_update=True)
        await self.db.refresh(so)
        transitions = {
            SellerOrderStatus.pending: SellerOrderStatus.processing,
            SellerOrderStatus.processing: SellerOrderStatus.shipped,
            SellerOrderStatus.shipped: SellerOrderStatus.delivered,
        }
        target = SellerOrderStatus(payload.status)
        if so.status == target:
            return {"message": "Seller order already has this status"}
        if transitions.get(so.status) != target:
            raise BusinessRuleError("Invalid fulfilment status transition")
        if order.status not in (
            OrderStatus.payment_confirmed,
            OrderStatus.processing,
            OrderStatus.shipped,
        ):
            raise BusinessRuleError("The order must be paid or COD verified before fulfilment")
        if target == SellerOrderStatus.shipped:
            for item in order.items:
                if item.seller_id == seller_id:
                    await self.inv_repo.deduct(item.variant_id, item.quantity)
        old_status = so.status.value
        await self.so_repo.update_status(
            so.id,
            target,
            tracking_number=payload.tracking_number,
            courier_name=payload.courier_name,
        )
        await self.order_repo.add_status_history(
            seller_order_id=so.id, old_status=old_status, new_status=target.value
        )
        await self.db.flush()
        states = list(
            (
                await self.db.scalars(
                    select(SellerOrder.status).where(SellerOrder.order_id == order.id)
                )
            ).all()
        )
        parent_status = (
            OrderStatus.delivered
            if all(v == SellerOrderStatus.delivered for v in states)
            else OrderStatus.shipped
            if all(v in (SellerOrderStatus.shipped, SellerOrderStatus.delivered) for v in states)
            else OrderStatus.processing
        )
        await self.order_repo.update_status(order.id, parent_status)
        if target == SellerOrderStatus.delivered:
            # Persist settlement with delivery; COD earnings wait for recorded collection.
            from app.models.payment import Payment, PaymentStatus

            paid = await self.db.scalar(
                select(Payment.id).where(
                    Payment.order_id == order.id, Payment.status == PaymentStatus.completed
                )
            )
            if paid:
                from app.services.commission_service import CommissionService

                await CommissionService(self.db).settle(so.id, commit=False)
        await self.db.commit()

        return {"message": f"Seller order status updated to '{payload.status}'"}

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _merge_items(items: list[CartItemInput]) -> dict[UUID, int]:
        quantities: dict[UUID, int] = {}
        for item in items:
            quantities[item.variant_id] = quantities.get(item.variant_id, 0) + item.quantity
        return quantities

    async def _calculate_checkout(
        self, variant_qtys: dict[UUID, int]
    ) -> _CheckoutCalculation:
        variants = await self._fetch_and_validate_variants(variant_qtys)
        lines: list[_CheckoutLine] = []
        seller_subtotals: dict[UUID, Decimal] = {}
        subtotal = Decimal("0")

        for variant, quantity in variants:
            product = variant.product
            unit_price = (
                variant.price_override
                if variant.price_override is not None
                else (product.sale_price if product.sale_price is not None else product.price)
            )
            line_subtotal = unit_price * quantity
            subtotal += line_subtotal
            lines.append(
                _CheckoutLine(
                    variant=variant,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=line_subtotal,
                    primary_image=next(
                        (image.url for image in product.images if image.is_primary), None
                    ),
                )
            )
            seller_subtotals[product.seller_id] = (
                seller_subtotals.get(product.seller_id, Decimal("0")) + line_subtotal
            )

        from app.services.platform_settings import get_platform_settings

        policy = await get_platform_settings(self.db)
        free_shipping_threshold = Decimal(policy.free_shipping_threshold)
        shipping_fee = (
            Decimal("0")
            if subtotal >= free_shipping_threshold
            else Decimal(policy.standard_shipping_fee)
        )
        return _CheckoutCalculation(
            lines=lines,
            seller_subtotals=seller_subtotals,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            free_shipping_threshold=free_shipping_threshold,
            cod_timeout_minutes=policy.cod_timeout_minutes,
        )

    async def _fetch_and_validate_variants(
        self, variant_qtys: dict[UUID, int]
    ) -> list[tuple[ProductVariant, int]]:
        if (
            not variant_qtys
            or len(variant_qtys) > 100
            or any(qty < 1 or qty > 100 for qty in variant_qtys.values())
        ):
            raise BusinessRuleError(
                "A checkout allows 1–100 units per variant and at most 100 variants"
            )
        result = await self.db.execute(
            select(ProductVariant)
            .join(Product)
            .join(Seller)
            .options(
                selectinload(ProductVariant.product).selectinload(Product.seller),
                selectinload(ProductVariant.product).selectinload(
                    __import__("app.models.product", fromlist=["Product"]).Product.images
                ),
                selectinload(ProductVariant.inventory),
            )
            .where(
                ProductVariant.id.in_(list(variant_qtys)),
                ProductVariant.is_active.is_(True),
                Product.is_published.is_(True),
                Product.admin_hidden.is_(False),
                Product.deleted_at.is_(None),
                Seller.status == SellerStatus.active,
            )
        )
        variants = {variant.id: variant for variant in result.scalars().all()}

        if len(variants) != len(variant_qtys):
            raise BusinessRuleError("One or more items are no longer available")

        validated = []
        for variant_id, qty in variant_qtys.items():
            variant = variants[variant_id]
            inv = variant.inventory
            if not inv or inv.available_stock < qty:
                raise BusinessRuleError(
                    f"Insufficient stock for {variant.product.name} — "
                    f"{variant.size_value}/{variant.colour}. "
                    f"Available: {inv.available_stock if inv else 0}"
                )
            validated.append((variant, qty))
        return validated

    async def _enqueue_cod_timeout(self, order_id: str, minutes: int = 30) -> None:
        """Enqueue a 30-min COD verification timeout task."""
        if settings.ENVIRONMENT == "test":
            return
        try:
            from arq import create_pool
            from arq.connections import RedisSettings

            pool = await create_pool(RedisSettings.from_dsn(str(settings.REDIS_URL)))
            await pool.enqueue_job(
                "cod_verification_timeout",
                order_id,
                _defer_by=minutes * 60,
                _job_id=f"cod-timeout:{order_id}",
            )
            await pool.aclose()
        except Exception:
            pass  # Non-critical — task will be retried on next worker start

    @staticmethod
    def _to_detail(order: Order) -> OrderDetailResponse:
        return OrderDetailResponse(
            id=order.id,
            order_number=order.order_number,
            status=order.status.value,
            payment_method=order.payment_method.value,
            subtotal=order.subtotal,
            discount_amount=order.discount_amount,
            shipping_fee=order.shipping_fee,
            total=order.total,
            notes=order.notes,
            address=ShippingAddressResponse(
                recipient_name=order.address.recipient_name,
                phone=order.address.phone,
                street=order.address.street,
                city=order.address.city,
                province=order.address.province,
                note=order.address.note,
            )
            if order.address
            else None,
            items=[
                OrderItemResponse(
                    id=i.id,
                    seller_id=i.seller_id,
                    product_id=i.product_id,
                    variant_id=i.variant_id,
                    product_name=i.product_name,
                    variant_label=i.variant_label,
                    unit_price=i.unit_price,
                    quantity=i.quantity,
                    subtotal=i.subtotal,
                )
                for i in order.items
            ],
            seller_orders=[
                SellerOrderResponse(
                    id=so.id,
                    seller_id=so.seller_id,
                    brand_name=so.seller.brand_name if so.seller else "",
                    status=so.status.value,
                    subtotal=so.subtotal,
                    tracking_number=so.tracking_number,
                    courier_name=so.courier_name,
                    shipped_at=so.shipped_at,
                    delivered_at=so.delivered_at,
                )
                for so in order.seller_orders
            ],
            created_at=order.created_at,
        )

    @staticmethod
    def _to_seller_order_response(so, include_items: bool = False) -> dict:
        base = {
            "id": str(so.id),
            "order_id": str(so.order_id),
            "order_number": so.order.order_number if so.order else "",
            "status": so.status.value,
            "subtotal": so.subtotal,
            "tracking_number": so.tracking_number,
            "courier_name": so.courier_name,
            "shipped_at": so.shipped_at.isoformat() if so.shipped_at else None,
            "delivered_at": so.delivered_at.isoformat() if so.delivered_at else None,
            "created_at": so.created_at.isoformat(),
        }
        if include_items and so.order:
            base["shipping_address"] = {
                "recipient_name": so.order.address.recipient_name if so.order.address else "",
                "phone": so.order.address.phone if so.order.address else "",
                "city": so.order.address.city if so.order.address else "",
                "province": so.order.address.province if so.order.address else "",
                "street": so.order.address.street if so.order.address else "",
                "note": so.order.address.note if so.order.address else None,
            }
            base["items"] = [
                {
                    "product_name": i.product_name,
                    "variant_label": i.variant_label,
                    "unit_price": i.unit_price,
                    "quantity": i.quantity,
                    "subtotal": i.subtotal,
                }
                for i in so.order.items
                if i.seller_id == so.seller_id
            ]
        return base

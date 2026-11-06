"""services / admin service.

Business operations connecting API handlers, persistence, and provider integrations.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import UTC, datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.seller import Seller, SellerStatus
from app.models.order import Order, OrderStatus, SellerOrder
from app.models.product import Product
from app.models.wallet import Payout, PayoutStatus, CommissionLedger
from app.models.admin import SystemSetting, Banner
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminDashboardResponse, AdminSellerRowResponse, AdminSellerDetailResponse,
    PaginatedAdminSellers, AdminOrderRowResponse, OrderTotals, PaginatedAdminOrders,
    AdminOrderDetailResponse,
    CODQueueItem, BannerResponse, PlatformSettingsResponse,
)
from app.services.notification_outbox import queue_notification
from app.schemas.order import OrderItemResponse, SellerOrderResponse, ShippingAddressResponse

COD_TIMEOUT_MINUTES = 30

DEFAULT_SETTINGS = {
    "commission_rate":         "0.15",
    "registration_fee":        "5000",
    "extra_slot_price":        "50",
    "free_shipping_threshold": "5000",
    "standard_shipping_fee":   "200",
    "cod_timeout_minutes":     "30",
    "wallet_hold_days":        "3",
}


class AdminService:
    def __init__(self, db: AsyncSession) -> None:
        """Bind AdminService to its injected dependencies for subsequent operations."""
        self.db = db

    # ── Dashboard ──────────────────────────────────────────────────────────────

    async def get_dashboard(self, period: str) -> AdminDashboardResponse:
        """Aggregate marketplace counts and financial totals for the admin dashboard."""
        now = datetime.now(timezone.utc)
        since = now.replace(hour=0, minute=0, second=0, microsecond=0) if period == "today" else now - timedelta(days={
            "week": 7, "month": 30, "quarter": 90, "year": 365,
        }.get(period, 30))
        async def count(model, *filters):
            """Execute a dashboard count query using the shared database session."""
            r = await self.db.execute(select(func.count(model.id)).where(*filters))
            return r.scalar_one() or 0

        async def sum_col(col, *filters):
            """Execute a dashboard sum query and normalize an empty result to zero."""
            r = await self.db.execute(select(func.coalesce(func.sum(col), 0)).where(*filters))
            return Decimal(r.scalar_one())

        active_sellers  = await count(Seller, Seller.status == SellerStatus.active, Seller.deleted_at.is_(None))
        pending_sellers = await count(Seller, Seller.status == SellerStatus.pending_approval, Seller.deleted_at.is_(None))
        cod_unverified  = await count(Order, Order.status == OrderStatus.pending_cod_verification)
        total_orders    = await count(Order, Order.created_at >= since)

        pending_payouts_r = await self.db.execute(
            select(func.count(Payout.id)).where(Payout.status == PayoutStatus.requested)
        )
        pending_payouts = pending_payouts_r.scalar_one() or 0

        total_gmv = await sum_col(Order.total, Order.status.in_(["delivered", "completed"]), Order.created_at >= since)
        platform_revenue = await sum_col(CommissionLedger.net_commission_amount, CommissionLedger.settled_at >= since)
        from app.services.revenue import seller_fee_revenue
        slot_revenue = await seller_fee_revenue(self.db, since)
        new_customers = await count(User, User.role == UserRole.customer, User.created_at >= since)

        return AdminDashboardResponse(
            period           = period,
            total_gmv        = total_gmv,
            platform_revenue = platform_revenue,
            slot_revenue     = slot_revenue,
            total_revenue    = platform_revenue + slot_revenue,
            total_orders     = total_orders,
            active_sellers   = active_sellers,
            pending_sellers  = pending_sellers,
            cod_unverified   = cod_unverified,
            pending_payouts  = pending_payouts,
            new_customers    = new_customers,
        )

    # ── Sellers ────────────────────────────────────────────────────────────────

    async def list_sellers(
        self,
        status:   Optional[str] = None,
        q:        Optional[str] = None,
        page:     int = 1,
        per_page: int = 25,
    ) -> PaginatedAdminSellers:
        """Build a filtered seller page with product counts and settlement totals."""
        query = select(Seller).options(selectinload(Seller.wallet)).where(Seller.deleted_at.is_(None))

        if status and status != "all":
            query = query.where(Seller.status == SellerStatus(status))
        if q:
            query = query.where(Seller.brand_name.ilike(f"%{q}%"))

        count_q = select(func.count()).select_from(query.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        query = query.order_by(desc(Seller.created_at)).offset((page - 1) * per_page).limit(per_page)
        result  = await self.db.execute(query)
        sellers = result.scalars().all()

        rows = []
        for s in sellers:
            product_count = await self._count_products(s.id)
            commission_sum = await self._seller_commission(s.id)
            rows.append(AdminSellerRowResponse(
                id                = s.id,
                brand_name        = s.brand_name,
                status            = s.status.value,
                slots_used        = s.slots_used,
                total_slots       = s.total_slots,
                product_count     = product_count,
                total_gmv         = await self._seller_gmv(s.id),
                platform_cut      = commission_sum,
                available_balance = s.wallet.available_balance if s.wallet else 0,
                joined_at         = s.created_at,
            ))

        return PaginatedAdminSellers(
            data=rows, total=total, page=page, per_page=per_page,
            total_pages=max(1, (total + per_page - 1) // per_page),
        )

    async def get_seller(self, seller_id: UUID) -> AdminSellerDetailResponse:
        """Build the admin seller detail view from seller, wallet, and order records."""
        result = await self.db.execute(
            select(Seller)
            .options(selectinload(Seller.wallet))
            .where(Seller.id == seller_id, Seller.deleted_at.is_(None))
        )
        seller = result.scalar_one_or_none()
        if not seller:
            raise NotFoundError("Seller not found")

        product_count  = await self._count_products(seller_id)
        commission_sum = await self._seller_commission(seller_id)

        return AdminSellerDetailResponse(
            id                = seller.id,
            brand_name        = seller.brand_name,
            slug              = seller.slug,
            status            = seller.status.value,
            slots_used        = seller.slots_used,
            total_slots       = seller.total_slots,
            product_count     = product_count,
            total_gmv         = await self._seller_gmv(seller.id),
            platform_cut      = commission_sum,
            available_balance = seller.wallet.available_balance if seller.wallet else 0,
            pending_balance   = seller.wallet.pending_balance if seller.wallet else 0,
            registration_fee  = seller.registration_fee,
            registration_amount_due=(
                seller.registration_fee
                if seller.status == SellerStatus.pending_payment and not seller.registration_paid_at
                else Decimal("0.00")
            ),
            registration_paid_at=seller.registration_paid_at,
            registration_payment_reference=seller.registration_payment_reference,
            registration_paid_by=seller.registration_paid_by,
            description       = seller.description,
            whatsapp_number   = seller.whatsapp_number,
            instagram_handle  = seller.instagram_handle,
            logo_url          = seller.logo_url,
            return_policy     = seller.return_policy,
            rejected_reason   = seller.rejected_reason,
            joined_at         = seller.created_at,
        )

    async def approve_seller(self, seller_id: UUID, admin_id: UUID) -> dict:
        """Approve an eligible seller and queue the decision notification transactionally."""
        seller = await self._get_seller(seller_id)
        if seller.status != SellerStatus.pending_approval:
            raise BusinessRuleError(
                f"Can only approve sellers in pending_approval status. Current: {seller.status.value}"
            )
        await self.db.execute(
            update(Seller).where(Seller.id == seller_id).values(
                status=SellerStatus.active,
                approved_by=admin_id,
                approved_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await queue_notification(
            self.db,
            f"seller:{seller_id}:decision:approved",
            "notify_seller_decision",
            str(seller_id),
            True,
            None,
        )
        await self.db.commit()
        return {"message": f"Seller '{seller.brand_name}' approved and activated"}

    async def reject_seller(self, seller_id: UUID, admin_id: UUID, reason: str) -> dict:
        """Reject a pending seller application and queue the decision notification."""
        seller = await self._get_seller(seller_id)
        if seller.status not in (SellerStatus.pending_approval, SellerStatus.pending_payment):
            raise BusinessRuleError("Can only reject pending applications")
        await self.db.execute(
            update(Seller).where(Seller.id == seller_id).values(
                status=SellerStatus.rejected,
                rejected_reason=reason,
                approved_by=admin_id,
                updated_at=datetime.utcnow(),
            )
        )
        await queue_notification(
            self.db,
            f"seller:{seller_id}:decision:rejected",
            "notify_seller_decision",
            str(seller_id),
            False,
            reason,
        )
        await self.db.commit()
        return {"message": f"Seller '{seller.brand_name}' rejected"}

    async def suspend_seller(self, seller_id: UUID, admin_id: UUID, reason: str) -> dict:
        """Suspend an active seller after validating the current approval state."""
        seller = await self._get_seller(seller_id)
        if seller.status != SellerStatus.active:
            raise BusinessRuleError("Can only suspend active sellers")
        await self.db.execute(
            update(Seller).where(Seller.id == seller_id).values(
                status=SellerStatus.suspended,
                rejected_reason=reason,
                updated_at=datetime.utcnow(),
            )
        )
        # Public reads/cart/checkout gate on seller status. Do not overwrite
        # independent product moderation decisions while suspending the seller.
        await self.db.commit()
        return {"message": f"Seller '{seller.brand_name}' suspended. All products hidden."}

    async def reinstate_seller(self, seller_id: UUID, admin_id: UUID) -> dict:
        """Restore a suspended seller to active status."""
        seller = await self._get_seller(seller_id)
        if seller.status != SellerStatus.suspended:
            raise BusinessRuleError("Can only reinstate suspended sellers")
        await self.db.execute(
            update(Seller).where(Seller.id == seller_id).values(
                status=SellerStatus.active,
                approved_by=admin_id,
                approved_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        # Re-enabling seller visibility must not unhide moderated products.
        await self.db.commit()
        return {"message": f"Seller '{seller.brand_name}' reinstated. Products restored."}

    # ── Orders ─────────────────────────────────────────────────────────────────

    async def list_orders(
        self,
        status:         Optional[str] = None,
        seller_id:      Optional[UUID] = None,
        payment_method: Optional[str] = None,
        page:           int = 1,
        per_page:       int = 25,
    ) -> PaginatedAdminOrders:
        """Build the filtered admin order page with order and seller-order totals."""
        query = select(Order).options(
            selectinload(Order.items),
            selectinload(Order.seller_orders),
            selectinload(Order.address),
        )
        if status:
            query = query.where(Order.status == OrderStatus(status))
        if payment_method:
            query = query.where(Order.payment_method == payment_method)
        if seller_id:
            # One parent order per row, even for legacy duplicate brand splits.
            query = query.where(Order.seller_orders.any(SellerOrder.seller_id == seller_id))

        count_q = select(func.count()).select_from(query.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        matching_ids = query.with_only_columns(Order.id).order_by(None)
        commission_total_r = await self.db.execute(
            select(func.coalesce(func.sum(CommissionLedger.net_commission_amount), 0))
            .join(SellerOrder, CommissionLedger.seller_order_id == SellerOrder.id)
            .where(SellerOrder.order_id.in_(matching_ids))
        )
        commission_total = commission_total_r.scalar_one()

        gmv_total_r = await self.db.execute(
            select(func.coalesce(func.sum(Order.total), 0)).where(Order.id.in_(matching_ids))
        )
        gmv_total = gmv_total_r.scalar_one()

        query = query.order_by(desc(Order.created_at), desc(Order.id))
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        orders = result.scalars().all()
        commissions = dict((await self.db.execute(
            select(SellerOrder.order_id, func.sum(CommissionLedger.net_commission_amount))
            .join(SellerOrder, CommissionLedger.seller_order_id == SellerOrder.id)
            .where(SellerOrder.order_id.in_([order.id for order in orders]))
            .group_by(SellerOrder.order_id)
        )).all())

        rows = []
        for o in orders:
            customer_name = o.address.recipient_name if o.address else (o.guest_name or "Guest")
            rows.append(AdminOrderRowResponse(
                id             = o.id,
                order_number   = o.order_number,
                status         = o.status.value,
                customer_name  = customer_name,
                seller_count   = len(o.seller_orders),
                subtotal       = o.subtotal,
                total          = o.total,
                commission     = commissions.get(o.id, Decimal("0")),
                payment_method = o.payment_method.value,
                created_at     = o.created_at,
            ))

        return PaginatedAdminOrders(
            data   = rows,
            totals = OrderTotals(
                total_gmv=gmv_total,
                total_commission=commission_total,
                order_count=total,
            ),
            total=total, page=page, per_page=per_page,
            total_pages=max(1, (total + per_page - 1) // per_page),
        )

    async def get_order_detail(self, order_id: UUID) -> AdminOrderDetailResponse:
        """Read immutable checkout values and current brand fulfilment, without writes."""
        order = await self.db.scalar(
            select(Order).where(Order.id == order_id).options(
                selectinload(Order.address), selectinload(Order.items),
                selectinload(Order.seller_orders).selectinload(SellerOrder.seller),
            )
        )
        if order is None:
            raise NotFoundError("Order not found")
        commission = await self.db.scalar(
            select(func.coalesce(func.sum(CommissionLedger.net_commission_amount), 0))
            .join(SellerOrder, CommissionLedger.seller_order_id == SellerOrder.id)
            .where(SellerOrder.order_id == order.id)
        )
        return AdminOrderDetailResponse(
            id=order.id, order_number=order.order_number, status=order.status.value,
            payment_method=order.payment_method.value, user_id=order.user_id,
            customer_name=order.address.recipient_name if order.address else (
                order.guest_name or "Name unavailable"
            ),
            subtotal=order.subtotal, discount_amount=order.discount_amount,
            shipping_fee=order.shipping_fee, total=order.total, commission=commission,
            notes=order.notes, created_at=order.created_at,
            address=(
                ShippingAddressResponse.model_validate(order.address) if order.address else None
            ),
            items=[OrderItemResponse.model_validate(item) for item in sorted(
                order.items, key=lambda row: row.id
            )],
            seller_orders=[SellerOrderResponse(
                id=row.id, seller_id=row.seller_id,
                brand_name=row.seller.brand_name if row.seller else "",
                status=row.status.value, subtotal=row.subtotal,
                tracking_number=row.tracking_number, courier_name=row.courier_name,
                shipped_at=row.shipped_at, delivered_at=row.delivered_at,
            ) for row in sorted(order.seller_orders, key=lambda row: row.id)],
        )

    # ── COD Queue ──────────────────────────────────────────────────────────────

    async def list_cod_queue(self) -> list[CODQueueItem]:
        """Read pending COD verification orders using the runtime verification deadline."""
        from app.services.platform_settings import get_platform_settings
        policy = await get_platform_settings(self.db)
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.address),
                selectinload(Order.seller_orders).selectinload(SellerOrder.seller),
            )
            .where(
                Order.status == OrderStatus.pending_cod_verification,
                Order.payment_method == "cod",
            )
            .order_by(Order.created_at, Order.id)
        )
        orders = result.scalars().all()

        now   = datetime.now(UTC)
        items = []
        for o in orders:
            placed_at = (
                o.created_at.astimezone(UTC) if o.created_at.tzinfo
                else o.created_at.replace(tzinfo=UTC)
            )
            expires_at = placed_at + timedelta(minutes=policy.cod_timeout_minutes)
            remaining  = max(0, int((expires_at - now).total_seconds() / 60))

            brand_names = sorted({so.seller.brand_name for so in o.seller_orders if so.seller})
            customer_phone = o.address.phone if o.address else (o.guest_phone or "")
            customer_name  = o.address.recipient_name if o.address else (o.guest_name or "Guest")

            items.append(CODQueueItem(
                order_id          = o.id,
                order_number      = o.order_number,
                customer_name     = customer_name,
                customer_phone    = customer_phone,
                total             = o.total,
                brand_names       = brand_names,
                placed_at         = placed_at,
                expires_at        = expires_at,
                minutes_remaining = remaining,
                updated_at        = o.updated_at,
            ))

        return items

    async def _check_cod_review(
        self, order: Order, expected_updated_at: datetime | None,
        expected_expires_at: datetime | None,
    ) -> datetime:
        """Recheck the current order version and runtime deadline while its row is locked."""
        from app.services.platform_settings import get_platform_settings

        if order.status != OrderStatus.pending_cod_verification or order.payment_method != "cod":
            raise BusinessRuleError("Order is not awaiting COD verification")
        from app.models.order import SellerOrderStatus

        if not order.items or not order.seller_orders or any(
            row.status != SellerOrderStatus.pending for row in order.seller_orders
        ):
            raise BusinessRuleError("COD fulfilment records are inconsistent; contact support")
        if expected_updated_at is not None and order.updated_at != expected_updated_at:
            raise ConflictError("The order changed. Refresh and review it again.")
        policy = await get_platform_settings(self.db)
        placed = order.created_at
        placed = placed.astimezone(UTC) if placed.tzinfo else placed.replace(tzinfo=UTC)
        expires = placed + timedelta(minutes=policy.cod_timeout_minutes)
        if expected_expires_at is not None and expires != expected_expires_at:
            raise ConflictError("The COD deadline changed. Refresh and review it again.")
        return expires

    async def verify_cod(
        self, order_id: UUID, admin_id: UUID, note: str | None = None, *,
        expected_updated_at: datetime | None = None, expected_expires_at: datetime | None = None,
    ) -> dict:
        """Advance an eligible COD order and queue its status notification."""
        from app.repositories.order_repo import OrderRepository
        repo  = OrderRepository(self.db)
        order = await repo.get_by_id(order_id, for_update=True)
        if not order:
            raise NotFoundError("Order not found")
        expires = await self._check_cod_review(order, expected_updated_at, expected_expires_at)
        if datetime.now(UTC) >= expires:
            raise BusinessRuleError(
                "COD verification deadline expired; review cancellation instead"
            )
        await repo.update_status(
            order_id, OrderStatus.processing,
            changed_by=admin_id, note=note or "COD verified by admin",
        )
        await queue_notification(
            self.db,
            f"order:{order.id}:status:processing",
            "send_order_status_update",
            str(order.id),
            OrderStatus.processing.value,
        )
        await self.db.commit()
        return {
            "order_id": order.id, "order_number": order.order_number, "status": "processing",
            "message": f"COD order {order.order_number} verified and moved to processing",
        }

    async def cancel_cod(
        self, order_id: UUID, admin_id: UUID, reason: str | None = None, *,
        expected_updated_at: datetime | None = None, expected_expires_at: datetime | None = None,
    ) -> dict:
        """Cancel an unverified COD order, release reservations, and queue its
        notification.
        """
        from app.repositories.order_repo import OrderRepository, SellerOrderRepository
        from app.repositories.inventory_repo import InventoryRepository
        from app.models.order import SellerOrderStatus

        order_repo = OrderRepository(self.db)
        so_repo    = SellerOrderRepository(self.db)
        inv_repo   = InventoryRepository(self.db)

        order = await order_repo.get_by_id(order_id, for_update=True)
        if not order:
            raise NotFoundError("Order not found")
        await self._check_cod_review(order, expected_updated_at, expected_expires_at)

        for item in sorted(order.items, key=lambda row: row.variant_id):
            await inv_repo.release(item.variant_id, item.quantity, strict=True)

        for so in order.seller_orders:
            await so_repo.update_status(so.id, SellerOrderStatus.cancelled)

        await order_repo.update_status(
            order_id, OrderStatus.cancelled,
            changed_by=admin_id,
            note=reason or "COD order cancelled by admin",
        )
        await queue_notification(
            self.db,
            f"order:{order.id}:status:cancelled",
            "send_order_status_update",
            str(order.id),
            OrderStatus.cancelled.value,
        )
        await self.db.commit()
        return {
            "order_id": order.id, "order_number": order.order_number, "status": "cancelled",
            "message": f"COD order {order.order_number} cancelled. Inventory released.",
        }

    # ── Banners ────────────────────────────────────────────────────────────────

    async def list_banners(self) -> list[BannerResponse]:
        """Convert stored banners into the admin response contract."""
        result = await self.db.execute(
            select(Banner).order_by(Banner.sort_order, Banner.created_at, Banner.id)
        )
        return [BannerResponse.model_validate(b) for b in result.scalars().all()]

    async def create_banner(self, **kwargs) -> BannerResponse:
        """Persist a banner and return its response model."""
        banner = Banner(**kwargs)
        self.db.add(banner)
        await self.db.flush()
        await self.db.refresh(banner)
        await self.db.commit()
        return BannerResponse.model_validate(banner)

    async def delete_banner(
        self, banner_id: UUID, *, expected_updated_at: datetime | None = None
    ) -> None:
        """Lock the banner and reject deletion of a stale reviewed version."""
        result = await self.db.execute(
            select(Banner).where(Banner.id == banner_id).with_for_update()
            .execution_options(populate_existing=True)
        )
        banner = result.scalar_one_or_none()
        if not banner:
            raise NotFoundError("Banner not found")
        if expected_updated_at is not None and expected_updated_at != banner.updated_at:
            raise ConflictError("The banner changed. Refresh and review it again.")
        await self.db.delete(banner)
        await self.db.commit()

    # ── Settings ───────────────────────────────────────────────────────────────

    async def get_settings(self) -> PlatformSettingsResponse:
        """Return the effective platform settings from the shared policy loader."""
        from app.services.platform_settings import get_platform_settings
        return await get_platform_settings(self.db)

    async def update_settings(
        self, updates: dict, admin_id: UUID
    ) -> PlatformSettingsResponse:
        """Validate and persist supported runtime settings, then reload the effective
        policy.
        """
        from sqlalchemy.dialects.postgresql import insert
        from app.schemas.admin import UpdateSettingsRequest
        payload = UpdateSettingsRequest.model_validate(updates)
        updates = payload.model_dump(exclude_none=True, exclude={"expected_settings"})
        if not updates:
            raise BusinessRuleError("Choose at least one platform setting to update")
        # Serialize even first-time overrides, where no setting row exists to lock.
        # All runtime settings writers use this transaction-scoped advisory lock.
        await self.db.execute(select(func.pg_advisory_xact_lock(1464355418, 1)))
        current = await self.get_settings()
        if payload.expected_settings is not None and payload.expected_settings != current:
            raise ConflictError("Platform settings changed. Refresh and review them again.")
        for key, val in updates.items():
            if val is None:
                continue
            statement = insert(SystemSetting).values(key=key, value=str(val), updated_by=admin_id)
            await self.db.execute(statement.on_conflict_do_update(
                index_elements=[SystemSetting.key],
                set_={"value": str(val), "updated_by": admin_id, "updated_at": datetime.now(timezone.utc)},
            ))

        saved = await self.get_settings()
        await self.db.commit()
        return saved

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _get_seller(self, seller_id: UUID) -> Seller:
        """Lock and refresh the seller until the decision transaction ends."""
        result = await self.db.execute(
            select(Seller)
            .where(Seller.id == seller_id, Seller.deleted_at.is_(None))
            .with_for_update()
            # Refresh objects cached before a competing decision committed.
            .execution_options(populate_existing=True)
        )
        seller = result.scalar_one_or_none()
        if not seller:
            raise NotFoundError("Seller not found")
        return seller

    async def _count_products(self, seller_id: UUID) -> int:
        """Count the seller's published, non-deleted products."""
        result = await self.db.execute(
            select(func.count(Product.id)).where(
                Product.seller_id == seller_id,
                Product.is_published.is_(True),
                Product.deleted_at.is_(None),
            )
        )
        return result.scalar_one() or 0

    async def _seller_commission(self, seller_id: UUID) -> Decimal:
        """Aggregate the seller's net platform commission from settlement records."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(CommissionLedger.net_commission_amount), 0))
            .where(CommissionLedger.seller_id == seller_id)
        )
        return result.scalar_one()

    async def _seller_gmv(self, seller_id: UUID) -> Decimal:
        """Aggregate the seller's net settled gross merchandise value."""
        return await self.db.scalar(select(func.coalesce(func.sum(SellerOrder.subtotal), 0)).where(
            SellerOrder.seller_id == seller_id, SellerOrder.status == "delivered",
        ))

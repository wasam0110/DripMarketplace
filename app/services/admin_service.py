from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, update, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError, InvalidStatusTransitionError
from app.models.seller import Seller, SellerStatus, SellerWallet
from app.models.order import Order, OrderStatus, SellerOrder, OrderItem
from app.models.product import Product
from app.models.wallet import Payout, PayoutStatus, CommissionLedger
from app.models.admin import SystemSetting, Banner
from app.models.user import User, UserRole
from app.repositories.seller_repo import SellerRepository
from app.schemas.admin import (
    AdminDashboardResponse, AdminSellerRowResponse, AdminSellerDetailResponse,
    PaginatedAdminSellers, AdminOrderRowResponse, OrderTotals, PaginatedAdminOrders,
    CODQueueItem, BannerResponse, PlatformSettingsResponse,
)

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
        self.db = db

    # ── Dashboard ──────────────────────────────────────────────────────────────

    async def get_dashboard(self, period: str) -> AdminDashboardResponse:
        async def count(model, *filters):
            r = await self.db.execute(select(func.count(model.id)).where(*filters))
            return r.scalar_one() or 0

        async def sum_col(col, *filters):
            r = await self.db.execute(select(func.coalesce(func.sum(col), 0)).where(*filters))
            return int(r.scalar_one())

        active_sellers  = await count(Seller, Seller.status == SellerStatus.active, Seller.deleted_at.is_(None))
        pending_sellers = await count(Seller, Seller.status == SellerStatus.pending_approval, Seller.deleted_at.is_(None))
        cod_unverified  = await count(Order, Order.status == OrderStatus.pending_cod_verification)
        total_orders    = await count(Order, Order.id.isnot(None))

        pending_payouts_r = await self.db.execute(
            select(func.count(Payout.id)).where(Payout.status == PayoutStatus.requested)
        )
        pending_payouts = pending_payouts_r.scalar_one() or 0

        total_gmv        = await sum_col(Order.total,                   Order.status.in_(["delivered", "completed"]))
        platform_revenue = await sum_col(CommissionLedger.commission_amount, CommissionLedger.id.isnot(None))
        slot_revenue     = await sum_col(Seller.registration_fee,         Seller.status == SellerStatus.active)
        new_customers    = await count(User, User.role == UserRole.customer)

        return AdminDashboardResponse(
            period           = period,
            total_gmv        = total_gmv,
            platform_revenue = platform_revenue,
            slot_revenue     = int(slot_revenue),
            total_revenue    = platform_revenue + int(slot_revenue),
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
                total_gmv         = 0,              # Full aggregation wired in Block 11
                platform_cut      = int(commission_sum),
                available_balance = int(s.wallet.available_balance) if s.wallet else 0,
                joined_at         = s.created_at,
            ))

        return PaginatedAdminSellers(
            data=rows, total=total, page=page, per_page=per_page,
            total_pages=max(1, (total + per_page - 1) // per_page),
        )

    async def get_seller(self, seller_id: UUID) -> AdminSellerDetailResponse:
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
            total_gmv         = 0,
            platform_cut      = int(commission_sum),
            available_balance = int(seller.wallet.available_balance) if seller.wallet else 0,
            pending_balance   = int(seller.wallet.pending_balance)   if seller.wallet else 0,
            registration_fee  = int(seller.registration_fee),
            description       = seller.description,
            whatsapp_number   = seller.whatsapp_number,
            instagram_handle  = seller.instagram_handle,
            logo_url          = seller.logo_url,
            return_policy     = seller.return_policy,
            rejected_reason   = seller.rejected_reason,
            joined_at         = seller.created_at,
        )

    async def approve_seller(self, seller_id: UUID, admin_id: UUID) -> dict:
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
        await self.db.commit()
        return {"message": f"Seller '{seller.brand_name}' approved and activated"}

    async def reject_seller(self, seller_id: UUID, admin_id: UUID, reason: str) -> dict:
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
        await self.db.commit()
        return {"message": f"Seller '{seller.brand_name}' rejected"}

    async def suspend_seller(self, seller_id: UUID, admin_id: UUID, reason: str) -> dict:
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
        # Hide all products
        await self.db.execute(
            update(Product)
            .where(Product.seller_id == seller_id, Product.deleted_at.is_(None))
            .values(admin_hidden=True)
        )
        await self.db.commit()
        return {"message": f"Seller '{seller.brand_name}' suspended. All products hidden."}

    async def reinstate_seller(self, seller_id: UUID, admin_id: UUID) -> dict:
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
        # Restore products
        await self.db.execute(
            update(Product)
            .where(Product.seller_id == seller_id, Product.deleted_at.is_(None))
            .values(admin_hidden=False)
        )
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
            query = query.join(SellerOrder, Order.id == SellerOrder.order_id).where(
                SellerOrder.seller_id == seller_id
            )

        count_q = select(func.count()).select_from(query.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        commission_total_r = await self.db.execute(
            select(func.coalesce(func.sum(CommissionLedger.commission_amount), 0))
        )
        commission_total = int(commission_total_r.scalar_one())

        gmv_total_r = await self.db.execute(
            select(func.coalesce(func.sum(Order.total), 0))
        )
        gmv_total = int(gmv_total_r.scalar_one())

        query = query.order_by(desc(Order.created_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        orders = result.scalars().all()

        rows = []
        for o in orders:
            customer_name = o.address.recipient_name if o.address else (o.guest_name or "Guest")
            rows.append(AdminOrderRowResponse(
                id             = o.id,
                order_number   = o.order_number,
                status         = o.status.value,
                customer_name  = customer_name,
                seller_count   = len(o.seller_orders),
                subtotal       = int(o.subtotal),
                total          = int(o.total),
                commission     = 0,  # Per-order commission from Block 11 analytics
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
            total=total, page=page,
        )

    # ── COD Queue ──────────────────────────────────────────────────────────────

    async def list_cod_queue(self) -> list[CODQueueItem]:
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.address),
                selectinload(Order.seller_orders).selectinload(SellerOrder.seller),
            )
            .where(Order.status == OrderStatus.pending_cod_verification)
            .order_by(Order.created_at)
        )
        orders = result.scalars().all()

        now   = datetime.now(timezone.utc)
        items = []
        for o in orders:
            placed_at  = o.created_at.replace(tzinfo=timezone.utc)
            expires_at = placed_at + timedelta(minutes=COD_TIMEOUT_MINUTES)
            remaining  = max(0, int((expires_at - now).total_seconds() / 60))

            brand_names    = list({so.seller.brand_name for so in o.seller_orders if so.seller})
            customer_phone = o.address.phone if o.address else (o.guest_phone or "")
            customer_name  = o.address.recipient_name if o.address else (o.guest_name or "Guest")

            items.append(CODQueueItem(
                order_id          = o.id,
                order_number      = o.order_number,
                customer_name     = customer_name,
                customer_phone    = customer_phone,
                total             = int(o.total),
                brand_names       = brand_names,
                placed_at         = placed_at,
                expires_at        = expires_at,
                minutes_remaining = remaining,
            ))

        return items

    async def verify_cod(self, order_id: UUID, admin_id: UUID, note: Optional[str] = None) -> dict:
        from app.repositories.order_repo import OrderRepository
        repo  = OrderRepository(self.db)
        order = await repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
        if order.status != OrderStatus.pending_cod_verification:
            raise BusinessRuleError(f"Order is not awaiting COD verification (status: {order.status.value})")
        await repo.update_status(order_id, OrderStatus.processing, changed_by=admin_id, note=note or "COD verified by admin")
        await self.db.commit()
        return {"message": f"COD order {order.order_number} verified and moved to processing"}

    async def cancel_cod(self, order_id: UUID, admin_id: UUID, reason: Optional[str] = None) -> dict:
        from app.repositories.order_repo import OrderRepository, SellerOrderRepository
        from app.repositories.inventory_repo import InventoryRepository
        from app.models.order import SellerOrderStatus

        order_repo = OrderRepository(self.db)
        so_repo    = SellerOrderRepository(self.db)
        inv_repo   = InventoryRepository(self.db)

        order = await order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
        if order.status != OrderStatus.pending_cod_verification:
            raise BusinessRuleError("Can only cancel orders awaiting COD verification")

        for item in order.items:
            await inv_repo.release(item.variant_id, item.quantity)

        for so in order.seller_orders:
            await so_repo.update_status(so.id, SellerOrderStatus.cancelled)

        await order_repo.update_status(
            order_id, OrderStatus.cancelled,
            changed_by=admin_id,
            note=reason or "COD verification timeout — cancelled by admin",
        )
        await self.db.commit()
        return {"message": f"COD order {order.order_number} cancelled. Inventory released."}

    # ── Banners ────────────────────────────────────────────────────────────────

    async def list_banners(self) -> list[BannerResponse]:
        result = await self.db.execute(
            select(Banner).order_by(Banner.sort_order, Banner.created_at)
        )
        return [BannerResponse.model_validate(b) for b in result.scalars().all()]

    async def create_banner(self, **kwargs) -> BannerResponse:
        banner = Banner(**kwargs)
        self.db.add(banner)
        await self.db.flush()
        await self.db.refresh(banner)
        await self.db.commit()
        return BannerResponse.model_validate(banner)

    async def delete_banner(self, banner_id: UUID) -> None:
        result = await self.db.execute(select(Banner).where(Banner.id == banner_id))
        banner = result.scalar_one_or_none()
        if not banner:
            raise NotFoundError("Banner not found")
        await self.db.delete(banner)
        await self.db.commit()

    # ── Settings ───────────────────────────────────────────────────────────────

    async def get_settings(self) -> PlatformSettingsResponse:
        result  = await self.db.execute(select(SystemSetting))
        rows    = {s.key: s.value for s in result.scalars().all()}
        merged  = {**DEFAULT_SETTINGS, **rows}
        return PlatformSettingsResponse(
            commission_rate         = float(merged["commission_rate"]),
            registration_fee        = int(merged["registration_fee"]),
            extra_slot_price        = int(merged["extra_slot_price"]),
            free_shipping_threshold = int(merged["free_shipping_threshold"]),
            standard_shipping_fee   = int(merged["standard_shipping_fee"]),
            cod_timeout_minutes     = int(merged["cod_timeout_minutes"]),
            wallet_hold_days        = int(merged["wallet_hold_days"]),
        )

    async def update_settings(
        self, updates: dict, admin_id: UUID
    ) -> PlatformSettingsResponse:
        for key, val in updates.items():
            if val is None:
                continue
            result = await self.db.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            setting = result.scalar_one_or_none()
            if setting:
                setting.value      = str(val)
                setting.updated_by = admin_id
                setting.updated_at = datetime.utcnow()
            else:
                self.db.add(SystemSetting(key=key, value=str(val), updated_by=admin_id))

        await self.db.commit()
        return await self.get_settings()

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _get_seller(self, seller_id: UUID) -> Seller:
        result = await self.db.execute(
            select(Seller).where(Seller.id == seller_id, Seller.deleted_at.is_(None))
        )
        seller = result.scalar_one_or_none()
        if not seller:
            raise NotFoundError("Seller not found")
        return seller

    async def _count_products(self, seller_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Product.id)).where(
                Product.seller_id == seller_id,
                Product.is_published.is_(True),
                Product.deleted_at.is_(None),
            )
        )
        return result.scalar_one() or 0

    async def _seller_commission(self, seller_id: UUID) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(CommissionLedger.commission_amount), 0))
            .where(CommissionLedger.seller_id == seller_id)
        )
        return result.scalar_one()
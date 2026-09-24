from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID
from typing import Optional

from sqlalchemy import select, func, desc, and_, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus, OrderItem, SellerOrder
from app.models.product import Product, ProductVariant, ProductInventory
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.models.wallet import CommissionLedger
from app.models.analytics import AnalyticsEvent
from app.schemas.analytics import (
    SellerAnalyticsOverview,
    RevenueSeriesResponse,
    RevenueDayRow,
    TopProductsResponse,
    TopProductRow,
    InventoryHealthResponse,
    PlatformAnalytics,
    TopSellersResponse,
    TopSellerRow,
    CohortResponse,
    CohortRow,
    PaymentMethodsResponse,
    PaymentMethodStat,
    CitiesResponse,
    CityRow,
    ConversionResponse,
    SearchQueriesResponse,
    SearchQueryRow,
)

LOW_STOCK_THRESHOLD = 5


def _period_to_days(period: str) -> int:
    return {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(period, 30)


def _date_from(period: str) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=_period_to_days(period))


def _trunc(granularity: str) -> str:
    return {"day": "day", "week": "week", "month": "month"}.get(granularity, "day")


# ── Seller Analytics ───────────────────────────────────────────────────────────


class SellerAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_overview(self, seller_id: UUID, period: str) -> SellerAnalyticsOverview:
        date_from = _date_from(period)

        # Commission totals
        comm_q = select(
            func.coalesce(func.sum(CommissionLedger.gross_amount), 0),
            func.coalesce(func.sum(CommissionLedger.commission_amount), 0),
            func.coalesce(func.sum(CommissionLedger.seller_amount), 0),
            func.count(CommissionLedger.id),
        ).where(
            CommissionLedger.seller_id == seller_id,
            CommissionLedger.settled_at >= date_from,
        )
        comm = (await self.db.execute(comm_q)).one()
        gross = int(comm[0])
        commission = int(comm[1])
        net = int(comm[2])
        orders = int(comm[3])

        # Units sold
        units_q = select(func.coalesce(func.sum(OrderItem.quantity), 0)).where(
            OrderItem.seller_id == seller_id,
            OrderItem.order_id.in_(
                select(Order.id).where(
                    Order.created_at >= date_from,
                    Order.status.in_(
                        ["payment_confirmed", "processing", "shipped", "delivered", "completed"]
                    ),
                )
            ),
        )
        units_sold = int((await self.db.execute(units_q)).scalar_one())

        # Total product views
        views_q = (
            select(func.count(AnalyticsEvent.id))
            .join(Product, AnalyticsEvent.product_id == Product.id)
            .where(
                Product.seller_id == seller_id,
                AnalyticsEvent.kind == "product_view",
                AnalyticsEvent.created_at >= date_from,
            )
        )
        total_views = int((await self.db.execute(views_q)).scalar_one())

        avg_order_value = gross // orders if orders else 0
        conversion_rate = round(orders / total_views * 100, 2) if total_views else 0.0

        return SellerAnalyticsOverview(
            period=period,
            gross_revenue=gross,
            commission_paid=commission,
            net_earnings=net,
            order_count=orders,
            units_sold=units_sold,
            avg_order_value=avg_order_value,
            total_views=total_views,
            conversion_rate=conversion_rate,
        )

    async def get_revenue_series(
        self, seller_id: UUID, period: str, granularity: str
    ) -> RevenueSeriesResponse:
        date_from = _date_from(period)
        trunc_unit = _trunc(granularity)

        q = (
            select(
                func.date_trunc(trunc_unit, CommissionLedger.settled_at).label("bucket"),
                func.sum(CommissionLedger.gross_amount).label("gross"),
                func.sum(CommissionLedger.commission_amount).label("commission"),
                func.sum(CommissionLedger.seller_amount).label("net"),
                func.count(CommissionLedger.id).label("orders"),
            )
            .where(
                CommissionLedger.seller_id == seller_id,
                CommissionLedger.settled_at >= date_from,
            )
            .group_by("bucket")
            .order_by("bucket")
        )

        result = await self.db.execute(q)
        rows = result.all()

        return RevenueSeriesResponse(
            period=period,
            granularity=granularity,
            data=[
                RevenueDayRow(
                    date=row.bucket.strftime("%Y-%m-%d"),
                    gross=int(row.gross),
                    commission=int(row.commission),
                    net=int(row.net),
                    orders=int(row.orders),
                )
                for row in rows
            ],
        )

    async def get_top_products(
        self, seller_id: UUID, period: str, sort_by: str, limit: int
    ) -> TopProductsResponse:
        date_from = _date_from(period)

        valid_orders = select(Order.id).where(
            Order.created_at >= date_from,
            Order.status.in_(
                ["payment_confirmed", "processing", "shipped", "delivered", "completed"]
            ),
        )

        q = (
            select(
                Product.id,
                Product.name,
                Product.view_count,
                Product.avg_rating,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
                func.coalesce(func.sum(OrderItem.subtotal), 0).label("revenue"),
            )
            .outerjoin(
                OrderItem,
                and_(
                    OrderItem.product_id == Product.id,
                    OrderItem.order_id.in_(valid_orders),
                ),
            )
            .where(
                Product.seller_id == seller_id,
                Product.deleted_at.is_(None),
            )
            .group_by(Product.id)
        )

        order_col = {
            "revenue": desc("revenue"),
            "units": desc("units_sold"),
            "views": desc(Product.view_count),
        }
        q = q.order_by(order_col.get(sort_by, desc("revenue"))).limit(limit)

        rows = (await self.db.execute(q)).all()

        return TopProductsResponse(
            period=period,
            sort_by=sort_by,
            data=[
                TopProductRow(
                    product_id=str(r.id),
                    product_name=r.name,
                    image_url=None,  # hydrated on frontend
                    revenue=int(r.revenue),
                    units_sold=int(r.units_sold),
                    views=r.view_count,
                    avg_rating=float(r.avg_rating),
                )
                for r in rows
            ],
        )

    async def get_inventory_health(self, seller_id: UUID) -> InventoryHealthResponse:
        avail = ProductInventory.stock - ProductInventory.reserved

        q = (
            select(
                func.count(ProductVariant.id).label("total"),
                func.sum(case((avail > 0, 1), else_=0)).label("in_stock"),
                func.sum(case((and_(avail > 0, avail <= LOW_STOCK_THRESHOLD), 1), else_=0)).label(
                    "low_stock"
                ),
                func.sum(case((avail <= 0, 1), else_=0)).label("out_of_stock"),
                func.coalesce(func.sum(avail), 0).label("total_units"),
            )
            .join(ProductInventory, ProductVariant.id == ProductInventory.variant_id)
            .join(Product, ProductVariant.product_id == Product.id)
            .where(
                Product.seller_id == seller_id,
                ProductVariant.is_active.is_(True),
                Product.deleted_at.is_(None),
            )
        )

        r = (await self.db.execute(q)).one()
        return InventoryHealthResponse(
            total_variants=int(r.total or 0),
            in_stock=int(r.in_stock or 0),
            low_stock=int(r.low_stock or 0),
            out_of_stock=int(r.out_of_stock or 0),
            total_units=int(r.total_units or 0),
        )


# ── Admin Analytics ────────────────────────────────────────────────────────────


class AdminAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_platform_analytics(self, period: str) -> PlatformAnalytics:
        date_from = _date_from(period)

        async def scalar(q):
            return (await self.db.execute(q)).scalar_one() or 0

        total_gmv = await scalar(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                Order.created_at >= date_from,
                Order.status.in_(
                    ["payment_confirmed", "processing", "shipped", "delivered", "completed"]
                ),
            )
        )
        commission_revenue = await scalar(
            select(func.coalesce(func.sum(CommissionLedger.commission_amount), 0)).where(
                CommissionLedger.settled_at >= date_from
            )
        )
        from app.services.revenue import seller_fee_revenue
        slot_revenue = await seller_fee_revenue(self.db, date_from)
        total_orders = await scalar(
            select(func.count(Order.id)).where(Order.created_at >= date_from)
        )
        new_customers = await scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.customer,
                User.created_at >= date_from,
            )
        )
        active_sellers = await scalar(
            select(func.count(Seller.id)).where(Seller.status == SellerStatus.active)
        )
        cancelled_orders = await scalar(
            select(func.count(Order.id)).where(
                Order.created_at >= date_from,
                Order.status == OrderStatus.cancelled,
            )
        )
        cod_orders = await scalar(
            select(func.count(Order.id)).where(
                Order.created_at >= date_from,
                Order.payment_method == "cod",
            )
        )

        avg_order_value = int(total_gmv) // int(total_orders) if total_orders else 0
        cod_rate = round(int(cod_orders) / int(total_orders) * 100, 2) if total_orders else 0.0
        cancel_rate = (
            round(int(cancelled_orders) / int(total_orders) * 100, 2) if total_orders else 0.0
        )

        return PlatformAnalytics(
            period=period,
            total_gmv=int(total_gmv),
            commission_revenue=int(commission_revenue),
            slot_revenue=int(slot_revenue),
            total_orders=int(total_orders),
            new_customers=int(new_customers),
            active_sellers=int(active_sellers),
            avg_order_value=avg_order_value,
            cod_rate=cod_rate,
            cancellation_rate=cancel_rate,
        )

    async def get_platform_revenue(self, period: str, granularity: str) -> RevenueSeriesResponse:
        date_from = _date_from(period)
        trunc_unit = _trunc(granularity)

        q = (
            select(
                func.date_trunc(trunc_unit, CommissionLedger.settled_at).label("bucket"),
                func.sum(CommissionLedger.gross_amount).label("gross"),
                func.sum(CommissionLedger.commission_amount).label("commission"),
                func.sum(CommissionLedger.seller_amount).label("net"),
                func.count(CommissionLedger.id).label("orders"),
            )
            .where(CommissionLedger.settled_at >= date_from)
            .group_by("bucket")
            .order_by("bucket")
        )

        result = await self.db.execute(q)
        return RevenueSeriesResponse(
            period=period,
            granularity=granularity,
            data=[
                RevenueDayRow(
                    date=r.bucket.strftime("%Y-%m-%d"),
                    gross=int(r.gross),
                    commission=int(r.commission),
                    net=int(r.net),
                    orders=int(r.orders),
                )
                for r in result.all()
            ],
        )

    async def get_top_sellers(self, period: str, limit: int) -> TopSellersResponse:
        date_from = _date_from(period)

        q = (
            select(
                Seller.id,
                Seller.brand_name,
                Seller.logo_url,
                func.coalesce(func.sum(CommissionLedger.gross_amount), 0).label("gmv"),
                func.coalesce(func.sum(CommissionLedger.commission_amount), 0).label("commission"),
                func.count(CommissionLedger.id).label("order_count"),
            )
            .outerjoin(
                CommissionLedger,
                and_(
                    CommissionLedger.seller_id == Seller.id,
                    CommissionLedger.settled_at >= date_from,
                ),
            )
            .where(Seller.deleted_at.is_(None))
            .group_by(Seller.id)
            .order_by(desc("gmv"))
            .limit(limit)
        )

        rows = (await self.db.execute(q)).all()
        return TopSellersResponse(
            period=period,
            data=[
                TopSellerRow(
                    seller_id=str(r.id),
                    brand_name=r.brand_name,
                    logo_url=r.logo_url,
                    gmv=int(r.gmv),
                    commission=int(r.commission),
                    order_count=int(r.order_count),
                )
                for r in rows
            ],
        )

    async def get_cohort(self, months: int) -> CohortResponse:
        now = datetime.now(timezone.utc)
        current_index = now.year * 12 + now.month - 1
        first_index = current_index - months + 1
        start = datetime(first_index // 12, first_index % 12 + 1, 1, tzinfo=timezone.utc)
        rows = (
            await self.db.execute(
                text("""
            WITH first_orders AS (
                SELECT user_id, date_trunc('month', min(created_at)) AS cohort
                FROM orders WHERE user_id IS NOT NULL AND status IN
                  ('payment_confirmed','processing','shipped','delivered','completed')
                GROUP BY user_id
            ), sizes AS (
                SELECT cohort, count(*) AS size FROM first_orders WHERE cohort >= :start GROUP BY cohort
            ), activity AS (
                SELECT f.cohort, date_trunc('month', o.created_at) AS active_month,
                       count(DISTINCT o.user_id) AS active
                FROM first_orders f JOIN orders o ON o.user_id=f.user_id
                WHERE f.cohort >= :start AND o.status IN
                  ('payment_confirmed','processing','shipped','delivered','completed')
                GROUP BY f.cohort, active_month
            )
            SELECT s.cohort, s.size, a.active_month, a.active FROM sizes s
            JOIN activity a ON a.cohort=s.cohort ORDER BY s.cohort, a.active_month
        """),
                {"start": start},
            )
        ).all()
        cohorts = {}
        for row in rows:
            cohort_index = row.cohort.year * 12 + row.cohort.month - 1
            key = row.cohort.strftime("%Y-%m")
            if key not in cohorts:
                cohorts[key] = CohortRow(
                    cohort_month=key,
                    cohort_size=row.size,
                    retention=[
                        0.0 if cohort_index + i <= current_index else None for i in range(months)
                    ],
                )
            offset = (row.active_month.year * 12 + row.active_month.month - 1) - cohort_index
            if 0 <= offset < months:
                cohorts[key].retention[offset] = round(row.active / row.size * 100, 2)
        return CohortResponse(months=months, data=list(cohorts.values()))

    async def get_payment_methods(self, period: str) -> PaymentMethodsResponse:
        date_from = _date_from(period)

        q = (
            select(
                Order.payment_method,
                func.count(Order.id).label("count"),
                func.coalesce(func.sum(Order.total), 0).label("total"),
            )
            .where(
                Order.created_at >= date_from,
                Order.status.notin_(["pending_payment"]),
            )
            .group_by(Order.payment_method)
        )

        rows = (await self.db.execute(q)).all()
        data = {r.payment_method: {"count": int(r.count), "total": int(r.total)} for r in rows}
        all_total = sum(v["total"] for v in data.values()) or 1

        def stat(method: str, **extra) -> PaymentMethodStat:
            d = data.get(method, {"count": 0, "total": 0})
            return PaymentMethodStat(
                count=d["count"],
                total=d["total"],
                share=round(d["total"] / all_total * 100, 2),
                **extra,
            )

        # COD: compute verified_rate and cancellation_rate
        cod_total = data.get("cod", {}).get("count", 0) or 1
        cod_cancelled = (
            await self.db.execute(
                select(func.count(Order.id)).where(
                    Order.created_at >= date_from,
                    Order.payment_method == "cod",
                    Order.status == OrderStatus.cancelled,
                )
            )
        ).scalar_one() or 0
        cod_verified = (
            await self.db.execute(
                select(func.count(Order.id)).where(
                    Order.created_at >= date_from,
                    Order.payment_method == "cod",
                    Order.status.notin_(["pending_cod_verification", "cancelled"]),
                )
            )
        ).scalar_one() or 0

        return PaymentMethodsResponse(
            period=period,
            payfast=stat("payfast"),
            cod=stat(
                "cod",
                verified_rate=round(cod_verified / cod_total * 100, 2),
                cancellation_rate=round(cod_cancelled / cod_total * 100, 2),
            ),
        )

    async def get_cities(self, period: str, limit: int) -> CitiesResponse:
        from app.models.order import OrderAddress

        date_from = _date_from(period)

        q = (
            select(
                OrderAddress.city,
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.total), 0).label("gmv"),
            )
            .join(Order, OrderAddress.order_id == Order.id)
            .where(
                Order.created_at >= date_from,
                Order.status.in_(
                    ["payment_confirmed", "processing", "shipped", "delivered", "completed"]
                ),
            )
            .group_by(OrderAddress.city)
            .order_by(desc("gmv"))
            .limit(limit)
        )

        rows = (await self.db.execute(q)).all()
        all_gmv = sum(int(r.gmv) for r in rows) or 1

        return CitiesResponse(
            period=period,
            data=[
                CityRow(
                    city=r.city,
                    order_count=int(r.order_count),
                    total_gmv=int(r.gmv),
                    share=round(int(r.gmv) / all_gmv * 100, 2),
                )
                for r in rows
            ],
        )

    async def get_conversion(self, period: str) -> ConversionResponse:
        date_from = _date_from(period)
        rows = (
            await self.db.execute(
                select(AnalyticsEvent.kind, func.count())
                .where(AnalyticsEvent.created_at >= date_from)
                .group_by(AnalyticsEvent.kind)
            )
        ).all()
        counts = dict(rows)
        views = counts.get("product_view", 0)
        carts = counts.get("add_to_cart", 0)
        completed = await self.db.scalar(
            select(func.count(Order.id)).where(
                Order.created_at >= date_from, Order.status.in_(["delivered", "completed"])
            )
        )
        tracked = await self.db.scalar(select(func.min(AnalyticsEvent.created_at)))
        return ConversionResponse(
            period=period,
            product_views=views,
            add_to_cart=carts,
            orders_completed=completed,
            view_to_cart_rate=round(carts / views * 100, 2) if views else 0,
            cart_to_order_rate=round(completed / carts * 100, 2) if carts else 0,
            overall_cvr=round(completed / views * 100, 2) if views else 0,
            tracked_since=tracked.isoformat() if tracked else None,
        )

    async def get_search_queries(self, period: str, limit: int) -> SearchQueriesResponse:
        rows = (
            await self.db.execute(
                select(
                    AnalyticsEvent.query,
                    func.count().label("count"),
                    func.sum(case((AnalyticsEvent.result_count == 0, 1), else_=0)).label("empty"),
                )
                .where(
                    AnalyticsEvent.kind == "search", AnalyticsEvent.created_at >= _date_from(period)
                )
                .group_by(AnalyticsEvent.query)
                .order_by(desc("count"), AnalyticsEvent.query)
                .limit(limit)
            )
        ).all()
        tracked = await self.db.scalar(
            select(func.min(AnalyticsEvent.created_at)).where(AnalyticsEvent.kind == "search")
        )
        return SearchQueriesResponse(
            period=period,
            tracked_since=tracked.isoformat() if tracked else None,
            data=[
                SearchQueryRow(
                    query=r.query, count=r.count, no_result_rate=round(r.empty / r.count * 100, 2)
                )
                for r in rows
            ],
        )

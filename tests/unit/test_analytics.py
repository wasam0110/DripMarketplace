"""Unit tests — Block 11: Analytics. No DB required."""
import pytest
from datetime import datetime, timezone, timedelta
from app.services.analytics_service import _period_to_days, _date_from, _trunc


class TestPeriodHelpers:
    def test_7d(self):
        assert _period_to_days("7d") == 7

    def test_30d(self):
        assert _period_to_days("30d") == 30

    def test_90d(self):
        assert _period_to_days("90d") == 90

    def test_1y(self):
        assert _period_to_days("1y") == 365

    def test_unknown_defaults_to_30(self):
        assert _period_to_days("unknown") == 30

    def test_date_from_7d_is_recent(self):
        dt = _date_from("7d")
        now = datetime.now(timezone.utc)
        diff = now - dt
        assert 6 <= diff.days <= 8

    def test_date_from_1y(self):
        dt = _date_from("1y")
        now = datetime.now(timezone.utc)
        diff = now - dt
        assert 364 <= diff.days <= 366


class TestGranularity:
    def test_day(self):
        assert _trunc("day") == "day"

    def test_week(self):
        assert _trunc("week") == "week"

    def test_month(self):
        assert _trunc("month") == "month"

    def test_unknown_defaults_to_day(self):
        assert _trunc("hour") == "day"


class TestAnalyticsSchemas:
    def test_seller_overview_schema(self):
        from app.schemas.analytics import SellerAnalyticsOverview
        s = SellerAnalyticsOverview(
            period="30d", gross_revenue=100000, commission_paid=15000,
            net_earnings=85000, order_count=50, units_sold=120,
            avg_order_value=2000, total_views=5000, conversion_rate=1.0,
        )
        assert s.net_earnings == 85000

    def test_platform_analytics_schema(self):
        from app.schemas.analytics import PlatformAnalytics
        p = PlatformAnalytics(
            period="30d", total_gmv=5000000, commission_revenue=750000,
            slot_revenue=250000, total_orders=1000, new_customers=200,
            active_sellers=50, avg_order_value=5000, cod_rate=45.0,
            cancellation_rate=8.5,
        )
        assert p.total_gmv == 5000000

    def test_revenue_day_row(self):
        from app.schemas.analytics import RevenueDayRow
        r = RevenueDayRow(
            date="2026-08-01", gross=50000, commission=7500, net=42500, orders=10
        )
        assert r.gross - r.commission == r.net

    def test_payment_method_stat(self):
        from app.schemas.analytics import PaymentMethodStat
        s = PaymentMethodStat(count=100, total=500000, share=45.0)
        assert s.share == 45.0

    def test_inventory_health_schema(self):
        from app.schemas.analytics import InventoryHealthResponse
        h = InventoryHealthResponse(
            total_variants=100, in_stock=80, low_stock=10,
            out_of_stock=10, total_units=3500,
        )
        assert h.in_stock + h.out_of_stock + (h.low_stock - 0) <= h.total_variants + h.low_stock

    def test_city_row(self):
        from app.schemas.analytics import CityRow
        c = CityRow(city="Karachi", order_count=500, total_gmv=2500000, share=45.5)
        assert c.city == "Karachi"
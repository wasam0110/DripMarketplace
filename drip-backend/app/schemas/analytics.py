from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


# ── Seller ─────────────────────────────────────────────────────────────────────

class SellerAnalyticsOverview(BaseModel):
    period:          str
    gross_revenue:   int
    commission_paid: int
    net_earnings:    int
    order_count:     int
    units_sold:      int
    avg_order_value: int
    total_views:     int
    conversion_rate: float


class RevenueDayRow(BaseModel):
    date:       str
    gross:      int
    commission: int
    net:        int
    orders:     int


class RevenueSeriesResponse(BaseModel):
    period:      str
    granularity: str
    data:        list[RevenueDayRow]


class TopProductRow(BaseModel):
    product_id:   str
    product_name: str
    image_url:    Optional[str]
    revenue:      int
    units_sold:   int
    views:        int
    avg_rating:   float


class TopProductsResponse(BaseModel):
    period:   str
    sort_by:  str
    data:     list[TopProductRow]


class InventoryHealthResponse(BaseModel):
    total_variants: int
    in_stock:       int
    low_stock:      int
    out_of_stock:   int
    total_units:    int


# ── Admin ──────────────────────────────────────────────────────────────────────

class PlatformAnalytics(BaseModel):
    period:             str
    total_gmv:          int
    commission_revenue: int
    slot_revenue:       int
    total_orders:       int
    new_customers:      int
    active_sellers:     int
    avg_order_value:    int
    cod_rate:           float
    cancellation_rate:  float


class TopSellerRow(BaseModel):
    seller_id:   str
    brand_name:  str
    logo_url:    Optional[str]
    gmv:         int
    commission:  int
    order_count: int


class TopSellersResponse(BaseModel):
    period: str
    data:   list[TopSellerRow]


class CohortRow(BaseModel):
    cohort_month: str
    cohort_size:  int
    retention:    list[Optional[float]]


class CohortResponse(BaseModel):
    months: int
    data:   list[CohortRow]


class PaymentMethodStat(BaseModel):
    count:             int
    total:             int
    share:             float
    verified_rate:     Optional[float] = None
    cancellation_rate: Optional[float] = None


class PaymentMethodsResponse(BaseModel):
    period:    str
    jazzcash:  PaymentMethodStat
    easypaisa: PaymentMethodStat
    card:      PaymentMethodStat
    cod:       PaymentMethodStat


class CityRow(BaseModel):
    city:        str
    order_count: int
    total_gmv:   int
    share:       float


class CitiesResponse(BaseModel):
    period: str
    data:   list[CityRow]


class ConversionResponse(BaseModel):
    period:             str
    product_views:      int
    add_to_cart:        int
    orders_completed:   int
    view_to_cart_rate:  float
    cart_to_order_rate: float
    overall_cvr:        float


class SearchQueryRow(BaseModel):
    query:          str
    count:          int
    no_result_rate: float


class SearchQueriesResponse(BaseModel):
    period: str
    data:   list[SearchQueryRow]
"""Money stays Decimal in Python and an exact decimal string on the wire."""

from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.analytics import (
    AnalyticsMoney,
    CityRow,
    PaymentMethodStat,
    PlatformAnalytics,
    RevenueDayRow,
    SellerAnalyticsOverview,
    TopProductRow,
    TopSellerRow,
)
from app.services.analytics_service import _money


@pytest.mark.parametrize(
    "model,fields,other",
    [
        (
            SellerAnalyticsOverview,
            ["gross_revenue", "commission_paid", "net_earnings", "avg_order_value"],
            {
                "period": "30d",
                "order_count": 1,
                "units_sold": 1,
                "total_views": 1,
                "conversion_rate": 100.0,
            },
        ),
        (RevenueDayRow, ["gross", "commission", "net"], {"date": "2026-10-16", "orders": 1}),
        (
            TopProductRow,
            ["revenue"],
            {
                "product_id": "test",
                "product_name": "test",
                "image_url": None,
                "units_sold": 1,
                "views": 1,
                "avg_rating": 4.0,
            },
        ),
        (
            PlatformAnalytics,
            ["total_gmv", "commission_revenue", "slot_revenue", "avg_order_value"],
            {
                "period": "30d",
                "total_orders": 1,
                "new_customers": 1,
                "active_sellers": 1,
                "cod_rate": 100.0,
                "cancellation_rate": 0.0,
            },
        ),
        (
            TopSellerRow,
            ["gmv", "commission"],
            {"seller_id": "test", "brand_name": "test", "logo_url": None, "order_count": 1},
        ),
        (PaymentMethodStat, ["total"], {"count": 1, "share": 100.0}),
        (CityRow, ["total_gmv"], {"city": "Karachi", "order_count": 1, "share": 100.0}),
    ],
)
def test_all_money_fields_preserve_large_decimal_and_publish_string_schema(model, fields, other):
    # An aggregate can exceed a single stored row's bound and JS's exact integer range.
    amount = Decimal("9007199254740993.01")
    value = model(**dict.fromkeys(fields, amount), **other)
    schema = model.model_json_schema(mode="serialization")["properties"]
    wire = value.model_dump(mode="json")
    for field in fields:
        assert getattr(value, field) == amount
        assert isinstance(getattr(value, field), Decimal)
        assert wire[field] == "9007199254740993.01"
        assert schema[field]["type"] == "string"
        assert "PKR major units" in schema[field]["description"]
    for field, expected in other.items():
        assert type(wire[field]) is type(expected)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0", "0.00"),
        ("1.004", "1.00"),
        ("1.005", "1.01"),
        ("1.006", "1.01"),
        ("9999.999", "10000.00"),
    ],
)
def test_money_rounding_is_explicit_half_up(value, expected):
    assert str(_money(Decimal(value))) == expected


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "1.001"])
def test_money_schema_rejects_nonfinite_or_unrounded_output(value):
    with pytest.raises(ValidationError):
        TypeAdapter(AnalyticsMoney).validate_python(Decimal(value))

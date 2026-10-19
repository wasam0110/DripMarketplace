"""Seller fulfilment read contracts match the existing payload, not legacy placeholders."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from main import create_application
from pydantic import ValidationError

from app.schemas.seller import (
    OrderItemSchema,
    PaginatedSellerOrders,
    SellerOrderDetailResponse,
    SellerOrderRow,
)

pytestmark = pytest.mark.unit


def row(subtotal=Decimal("2401.50")):
    return {
        "id": str(uuid4()),
        "order_id": str(uuid4()),
        "order_number": "WHZ-CONTRACT",
        "status": "pending",
        "subtotal": subtotal,
        "tracking_number": None,
        "courier_name": None,
        "shipped_at": None,
        "delivered_at": None,
        "created_at": "2026-10-18T11:12:13.123456+00:00",
    }


def detail():
    return {
        **row(),
        "shipping_address": {
            "recipient_name": "Synthetic Buyer",
            "phone": "03001234567",
            "street": "12 Test Street",
            "city": "Lahore",
            "province": "Punjab",
            "note": None,
        },
        "items": [
            {
                "product_name": "Own product",
                "variant_label": "M",
                "unit_price": Decimal("1200.75"),
                "quantity": 2,
                "subtotal": Decimal("2401.50"),
            }
        ],
    }


@pytest.mark.parametrize(
    "value,expected",
    [(0, "0.00"), (1200, "1200.00"), ("1200.2", "1200.20"), (Decimal("1200.25"), "1200.25")],
)
def test_row_preserves_live_fields_and_exact_pkr(value, expected):
    payload = row(value)
    model = SellerOrderRow.model_validate(payload)
    assert isinstance(model.subtotal, Decimal)
    assert model.model_dump(mode="json") == {**payload, "subtotal": expected}


def test_detail_preserves_existing_shape_without_phantom_fields():
    payload = detail()
    result = SellerOrderDetailResponse.model_validate(payload).model_dump(mode="json")
    assert set(result) == set(payload)
    assert result["shipping_address"] == payload["shipping_address"]
    assert result["subtotal"] == "2401.50"
    assert result["items"] == [
        {
            **payload["items"][0],
            "unit_price": "1200.75",
            "subtotal": "2401.50",
        }
    ]
    assert type(result["items"][0]["quantity"]) is int
    for absent in (
        "net_amount",
        "commission_amount",
        "customer_name",
        "payment_method",
        "cod_verified",
    ):
        assert absent not in result


@pytest.mark.parametrize("field", ["unit_price", "subtotal"])
@pytest.mark.parametrize("value", ["NaN", "Infinity", "-0.01", "1.001"])
def test_item_rejects_invalid_money_instead_of_rounding(field, value):
    payload = detail()["items"][0]
    payload[field] = value
    with pytest.raises(ValidationError):
        OrderItemSchema.model_validate(payload)


@pytest.mark.parametrize("value", [None, datetime(2026, 10, 18, 10, 5, tzinfo=UTC)])
def test_optional_fulfilment_times_keep_isoformat(value):
    payload = row()
    payload["shipped_at"] = payload["delivered_at"] = value
    result = SellerOrderRow.model_validate(payload).model_dump(mode="json")
    expected = value.isoformat() if value else None
    assert result["shipped_at"] == result["delivered_at"] == expected
    assert result["created_at"] == payload["created_at"]


def test_empty_page_keeps_pagination_contract():
    payload = {"data": [], "pagination": {"page": 2, "per_page": 25, "total": 0, "total_pages": 1}}
    assert PaginatedSellerOrders.model_validate(payload).model_dump(mode="json") == payload


def test_openapi_publishes_actual_seller_order_contracts():
    schema = create_application().openapi()
    for path, model in [
        ("/api/v1/seller/orders", "PaginatedSellerOrders"),
        ("/api/v1/seller/orders/{seller_order_id}", "SellerOrderDetailResponse"),
    ]:
        response = schema["paths"][path]["get"]["responses"]["200"]
        assert response["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{model}"
        }
    definitions = schema["components"]["schemas"]
    for model, fields in [
        ("SellerOrderRow", ["subtotal"]),
        ("OrderItemSchema", ["unit_price", "subtotal"]),
    ]:
        for field in fields:
            assert definitions[model]["properties"][field]["type"] == "string"
    assert set(definitions["SellerOrderRow"]["properties"]) == set(row())
    assert set(definitions["SellerOrderDetailResponse"]["properties"]) == set(detail())

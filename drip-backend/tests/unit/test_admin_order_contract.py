"""Admin order contracts preserve decimal strings without exposing access secrets."""

import pytest
from main import create_application

from app.schemas.admin import AdminOrderRowResponse, OrderTotals, PaginatedAdminOrders

pytestmark = pytest.mark.unit


def test_money_and_pagination_contract():
    row = AdminOrderRowResponse(
        id="11111111-1111-4111-8111-111111111111",
        order_number="WHZ-TEST",
        status="processing",
        customer_name="Snapshot name",
        seller_count=2,
        subtotal="1700.55",
        total="1800.75",
        commission="150.06",
        payment_method="cod",
        created_at="2026-10-28T00:00:00Z",
    )
    page = PaginatedAdminOrders(
        data=[row],
        totals=OrderTotals(total_gmv="999999999999.99", total_commission="150.06", order_count=1),
        total=1,
        page=1,
        per_page=25,
        total_pages=1,
    ).model_dump(mode="json")
    assert page["data"][0]["commission"] == "150.06"
    assert page["totals"]["total_gmv"] == "999999999999.99"
    assert page["per_page"] == 25 and page["total_pages"] == 1


def test_openapi_private_read_contracts():
    schema = create_application().openapi()
    private = schema["components"]["schemas"]["AdminOrderDetailResponse"]
    assert {"user_id", "commission", "customer_name", "address", "items", "seller_orders"} <= set(
        private["required"]
    )
    assert not {
        "checkout_key_hash",
        "checkout_request_hash",
        "guest_email",
        "guest_phone",
        "guest_token",
        "access_token",
    } & set(private["properties"])
    public = schema["components"]["schemas"]["OrderDetailResponse"]
    assert not {"commission", "user_id", "customer_name"} & set(public["properties"])
    endpoint = schema["paths"]["/api/v1/admin/orders/{order_id}"]
    assert set(endpoint) == {"get"}
    assert endpoint["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/AdminOrderDetailResponse"
    }

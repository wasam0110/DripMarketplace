"""Admin catalogue schema matches the existing read payload and exact PKR values."""

from decimal import Decimal
from uuid import uuid4

import pytest
from main import create_application
from pydantic import ValidationError

from app.schemas import product

pytestmark = pytest.mark.unit


def row(price):
    return {
        "id": str(uuid4()),
        "seller_id": str(uuid4()),
        "name": "Synthetic product",
        "price": price,
        "slug": "synthetic-product",
        "is_published": False,
        "admin_hidden": True,
    }


@pytest.mark.parametrize(
    "value,expected",
    [
        (100, "100.00"),
        ("1500.2", "1500.20"),
        (Decimal("1500.25"), "1500.25"),
        (Decimal("500000.00"), "500000.00"),
    ],
)
def test_row_preserves_live_fields_and_money(value, expected):
    payload = row(value)
    model = product.AdminProductRowResponse.model_validate(payload)
    assert isinstance(model.price, Decimal)
    assert model.model_dump(mode="json") == {**payload, "price": expected}


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "-0.01", "100.001"])
def test_invalid_money_is_not_silently_rounded(value):
    with pytest.raises(ValidationError):
        product.AdminProductRowResponse.model_validate(row(value))


def test_empty_page_does_not_invent_pagination_fields():
    payload = {"data": [], "pagination": {"page": 2, "per_page": 25, "total": 0}}
    assert product.AdminProductsPage.model_validate(payload).model_dump(mode="json") == payload


def test_openapi_documents_admin_product_contract():
    schema = create_application().openapi()
    response = schema["paths"]["/api/v1/admin/products"]["get"]["responses"]["200"]
    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/AdminProductsPage"
    }
    definitions = schema["components"]["schemas"]
    properties = definitions["AdminProductRowResponse"]["properties"]
    assert set(properties) == set(row(100))
    assert properties["price"]["type"] == "string"
    assert "PKR" in properties["price"]["description"]
    assert set(definitions["AdminProductsPagination"]["properties"]) == {
        "page",
        "per_page",
        "total",
    }

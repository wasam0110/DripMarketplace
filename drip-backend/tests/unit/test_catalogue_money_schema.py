"""Exact catalogue response contracts without widening price-entry policy."""

from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.money import PKRResponseAmount
from app.schemas.product import (
    CreateProductRequest,
    CreateVariantRequest,
    ProductCardResponse,
    ProductDetailResponse,
    SearchSuggestion,
    SellerProductRowResponse,
    UpdateProductRequest,
    UpdateVariantRequest,
    VariantWithStockResponse,
)
from app.schemas.user import WishlistItemResponse

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "0.00"),
        (1500, "1500.00"),
        ("1500.2", "1500.20"),
        (Decimal("1500.25"), "1500.25"),
        (Decimal("500000.00"), "500000.00"),
    ],
)
def test_pkr_amount_is_decimal_in_python_and_fixed_string_in_json(value, expected):
    adapter = TypeAdapter(PKRResponseAmount)
    validated = adapter.validate_python(value)
    assert isinstance(validated, Decimal)
    assert adapter.dump_python(validated) == Decimal(expected)
    assert adapter.dump_python(validated, mode="json") == expected
    assert adapter.dump_json(validated) == f'"{expected}"'.encode()


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "-0.01", "1500.251"])
def test_response_rejects_invalid_amount_instead_of_truncating(value):
    with pytest.raises(ValidationError):
        TypeAdapter(PKRResponseAmount).validate_python(value)


@pytest.mark.parametrize(
    "model",
    [
        ProductCardResponse,
        ProductDetailResponse,
        VariantWithStockResponse,
        SellerProductRowResponse,
        SearchSuggestion,
        WishlistItemResponse,
    ],
)
def test_openapi_documents_price_strings_and_nullable_sale(model):
    properties = model.model_json_schema(mode="serialization")["properties"]
    assert properties["price"]["type"] == "string"
    if "sale_price" in properties:
        assert {branch["type"] for branch in properties["sale_price"]["anyOf"]} == {
            "string",
            "null",
        }


@pytest.mark.parametrize(
    "model,payload",
    [
        (CreateProductRequest, {"name": "Linen Shirt", "description": "A linen shirt."}),
        (UpdateProductRequest, {}),
        (
            CreateVariantRequest,
            {"size_type": "alpha", "size_value": "M", "colour": "Ivory", "stock": 2},
        ),
        (UpdateVariantRequest, {}),
    ],
)
def test_price_entry_policy_still_whole_rupees(model, payload):
    field = "price_override" if model in {CreateVariantRequest, UpdateVariantRequest} else "price"
    request = model(**payload, **{field: 1500})
    assert type(getattr(request, field)) is int
    for invalid in ["1500.25", "NaN", 99, 500001]:
        with pytest.raises(ValidationError):
            model(**payload, **{field: invalid})

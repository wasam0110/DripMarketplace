"""Fixed catalogue policy stays aligned across request, service and SQL boundaries."""

from uuid import uuid4

import pytest
from main import create_application
from pydantic import ValidationError

from app.core.catalogue_policy import (
    MAX_IMAGE_BYTES,
    MAX_IMAGES_PER_PRODUCT,
    MAX_PRODUCT_PRICE,
    MIN_PRODUCT_PRICE,
)
from app.core.exceptions import BusinessRuleError
from app.models.product import Product
from app.schemas.product import (
    CreateProductRequest,
    CreateVariantRequest,
    ReorderImagesRequest,
    UpdateProductRequest,
    UpdateVariantRequest,
)
from app.services import image_service, product_service

pytestmark = pytest.mark.unit
PRICE_FIELDS = [
    (CreateProductRequest, "price"),
    (CreateProductRequest, "sale_price"),
    (UpdateProductRequest, "price"),
    (UpdateProductRequest, "sale_price"),
    (CreateVariantRequest, "price_override"),
    (UpdateVariantRequest, "price_override"),
]


@pytest.mark.parametrize("model,field", PRICE_FIELDS)
@pytest.mark.parametrize("amount", [99, 100, 500000, 500001, 100.25])
def test_product_price_boundaries_and_whole_pkr_policy(model, field, amount):
    payload = {}
    if model is CreateProductRequest:
        payload = {
            "name": "Synthetic shirt",
            "description": "A synthetic test description",
            "price": MAX_PRODUCT_PRICE,
        }
    elif model is CreateVariantRequest:
        payload = {"size_type": "alpha", "size_value": "M", "colour": "Black", "stock": 1}
    payload[field] = amount
    valid = MIN_PRODUCT_PRICE <= amount <= MAX_PRODUCT_PRICE and amount == int(amount)
    if model is CreateProductRequest and field == "sale_price" and amount == MAX_PRODUCT_PRICE:
        valid = False  # The separate sale < base price rule remains in force.
    if valid:
        assert getattr(model.model_validate(payload), field) == amount
    else:
        with pytest.raises(ValidationError):
            model.model_validate(payload)


@pytest.mark.parametrize("count,valid", [(0, False), (1, True), (6, True), (7, False)])
def test_image_reorder_size_boundary(count, valid):
    payload = {"image_ids": [uuid4() for _ in range(count)]}
    if valid:
        assert len(ReorderImagesRequest(**payload).image_ids) == count
    else:
        with pytest.raises(ValidationError):
            ReorderImagesRequest(**payload)


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_image_byte_boundary_before_conversion(delta):
    data = b"\x89PNG" + b"x" * (MAX_IMAGE_BYTES + delta - 4)
    service = image_service.ImageService()
    if delta <= 0:
        assert service.validate(data) == "image/png"
    else:
        with pytest.raises(BusinessRuleError, match="5 MB"):
            service.validate(data)


def test_policy_defaults_compatibility_aliases_and_sql_constraints():
    assert (MIN_PRODUCT_PRICE, MAX_PRODUCT_PRICE, MAX_IMAGES_PER_PRODUCT) == (100, 500000, 6)
    assert image_service.MAX_FILE_SIZE == MAX_IMAGE_BYTES == 5 * 1024 * 1024
    assert product_service.MAX_IMAGES_PER_PRODUCT == MAX_IMAGES_PER_PRODUCT
    checks = {
        c.name: str(c.sqltext) for c in Product.__table__.constraints if hasattr(c, "sqltext")
    }
    assert checks["ck_products_price_positive"] == f"price >= {MIN_PRODUCT_PRICE}"
    assert checks["ck_products_price_max"] == f"price <= {MAX_PRODUCT_PRICE}"


def test_openapi_bounds_match_shared_policy_and_keep_zero_filter():
    spec = create_application().openapi()
    schemas = spec["components"]["schemas"]
    for model, field in PRICE_FIELDS:
        shape = schemas[model.__name__]["properties"][field]
        if "anyOf" in shape:
            shape = next(item for item in shape["anyOf"] if item["type"] == "integer")
        assert shape["minimum"] == MIN_PRODUCT_PRICE
        assert shape["maximum"] == MAX_PRODUCT_PRICE
    assert (
        schemas["ReorderImagesRequest"]["properties"]["image_ids"]["maxItems"]
        == MAX_IMAGES_PER_PRODUCT
    )
    params = {
        p["name"]: p["schema"] for p in spec["paths"]["/api/v1/products"]["get"]["parameters"]
    }
    assert next(s for s in params["min_price"]["anyOf"] if s["type"] == "integer")["minimum"] == 0
    assert (
        next(s for s in params["max_price"]["anyOf"] if s["type"] == "integer")["maximum"]
        == MAX_PRODUCT_PRICE
    )

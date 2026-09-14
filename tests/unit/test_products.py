"""
Unit tests — Block 4: Products
Run: pytest tests/unit/test_products.py -v --no-cov
No DB required.
"""
import pytest
from pydantic import ValidationError

from app.services.product_service import _slugify
from app.schemas.product import (
    CreateProductRequest,
    UpdateProductRequest,
    CreateVariantRequest,
)

VALID_PRODUCT = {
    "name":        "DRIP Classic Tee",
    "description": "Premium 100% cotton streetwear tee for the culture",
    "price":       2500,
}

VALID_VARIANT = {
    "size_type":  "alpha",
    "size_value": "M",
    "colour":     "Black",
    "stock":      10,
}


class TestSlugify:
    def test_basic(self):
        assert _slugify("DRIP Classic Tee") == "drip-classic-tee"

    def test_strips_non_ascii(self):
        assert _slugify("Streetwear & Co") == "streetwear-co"

    def test_max_length(self):
        assert len(_slugify("A" * 400)) <= 250

    def test_numbers_preserved(self):
        assert _slugify("Jordan 23 Hoodie") == "jordan-23-hoodie"


class TestCreateProductSchema:
    def test_valid_minimal(self):
        req = CreateProductRequest(**VALID_PRODUCT)
        assert req.name == "DRIP Classic Tee"
        assert req.is_published is False
        assert req.variants == []

    def test_price_too_low(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(**{**VALID_PRODUCT, "price": 50})

    def test_price_too_high(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(**{**VALID_PRODUCT, "price": 600_000})

    def test_sale_price_must_be_less_than_price(self):
        with pytest.raises(ValidationError, match="sale_price must be less than price"):
            CreateProductRequest(**{**VALID_PRODUCT, "sale_price": 3000})

    def test_sale_price_equal_to_price_rejected(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(**{**VALID_PRODUCT, "sale_price": 2500})

    def test_valid_sale_price(self):
        req = CreateProductRequest(**{**VALID_PRODUCT, "sale_price": 1999})
        assert req.sale_price == 1999

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(**{**VALID_PRODUCT, "name": "A"})

    def test_description_too_short(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(**{**VALID_PRODUCT, "description": "Short"})

    def test_with_variants(self):
        req = CreateProductRequest(**{**VALID_PRODUCT, "variants": [VALID_VARIANT]})
        assert len(req.variants) == 1
        assert req.variants[0].size_value == "M"


class TestCreateVariantSchema:
    def test_valid_alpha(self):
        v = CreateVariantRequest(**VALID_VARIANT)
        assert v.size_type == "alpha"

    def test_valid_numeric(self):
        v = CreateVariantRequest(size_type="numeric", size_value="32", colour="Blue", stock=5)
        assert v.size_type == "numeric"

    def test_valid_one_size(self):
        v = CreateVariantRequest(size_type="one_size", size_value="OS", colour="Red", stock=0)
        assert v.size_type == "one_size"

    def test_invalid_size_type(self):
        with pytest.raises(ValidationError):
            CreateVariantRequest(size_type="XXL", size_value="XXL", colour="Black", stock=5)

    def test_negative_stock_rejected(self):
        with pytest.raises(ValidationError):
            CreateVariantRequest(**{**VALID_VARIANT, "stock": -1})

    def test_price_override_too_low(self):
        with pytest.raises(ValidationError):
            CreateVariantRequest(**{**VALID_VARIANT, "price_override": 50})


class TestUpdateProductSchema:
    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="At least one"):
            UpdateProductRequest()

    def test_single_field_ok(self):
        req = UpdateProductRequest(name="New Name Here")
        assert req.name == "New Name Here"

    def test_price_validation(self):
        with pytest.raises(ValidationError):
            UpdateProductRequest(price=50)
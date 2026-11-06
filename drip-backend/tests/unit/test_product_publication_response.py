"""The detail contract reports persisted publication state, including drafts."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.schemas.product import ProductCardResponse, ProductDetailResponse
from app.services.product_service import ProductService


@pytest.mark.unit
@pytest.mark.parametrize("published", [False, True])
def test_detail_reports_saved_publication_state(published):
    seller_id = uuid4()
    card = ProductCardResponse(
        id=uuid4(), seller_id=seller_id, brand_name="Test label", brand_color="#203C32",
        name="Linen shirt", slug="linen-shirt", price="2500.00", sale_price=None,
        primary_image=None, colours=[], alpha_sizes=[], numeric_sizes=[],
        avg_rating=0, review_count=0, is_new=True, has_stock=False,
    )
    product = SimpleNamespace(
        is_published=published, description="A lightweight linen shirt.",
        meta_title=None, meta_description=None, images=[], variants=[], category=None,
        created_at=datetime.now(UTC),
        seller=SimpleNamespace(
            id=seller_id, brand_name="Test label", slug="test-label", logo_url=None,
            brand_color="#203C32", return_policy=None, whatsapp_number=None,
        ),
    )
    service = ProductService.__new__(ProductService)
    service._to_card = Mock(return_value=card)
    detail = service._to_detail(product)
    assert detail.is_published is published
    assert detail.model_dump(mode="json")["is_published"] is published
    assert detail.id == card.id
    assert detail.seller_id == seller_id


@pytest.mark.unit
def test_publication_state_is_required_not_assumed():
    assert ProductDetailResponse.model_fields["is_published"].is_required()

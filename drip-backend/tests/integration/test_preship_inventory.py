"""Inventory thresholds are persisted and scoped, not discarded request fields."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_marketplace_regressions import market as marketplace_fixture

from app.api.v1.inventory import SetStockRequest
from app.core.exceptions import NotFoundError
from app.services.inventory_service import InventoryService

pytestmark = pytest.mark.integration
market = marketplace_fixture


async def test_reorder_threshold_round_trip_and_filters(db, market):
    service = InventoryService(db)
    assert market.inventory.reorder_point == 5
    changed = await service.set_stock(market.variant.id, market.seller.id, 8, 10)
    assert changed.reorder_point == 10 and changed.is_low_stock
    assert (await service.get_low_stock(market.seller.id)).total == 1
    for listing, kwargs in [
        (service.list_seller_inventory, {}), (service.admin_list_inventory, {}),
    ]:
        page = await listing(seller_id=market.seller.id, product_id=None,
                             low_stock_only=True, q=None, page=1, per_page=20, **kwargs)
        assert page.total == 1 and page.data[0].reorder_point == 10
    unchanged = await service.set_stock(market.variant.id, market.seller.id, 8, None)
    assert unchanged.reorder_point == 10
    zero = await service.set_stock(market.variant.id, market.seller.id, 8, 0)
    assert zero.reorder_point == 0 and not zero.is_low_stock
    assert (await service.get_low_stock(market.seller.id)).total == 0
    with pytest.raises(NotFoundError):
        await service.set_stock(market.variant.id, uuid4(), 8, 100)
    await db.refresh(market.inventory)
    assert market.inventory.reorder_point == 0


@pytest.mark.parametrize("threshold", [-1, 1_000_000])
def test_threshold_bounds(threshold):
    with pytest.raises(ValidationError):
        SetStockRequest(stock=1, reorder_point=threshold)

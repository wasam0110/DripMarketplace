"""Seller inventory pages retain a deterministic order for an unchanged catalogue."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.services.inventory_service import InventoryService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seller_inventory_has_stable_order_and_scope() -> None:
    seller_id = uuid4()
    db = AsyncMock()
    db.execute.side_effect = [
        Mock(scalar_one=Mock(return_value=0)), Mock(all=Mock(return_value=[])),
    ]
    result = await InventoryService(db).list_seller_inventory(
        seller_id=seller_id, product_id=None, low_stock_only=True, q=None,
        page=2, per_page=20,
    )
    query = db.execute.call_args_list[1].args[0]
    sql = str(
        query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )
    assert "ORDER BY products.id, product_variants.id" in sql
    assert str(seller_id) in sql
    assert "products.deleted_at IS NULL" in sql
    assert "product_inventory.stock - product_inventory.reserved" in sql
    assert "LIMIT 20 OFFSET 20" in sql
    assert result.data == []

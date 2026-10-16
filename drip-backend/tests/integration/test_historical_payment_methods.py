"""Legacy rows remain readable; removed checkout gateways remain unavailable."""

import pytest
from pydantic import ValidationError
from test_marketplace_regressions import guest_payload
from test_marketplace_regressions import market as marketplace_fixture

from app.core.exceptions import BusinessRuleError
from app.models.order import Order, StoredPaymentMethod
from app.schemas.payment import RetryPaymentRequest
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

pytestmark = pytest.mark.integration
market = marketplace_fixture


@pytest.mark.parametrize("method", ["jazzcash", "easypaisa", "card"])
async def test_historical_method_readable_but_not_payable(db, market, method):
    created = await OrderService(db).create_guest_order(guest_payload(market))
    order = await db.get(Order, created.order_id)
    order.payment_method = StoredPaymentMethod(method)
    await db.commit()
    await db.refresh(order)
    assert order.payment_method.value == method
    with pytest.raises(ValidationError):
        RetryPaymentRequest(payment_method=method)
    with pytest.raises(BusinessRuleError, match="Historical payment methods"):
        await PaymentService(db).initiate(order.id, guest_token=created.guest_token)

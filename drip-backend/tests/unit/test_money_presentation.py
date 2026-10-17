"""PKR presentation preserves fractions without changing stored accounting values."""

from decimal import ROUND_DOWN, ROUND_UP, Decimal, localcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.exceptions import BusinessRuleError, NoSlotsAvailableError, PermissionDeniedError
from app.core.money import format_pkr
from app.integrations import resend_client
from app.schemas.seller import SlotPricingResponse, SlotPurchaseResponse
from app.services.product_service import ProductService
from app.services.slot_service import SlotService

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("rounding", [ROUND_DOWN, ROUND_UP])
@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "0.00"),
        (1000, "1,000.00"),
        (1000.25, "1,000.25"),
        (Decimal("1000.25"), "1,000.25"),
        ("0.01", "0.01"),
        ("1.005", "1.01"),
        (Decimal("1.004"), "1.00"),
        ("9999999999.99", "9,999,999,999.99"),
    ],
)
def test_pkr_formatting_is_exact_and_explicit(rounding, value, expected):
    with localcontext() as context:
        context.rounding = rounding
        assert format_pkr(value) == expected


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "<b>1</b>", "invalid"])
def test_invalid_money_cannot_be_rendered(value):
    with pytest.raises(ValueError):
        format_pkr(value)


@pytest.mark.parametrize(
    "amount,expected",
    [
        (2600, "2,600.00"),
        (Decimal("2600.75"), "2,600.75"),
        ("2600.75", "2,600.75"),
    ],
)
async def test_legacy_order_email_accepts_decimal_queue_values(monkeypatch, amount, expected):
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(resend_client, "send_email", sender)
    assert await resend_client.send_order_confirmation_email(
        "test@example.test",
        "Customer",
        "WHZ-MONEY",
        amount,
        [{"product_name": "Shirt", "quantity": 1, "subtotal": amount}],
    )
    html = sender.await_args.kwargs["html"]
    assert html.count(f"PKR {expected}") == 2


@pytest.mark.parametrize("quantity", [0, 3])
def test_slot_money_is_two_place_json_string_but_counts_stay_integer(quantity):
    pricing = SlotService.calculate_pricing(quantity)
    data = pricing.model_dump(mode="json")
    for name in ("registration_fee", "extra_slot_price", "extra_cost", "total_cost"):
        assert isinstance(getattr(pricing, name), Decimal)
        assert data[name] == f"{getattr(pricing, name):.2f}"
        assert (
            SlotPricingResponse.model_json_schema(mode="serialization")["properties"][name]["type"]
            == "string"
        )
    for name in ("base_slots", "extra_slots", "total_slots"):
        assert type(data[name]) is int
    purchased = SlotPurchaseResponse(
        slots_purchased=3,
        new_total_slots=53,
        new_slots_available=53,
        amount_charged=Decimal("261.75"),
    )
    assert purchased.model_dump(mode="json")["amount_charged"] == "261.75"


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-0.01", "1.001"])
@pytest.mark.parametrize("purchase", [False, True])
def test_slot_responses_reject_invalid_or_unrounded_money(value, purchase):
    with pytest.raises(ValidationError):
        if purchase:
            SlotPurchaseResponse(
                slots_purchased=1, new_total_slots=51, new_slots_available=51, amount_charged=value
            )
        else:
            SlotPricingResponse(extra_slots=1, extra_cost=value, total_cost=5000, total_slots=51)


@pytest.mark.parametrize("source", ["default", "slot", "publish"])
async def test_slot_limit_errors_do_not_advertise_a_fixed_price(source):
    if source == "default":
        message = NoSlotsAvailableError().message
    else:
        db = AsyncMock()
        service = SlotService(db) if source == "slot" else ProductService(db)
        service.seller_repo = AsyncMock()
        service.seller_repo.get_by_id.return_value = SimpleNamespace(slots_used=50, total_slots=50)
        service._require_owned = AsyncMock(
            return_value=SimpleNamespace(
                is_published=False,
                variants=[object()],
                images=[object()],
            )
        )
        with pytest.raises((BusinessRuleError, PermissionDeniedError)) as error:
            if source == "slot":
                await service.assert_slot_available(uuid4())
            else:
                await service.publish_product(uuid4(), uuid4())
        message = error.value.message
        db.commit.assert_not_awaited()
    assert "current slot pricing" in message and "PKR 50" not in message

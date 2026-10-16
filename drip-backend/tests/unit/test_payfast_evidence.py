"""Never infer payment amounts or currency from local defaults."""

from decimal import Decimal

import pytest

from app.services.payment_service import _provider_money_matches


@pytest.mark.parametrize("evidence", [
    {}, {"amount": "2600"}, {"currency": "PKR"},
    {"amount": "Infinity", "currency": "PKR"},
    {"amount": "NaN", "currency": "PKR"},
    {"amount": None, "currency": "PKR"},
    {"amount": True, "currency": "PKR"},
    {"amount": "-2600", "currency": "PKR"},
    {"amount": "2600", "txnamt": "1", "currency": "PKR"},
    {"amount": "2600", "currency": "PKR", "currency_code": "USD"},
])
def test_missing_invalid_or_conflicting_money_is_rejected(evidence):
    assert not _provider_money_matches(evidence, Decimal("2600"), "PKR")


def test_explicit_consistent_money_is_accepted():
    assert _provider_money_matches(
        {"amount": "2600.00", "txnamt": 2600, "currency": "pkr", "currency_code": "PKR"},
        Decimal("2600"), "PKR",
    )


def test_enabled_gateway_requires_authoritative_status_api():
    from pydantic import ValidationError

    from app.core.config import Settings, settings

    values = settings.model_dump()
    values.update(PAYFAST_ENABLED=True, PAYFAST_MERCHANT_ID="test-merchant",
                  PAYFAST_SECURED_KEY="test-key", PAYFAST_MERCHANT_NAME="WearHowZ",
                  PAYFAST_API_BASE_URL="")
    with pytest.raises(ValidationError, match="PAYFAST_API_BASE_URL"):
        Settings.model_validate(values)
    values["PAYFAST_API_BASE_URL"] = "https://provider.example.test"
    assert Settings.model_validate(values).PAYFAST_ENABLED

"""Startup configuration, request contracts and service withdrawal guards agree."""

import os
import subprocess
import sys
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.exceptions import BusinessRuleError
from app.schemas.wallet import WithdrawalRequest
from app.services.wallet_service import WalletService

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "minimum,maximum",
    [(0, 1000), (-1, 1000), (1000, 999), (500, 0), (500, -1), (500, 10_000_000_000)],
)
def test_invalid_withdrawal_configuration_fails_startup(minimum, maximum):
    values = settings.model_dump()
    values.update(MIN_WITHDRAWAL_AMOUNT=minimum, MAX_WITHDRAWAL_AMOUNT=maximum)
    with pytest.raises(ValidationError, match="withdrawal"):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize("minimum,maximum", [(500, 200000), (750, 1000), (100, 250000), (750, 750)])
def test_fresh_process_schema_and_openapi_follow_startup_limits(minimum, maximum):
    # Conftest supplies synthetic settings and ENVIRONMENT=test (no .env reads).
    env = {
        **os.environ,
        "MIN_WITHDRAWAL_AMOUNT": str(minimum),
        "MAX_WITHDRAWAL_AMOUNT": str(maximum),
    }
    code = """
from decimal import Decimal
from uuid import uuid4
from pydantic import ValidationError
from app.core.config import settings
from app.schemas.wallet import WithdrawalRequest
from main import create_application
lo, hi = Decimal(settings.MIN_WITHDRAWAL_AMOUNT), Decimal(settings.MAX_WITHDRAWAL_AMOUNT)
for amount in (lo, hi):
    assert WithdrawalRequest(amount=amount, bank_account_id=uuid4()).amount == amount
for amount in (lo - Decimal('.01'), hi + Decimal('.01')):
    try:
        WithdrawalRequest(amount=amount, bank_account_id=uuid4())
    except ValidationError:
        pass
    else:
        raise AssertionError('out-of-policy amount accepted')
schema = create_application().openapi()['components']['schemas']['WithdrawalRequest']
numeric = next(item for item in schema['properties']['amount']['anyOf'] if item['type'] == 'number')
assert numeric['minimum'] == lo
assert numeric['maximum'] == hi
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-Infinity", "750.001", "0", "-1"])
def test_invalid_withdrawal_amounts_remain_rejected(amount):
    with pytest.raises(ValidationError):
        WithdrawalRequest(amount=amount, bank_account_id=uuid4())


@pytest.mark.parametrize("amount,word", [("749.99", "Minimum"), ("1000.01", "Maximum")])
async def test_service_rechecks_configured_limits_before_mutation(monkeypatch, amount, word):
    monkeypatch.setattr(settings, "MIN_WITHDRAWAL_AMOUNT", 750)
    monkeypatch.setattr(settings, "MAX_WITHDRAWAL_AMOUNT", 1000)
    db = AsyncMock()
    db.execute.side_effect = AssertionError("Out-of-policy withdrawal reached bank lookup")
    service = WalletService(db)
    service.wallet_repo = AsyncMock()
    service.wallet_repo.get_by_seller_id.return_value = SimpleNamespace(
        available_balance=Decimal("10000")
    )
    service.payout_repo = AsyncMock()
    service.tx_repo = AsyncMock()
    # Direct callers cannot bypass the service guard with an already-built payload.
    payload = WithdrawalRequest.model_construct(amount=Decimal(amount), bank_account_id=uuid4())
    with pytest.raises(BusinessRuleError, match=word):
        await service.request_withdrawal(uuid4(), payload)
    service.wallet_repo.debit_available.assert_not_awaited()
    service.payout_repo.create.assert_not_awaited()
    service.tx_repo.create.assert_not_awaited()
    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()

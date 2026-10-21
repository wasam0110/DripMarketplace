"""Checkout quote signatures, request identity and HTTP boundary validation."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from app.core.exceptions import ConflictError
from app.core.security import _load_private_key
from app.schemas.order import CheckoutOrderRequest, CheckoutRecoveryRequest
from app.services.checkout_safety import CheckoutGuard, digest, key_hash, sign_quote, verify_quote

pytestmark = pytest.mark.unit


def test_quote_signature_scope_and_tampering():
    owner = uuid4()
    fingerprint = digest({"price": "12.01"})
    token, expiry = sign_quote(fingerprint, owner)
    assert expiry > datetime.now(UTC)
    assert verify_quote(token, owner) == fingerprint
    for wrong_owner in (None, uuid4()):
        with pytest.raises(ConflictError, match="invalid or expired"):
            verify_quote(token, wrong_owner)
    with pytest.raises(ConflictError):
        verify_quote(token[:-12] + "invalid", owner)


def test_expired_quote_requires_new_acceptance():
    token = jwt.encode(
        {
            "sub": "guest",
            "aud": "wearhowz-checkout-quote",
            "iss": "wearhowz-api",
            "iat": datetime.now(UTC) - timedelta(hours=1),
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "price": "a" * 64,
        },
        _load_private_key(),
        algorithm="RS256",
    )
    with pytest.raises(ConflictError) as error:
        verify_quote(token, None)
    assert error.value.code == "CHECKOUT_QUOTE_INVALID"


def test_scope_separates_guest_and_accounts_and_hashes_secret():
    key = uuid4()
    assert len({key_hash(key, None), key_hash(key, uuid4()), key_hash(key, uuid4())}) == 3
    assert str(key) not in key_hash(key, None)
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})


def test_changed_price_requires_reacceptance():
    guard = CheckoutGuard("key", "request", "accepted")
    guard.accept("accepted")
    with pytest.raises(ConflictError) as error:
        guard.accept("changed")
    assert error.value.code == "CHECKOUT_QUOTE_CHANGED"


@pytest.mark.parametrize("key", ["guessable", "00000000-0000-0000-0000-000000000000"])
def test_recovery_requires_random_uuid4(key):
    with pytest.raises(ValidationError):
        CheckoutRecoveryRequest(checkout_key=key)


def test_http_order_requires_both_safeguards():
    with pytest.raises(ValidationError) as error:
        CheckoutOrderRequest(
            shipping_address={
                "recipient_name": "Test Person",
                "phone": "03001234567",
                "street": "12 Test Street",
                "city": "Karachi",
                "province": "Sindh",
            },
            payment_method="cod",
        )
    assert {tuple(item["loc"]) for item in error.value.errors()} == {
        ("checkout_key",),
        ("quote_token",),
    }

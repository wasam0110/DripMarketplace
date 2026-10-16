"""PyJWT preserves legacy claims while enforcing signatures and required fields."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.config import settings
from app.core.exceptions import TokenExpiredError, TokenInvalidError
from app.core.security import create_access_token, decode_access_token
from app.services.order_access import create_guest_token, guest_token_matches


def claims():
    now = datetime.now(UTC)
    return {"sub": str(uuid4()), "jti": str(uuid4()), "iat": now,
            "exp": now + timedelta(minutes=15), "aud": "drip-client", "iss": "drip-api"}


@pytest.mark.parametrize("missing", ["exp", "sub", "jti", "iat"])
def test_missing_claims_rejected(missing):
    payload = claims()
    del payload[missing]
    token = jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm="RS256")
    with pytest.raises(TokenInvalidError):
        decode_access_token(token)


def test_legacy_rs256_identity_and_expiry():
    token, token_id = create_access_token(subject=str(uuid4()), role="customer")
    decoded = decode_access_token(token)
    assert decoded["jti"] == token_id
    assert (decoded["iss"], decoded["aud"]) == ("drip-api", "drip-client")
    payload = claims()
    payload["exp"] = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(TokenExpiredError):
        decode_access_token(jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm="RS256"))
    with pytest.raises(TokenInvalidError):
        decode_access_token(jwt.encode(claims(), key="", algorithm="none"))


def test_guest_scope_still_required():
    order_id = uuid4()
    token = create_guest_token(order_id)
    assert guest_token_matches(token, order_id)
    assert not guest_token_matches(token, uuid4())
    account_token, _ = create_access_token(subject=str(order_id), role="customer")
    assert not guest_token_matches(account_token, order_id)

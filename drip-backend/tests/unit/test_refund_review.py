"""Input and reviewed-link semantics for manual refunds; no provider or database."""

import pytest
from pydantic import ValidationError

from app.schemas.payment import RefundConfirmationRequest, RefundRequest


@pytest.mark.parametrize("reason", ["", "     ", "tiny", "abc\x00def", "x" * 501])
def test_invalid_reason(reason):
    with pytest.raises(ValidationError):
        RefundRequest(amount="100.25", reason=reason)


@pytest.mark.parametrize("reference", ["", "  ", "ab", "ab\nc", "ab\x7fc", "x" * 256])
def test_invalid_transfer_reference(reference):
    with pytest.raises(ValidationError):
        RefundConfirmationRequest(reference=reference)


def test_explicit_null_return_link_is_distinct_from_legacy_omission():
    legacy = RefundConfirmationRequest(reference="  BANK-001  ")
    reviewed = RefundConfirmationRequest(reference="BANK-001", expected_return_id=None)
    assert legacy.reference == "BANK-001"
    assert "expected_return_id" not in legacy.model_fields_set
    assert "expected_return_id" in reviewed.model_fields_set


def test_exact_amount_remaining_and_normalized_reason():
    value = RefundRequest(
        amount="100.25",
        reason="  Returned product  ",
        idempotency_key="request-0001",
        expected_remaining_amount="100.25",
    )
    assert value.reason == "Returned product"
    assert str(value.expected_remaining_amount) == "100.25"


def test_existing_multiline_return_notes_remain_supported():
    value = RefundRequest(amount="100", reason="Received return\nApproved after inspection")
    assert "\n" in value.reason


@pytest.mark.parametrize(
    "fields",
    [
        {"amount": "1.001"},
        {"expected_remaining_amount": "-1"},
        {"idempotency_key": "        "},
        {"idempotency_key": "key-\n0001"},
    ],
)
def test_invalid_request_review_fields(fields):
    with pytest.raises(ValidationError):
        RefundRequest(**{"amount": "1", "reason": "Valid reason", **fields})

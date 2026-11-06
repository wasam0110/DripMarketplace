"""Registration receipt fields and exact manual-transfer input validation."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.admin import AdminSellerDetailResponse, SellerRegistrationPaymentRequest


def test_registration_reference_is_normalized():
    payload = SellerRegistrationPaymentRequest(amount="5000.25", reference="  BANK-123  ")
    assert payload.amount == Decimal("5000.25")
    assert payload.reference == "BANK-123"


@pytest.mark.parametrize("reference", ["   ", "ab", "bank\nreference", "bank\x00ref", "x" * 256])
def test_registration_reference_rejects_unusable_values(reference):
    with pytest.raises(ValidationError):
        SellerRegistrationPaymentRequest(amount="5000.25", reference=reference)


@pytest.mark.parametrize("amount", ["0", "-1", "5000.251", "NaN", "Infinity"])
def test_registration_amount_rejects_invalid_values(amount):
    with pytest.raises(ValidationError):
        SellerRegistrationPaymentRequest(amount=amount, reference="BANK-123")


def test_admin_detail_requires_receipt_metadata_fields():
    fields = AdminSellerDetailResponse.model_fields
    for name in (
        "registration_amount_due",
        "registration_paid_at",
        "registration_payment_reference",
        "registration_paid_by",
    ):
        assert fields[name].is_required()

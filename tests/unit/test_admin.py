"""Unit tests — Block 8: Admin. No DB required."""
import pytest
from pydantic import ValidationError

from app.schemas.admin import (
    RejectSellerRequest, SuspendSellerRequest,
    UpdateSettingsRequest, CODVerifyRequest,
)


class TestSellerActionSchemas:
    def test_reject_valid(self):
        req = RejectSellerRequest(reason="Brand name is already trademarked")
        assert len(req.reason) >= 10

    def test_reject_too_short(self):
        with pytest.raises(ValidationError):
            RejectSellerRequest(reason="bad")

    def test_suspend_valid(self):
        req = SuspendSellerRequest(reason="Repeated policy violations reported")
        assert req.reason is not None


class TestUpdateSettingsSchema:
    def test_valid_commission(self):
        req = UpdateSettingsRequest(commission_rate=0.20)
        assert req.commission_rate == 0.20

    def test_commission_above_one_rejected(self):
        with pytest.raises(ValidationError):
            UpdateSettingsRequest(commission_rate=1.5)

    def test_commission_negative_rejected(self):
        with pytest.raises(ValidationError):
            UpdateSettingsRequest(commission_rate=-0.1)

    def test_cod_timeout_below_min(self):
        with pytest.raises(ValidationError):
            UpdateSettingsRequest(cod_timeout_minutes=2)

    def test_cod_timeout_above_max(self):
        with pytest.raises(ValidationError):
            UpdateSettingsRequest(cod_timeout_minutes=9999)

    def test_valid_registration_fee(self):
        req = UpdateSettingsRequest(registration_fee=7500)
        assert req.registration_fee == 7500

    def test_all_none_valid(self):
        req = UpdateSettingsRequest()
        assert req.commission_rate is None


class TestCODVerifySchema:
    def test_no_note_ok(self):
        req = CODVerifyRequest()
        assert req.note is None

    def test_with_note(self):
        req = CODVerifyRequest(note="Customer confirmed address")
        assert req.note == "Customer confirmed address"
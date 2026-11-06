"""Unit tests — Block 8: Admin. No DB required."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.core.exceptions import NotFoundError
from app.schemas.admin import (
    CODVerifyRequest,
    RejectSellerRequest,
    SuspendSellerRequest,
    UpdateSettingsRequest,
)
from app.services.admin_service import AdminService


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


@pytest.mark.asyncio
async def test_seller_decision_loader_locks_and_refreshes_current_state():
    seller = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = seller
    db = MagicMock(execute=AsyncMock(return_value=result))
    seller_id = uuid4()

    assert await AdminService(db)._get_seller(seller_id) is seller
    statement = db.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql
    assert "sellers.deleted_at IS NULL" in sql
    assert seller_id in statement.compile().params.values()
    assert statement.get_execution_options()["populate_existing"] is True
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_seller_decision_loader_rejects_missing_or_deleted_seller():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = MagicMock(execute=AsyncMock(return_value=result))
    with pytest.raises(NotFoundError):
        await AdminService(db)._get_seller(uuid4())
    db.commit.assert_not_called()

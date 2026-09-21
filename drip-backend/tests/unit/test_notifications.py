"""Unit tests — Block 9: Notifications. No DB required."""
import pytest
from pydantic import ValidationError

from app.schemas.notification import (
    UpdatePreferencesRequest,
    BroadcastRequest,
)


class TestUpdatePreferencesSchema:
    def test_all_none_valid(self):
        req = UpdatePreferencesRequest()
        assert req.order_updates_email is None

    def test_set_false(self):
        req = UpdatePreferencesRequest(order_updates_email=False)
        assert req.order_updates_email is False

    def test_partial_update(self):
        req = UpdatePreferencesRequest(
            promotions_email=False, low_stock_alerts=True
        )
        assert req.promotions_email is False
        assert req.low_stock_alerts is True
        assert req.payout_notifications is None


class TestBroadcastSchema:
    def test_valid_all(self):
        req = BroadcastRequest(
            title="New collection drop",
            body="Check out our latest streetwear arrivals",
            audience="all",
        )
        assert req.audience == "all"

    def test_valid_sellers(self):
        req = BroadcastRequest(title="Fee update", body="Commission rate updated", audience="sellers")
        assert req.audience == "sellers"

    def test_invalid_audience(self):
        with pytest.raises(ValidationError):
            BroadcastRequest(title="Test", body="Test body", audience="admins")

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            BroadcastRequest(title="", body="Test body", audience="all")

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            BroadcastRequest(title="A" * 201, body="Test body", audience="all")

    def test_body_too_long(self):
        with pytest.raises(ValidationError):
            BroadcastRequest(title="Test", body="A" * 1001, audience="all")

    def test_with_action_url(self):
        req = BroadcastRequest(
            title="Sale starts now",
            body="50% off selected items",
            audience="customers",
            action_url="/sale",
        )
        assert req.action_url == "/sale"
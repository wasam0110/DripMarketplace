"""Unit tests — Block 10: Returns & Disputes. No DB required."""
import pytest
from pydantic import ValidationError

from app.schemas.return_ import (
    CreateReturnRequest, ReturnItemRequest,
    OpenDisputeRequest, AddDisputeMessageRequest,
    ResolveDisputeRequest, AdminReturnActionRequest,
)


VALID_ITEM = {"order_item_id": "00000000-0000-0000-0000-000000000001", "quantity": 1}

VALID_RETURN = {
    "seller_order_id": "00000000-0000-0000-0000-000000000002",
    "reason":          "Item arrived damaged and not as described",
    "items":           [VALID_ITEM],
}


class TestCreateReturnSchema:
    def test_valid(self):
        req = CreateReturnRequest(**VALID_RETURN)
        assert len(req.items) == 1

    def test_reason_too_short(self):
        with pytest.raises(ValidationError):
            CreateReturnRequest(**{**VALID_RETURN, "reason": "bad"})

    def test_empty_items_rejected(self):
        with pytest.raises(ValidationError):
            CreateReturnRequest(**{**VALID_RETURN, "items": []})

    def test_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            CreateReturnRequest(**{
                **VALID_RETURN,
                "items": [{"order_item_id": VALID_ITEM["order_item_id"], "quantity": 0}],
            })

    def test_multiple_items(self):
        req = CreateReturnRequest(**{
            **VALID_RETURN,
            "items": [
                VALID_ITEM,
                {"order_item_id": "00000000-0000-0000-0000-000000000003", "quantity": 2},
            ],
        })
        assert len(req.items) == 2


class TestDisputeSchemas:
    def test_open_dispute_valid(self):
        req = OpenDisputeRequest(message="The seller refused to accept the return unfairly")
        assert len(req.message) >= 10

    def test_open_dispute_too_short(self):
        with pytest.raises(ValidationError):
            OpenDisputeRequest(message="bad")

    def test_add_message_valid(self):
        req = AddDisputeMessageRequest(body="Here is the photo evidence of damage")
        assert req.body is not None

    def test_add_message_empty(self):
        with pytest.raises(ValidationError):
            AddDisputeMessageRequest(body="")


class TestResolveDisputeSchema:
    def test_in_favor_customer(self):
        req = ResolveDisputeRequest(
            in_favor_of="customer",
            resolution_note="Customer provided clear evidence of damage"
        )
        assert req.in_favor_of == "customer"

    def test_in_favor_seller(self):
        req = ResolveDisputeRequest(
            in_favor_of="seller",
            resolution_note="No valid evidence provided by customer"
        )
        assert req.in_favor_of == "seller"

    def test_invalid_in_favor_of(self):
        with pytest.raises(ValidationError):
            ResolveDisputeRequest(in_favor_of="admin", resolution_note="Test resolution note here")

    def test_short_resolution_note(self):
        with pytest.raises(ValidationError):
            ResolveDisputeRequest(in_favor_of="customer", resolution_note="short")


class TestAdminReturnSchema:
    def test_no_note_ok(self):
        req = AdminReturnActionRequest()
        assert req.admin_note is None

    def test_with_note(self):
        req = AdminReturnActionRequest(admin_note="Approved after reviewing images")
        assert req.admin_note is not None
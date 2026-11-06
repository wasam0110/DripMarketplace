"""Admin review expectations against native PostgreSQL and real API permissions."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.integration.test_return_api import (
    MESSAGE,
    RESOLUTION,
    snapshot,
)
from tests.integration.test_return_api import (
    case as case,
)
from tests.integration.test_return_api import (
    payload as return_request,
)
from tests.integration.test_return_api import (
    requested as requested,
)

from app.core.exceptions import BusinessRuleError, ConflictError
from app.models.return_ import Dispute
from app.schemas.return_ import (
    AddDisputeMessageRequest,
    AdminReturnActionRequest,
    CreateReturnRequest,
    OpenDisputeRequest,
    ResolveDisputeRequest,
)
from app.services.return_service import ReturnService

pytestmark = pytest.mark.integration


async def test_reviewed_return_lifecycle(client, db, case, requested):
    path = f"/api/v1/admin/returns/{requested['id']}"
    headers = case["headers"]["admin"]
    financial = await snapshot(db, financial=True)
    for action, status, target in [
        ("approve", "requested", "approved"), ("received", "approved", "received"),
    ]:
        response = await client.post(path + f"/{action}", headers=headers, json={
            "expected_status": status, "expected_notes": "Outdated note",
        })
        assert response.status_code == 409, response.text
        response = await client.post(path + f"/{action}", headers=headers, json={
            "expected_status": status, "expected_notes": None,
        })
        assert response.status_code == 200, response.text
        detail = (await client.get(path, headers=headers)).json()
        assert detail["status"] == target
        assert detail["order"]["payment_currency"] == "PKR"
    assert await snapshot(db, financial=True) == financial
    response = await client.post(path + "/refund", headers=headers, json={
        "expected_status": "received", "expected_notes": None, "expected_refund_amount": "0.01",
    })
    assert response.status_code == 409, response.text
    assert await snapshot(db, financial=True) == financial
    response = await client.post(path + "/refund", headers=headers, json={
        "expected_status": "received", "expected_notes": None,
        "expected_refund_amount": detail["estimated_refund_amount"],
    })
    assert response.status_code == 200, response.text
    saved = (await client.get(path, headers=headers)).json()
    assert saved["status"] == "received"
    assert saved["refund"]["refund_id"] == response.json()["refund_id"]
    assert saved["refund"]["status"] == "pending"


async def open_case(client, case, requested):
    result = await client.post(
        f"/api/v1/admin/returns/{requested['id']}/reject",
        headers=case["headers"]["admin"], json={},
    )
    assert result.status_code == 200
    result = await client.post(
        f"/api/v1/returns/{requested['id']}/dispute",
        headers=case["headers"]["buyer"], json=MESSAGE,
    )
    assert result.status_code == 201, result.text
    return result.json()


@pytest.mark.parametrize("outcome", ["customer", "seller"])
async def test_dispute_review_rejects_unread_messages(client, db, case, requested, outcome):
    dispute = await open_case(client, case, requested)
    path = f"/api/v1/admin/disputes/{dispute['id']}"
    headers = case["headers"]["admin"]
    before = await snapshot(db)
    for suffix, payload in [
        ("messages", {"body": "Reviewed the evidence"}),
        ("resolve", {**RESOLUTION, "in_favor_of": outcome}),
    ]:
        result = await client.post(path + f"/{suffix}", headers=headers, json={
            **payload, "expected_status": "open", "expected_message_count": 0,
        })
        assert result.status_code == 409, result.text
        assert await snapshot(db) == before
    result = await client.post(path + "/messages", headers=headers, json={
        "body": "Reviewed the evidence", "expected_status": "open", "expected_message_count": 1,
    })
    assert result.status_code == 201, result.text
    result = await client.post(path + "/resolve", headers=headers, json={
        **RESOLUTION, "in_favor_of": outcome,
        "expected_status": "under_review", "expected_message_count": 2,
    })
    assert result.status_code == 200, result.text
    assert result.json()["status"] == f"resolved_{outcome}"
    returned = await client.get(
        f"/api/v1/admin/returns/{requested['id']}", headers=headers,
    )
    assert returned.json()["status"] == ("approved" if outcome == "customer" else "rejected")


async def test_preloaded_dispute_is_refreshed_after_other_session_resolves(test_engine):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    # Seed committed rows so both independent sessions see the same records.
    async with sessions() as setup:
        world = await case.__wrapped__(setup)
        service = ReturnService(setup)
        returned = await service.request_return(
            world["users"]["buyer"], CreateReturnRequest(**return_request(world)),
        )
        await service.reject_return(
            returned.id, world["users"]["admin"], AdminReturnActionRequest(),
        )
        dispute = await service.open_dispute(
            returned.id, world["users"]["buyer"], OpenDisputeRequest(**MESSAGE),
        )
    async with sessions() as stale, sessions() as winner:
        cached = await stale.get(Dispute, dispute.id)
        assert cached.status.value == "open"
        await ReturnService(winner).resolve_dispute(
            cached.id, world["users"]["admin"], ResolveDisputeRequest(**RESOLUTION),
        )
        with pytest.raises((BusinessRuleError, ConflictError)):
            await ReturnService(stale).add_admin_message(
                cached.id, world["users"]["admin"], AddDisputeMessageRequest(body="Too late"),
            )
        await stale.rollback()


@pytest.mark.parametrize("suffix,payload", [
    ("messages", {"body": "   "}),
    ("resolve", {"in_favor_of": "seller", "resolution_note": " " * 12}),
])
async def test_blank_admin_dispute_text_is_rejected(client, db, case, requested, suffix, payload):
    dispute = await open_case(client, case, requested)
    before = await snapshot(db)
    result = await client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/{suffix}",
        headers=case["headers"]["admin"], json=payload,
    )
    assert result.status_code == 422, result.text
    assert await snapshot(db) == before

"""COD policy/locking/receipt guards without external services."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.core.exceptions import BusinessRuleError, ConflictError
from app.models.order import OrderStatus, SellerOrderStatus
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.order_repo import OrderRepository
from app.schemas.admin import CODVerifyRequest
from app.services.admin_service import AdminService

pytestmark = pytest.mark.unit
NOW = datetime(2026, 11, 1, 12, tzinfo=UTC)


@pytest.fixture
def setup(monkeypatch):
    import app.repositories.inventory_repo as inventory_module
    import app.repositories.order_repo as repo_module
    import app.services.admin_service as service_module
    import app.services.platform_settings as policy_module

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(service_module, "datetime", Clock)
    policy = AsyncMock(return_value=SimpleNamespace(cod_timeout_minutes=30))
    monkeypatch.setattr(policy_module, "get_platform_settings", policy)
    item = SimpleNamespace(variant_id=uuid4(), quantity=2)
    split = SimpleNamespace(id=uuid4(), status=SellerOrderStatus.pending)
    order = SimpleNamespace(
        id=uuid4(),
        order_number="WHZ-COD-TEST",
        payment_method="cod",
        status=OrderStatus.pending_cod_verification,
        created_at=NOW - timedelta(minutes=5),
        updated_at=NOW - timedelta(minutes=5),
        items=[item],
        seller_orders=[split],
    )
    repo = MagicMock(get_by_id=AsyncMock(return_value=order), update_status=AsyncMock())

    async def update_status(order_id, status, **kwargs):
        order.status = status

    repo.update_status.side_effect = update_status
    inventory = MagicMock(release=AsyncMock())
    seller_repo = MagicMock(update_status=AsyncMock())
    monkeypatch.setattr(repo_module, "OrderRepository", lambda db: repo)
    monkeypatch.setattr(repo_module, "SellerOrderRepository", lambda db: seller_repo)
    monkeypatch.setattr(inventory_module, "InventoryRepository", lambda db: inventory)
    outbox = AsyncMock()
    monkeypatch.setattr(service_module, "queue_notification", outbox)
    db = MagicMock(commit=AsyncMock())
    return SimpleNamespace(
        service=AdminService(db),
        db=db,
        order=order,
        repo=repo,
        inventory=inventory,
        seller=seller_repo,
        outbox=outbox,
        policy=policy,
        admin=uuid4(),
    )


async def test_verify_is_approval_not_stock_release_or_collection(setup):
    s = setup
    receipt = await s.service.verify_cod(
        s.order.id,
        s.admin,
        note="Customer confirmed",
        expected_updated_at=s.order.updated_at,
        expected_expires_at=s.order.created_at + timedelta(minutes=30),
    )
    assert receipt["order_id"] == s.order.id and receipt["status"] == "processing"
    s.repo.get_by_id.assert_awaited_once_with(s.order.id, for_update=True)
    s.inventory.release.assert_not_awaited()
    s.seller.update_status.assert_not_awaited()
    s.db.commit.assert_awaited_once()
    assert s.outbox.await_args.args[1] == f"order:{s.order.id}:status:processing"


@pytest.mark.parametrize("age", [30, 31])
async def test_exact_and_past_deadlines_reject_approval(setup, age):
    s = setup
    s.order.created_at = NOW - timedelta(minutes=age)
    with pytest.raises(BusinessRuleError, match="deadline expired"):
        await s.service.verify_cod(s.order.id, s.admin)
    s.db.commit.assert_not_awaited()
    s.outbox.assert_not_awaited()


@pytest.mark.parametrize("kind", ["version", "policy", "method", "status", "split"])
async def test_changed_or_inconsistent_review_does_not_mutate(setup, kind):
    s = setup
    kwargs = {}
    if kind == "version":
        kwargs["expected_updated_at"] = NOW
    if kind == "policy":
        kwargs["expected_expires_at"] = NOW
    if kind == "method":
        s.order.payment_method = "payfast"
    if kind == "status":
        s.order.status = OrderStatus.processing
    if kind == "split":
        s.order.seller_orders[0].status = SellerOrderStatus.shipped
    with pytest.raises((BusinessRuleError, ConflictError)):
        await s.service.verify_cod(s.order.id, s.admin, **kwargs)
    s.db.commit.assert_not_awaited()
    s.outbox.assert_not_awaited()


async def test_cancel_expired_order_releases_strictly_and_keeps_honest_audit_note(setup):
    s = setup
    s.order.created_at = NOW - timedelta(hours=1)
    receipt = await s.service.cancel_cod(s.order.id, s.admin)
    assert receipt["status"] == "cancelled"
    item = s.order.items[0]
    s.inventory.release.assert_awaited_once_with(item.variant_id, item.quantity, strict=True)
    assert s.repo.update_status.await_args.kwargs["note"] == "COD order cancelled by admin"
    s.seller.update_status.assert_awaited_once_with(
        s.order.seller_orders[0].id, SellerOrderStatus.cancelled
    )
    s.db.commit.assert_awaited_once()


async def test_duplicate_decision_does_not_publish_twice(setup):
    s = setup
    await s.service.cancel_cod(s.order.id, s.admin, reason="Customer declined")
    with pytest.raises(BusinessRuleError):
        await s.service.cancel_cod(s.order.id, s.admin)
    assert s.outbox.await_count == s.inventory.release.await_count == 1


async def test_release_failure_never_commits_or_publishes(setup):
    s = setup
    s.inventory.release.side_effect = BusinessRuleError("Inconsistent reservation")
    with pytest.raises(BusinessRuleError):
        await s.service.cancel_cod(s.order.id, s.admin)
    s.outbox.assert_not_awaited()
    s.db.commit.assert_not_awaited()


async def test_outbox_failure_does_not_commit(setup):
    s = setup
    s.outbox.side_effect = RuntimeError("synthetic outbox failure")
    with pytest.raises(RuntimeError):
        await s.service.verify_cod(s.order.id, s.admin)
    s.db.commit.assert_not_awaited()


async def test_order_lock_reloads_stale_identity_map():
    result = MagicMock()
    result.scalar_one_or_none.return_value = object()
    db = MagicMock(execute=AsyncMock(return_value=result))
    await OrderRepository(db).get_by_id(uuid4(), for_update=True)
    statement = db.execute.await_args.args[0]
    assert "FOR UPDATE" in str(statement.compile(dialect=postgresql.dialect()))
    assert statement.get_execution_options()["populate_existing"] is True


@pytest.mark.parametrize(
    "strict,affected,raises", [(True, 1, False), (True, 0, True), (False, 0, False)]
)
async def test_inventory_strict_mode_is_opt_in(strict, affected, raises):
    db = MagicMock(execute=AsyncMock(return_value=SimpleNamespace(rowcount=affected)))
    if raises:
        with pytest.raises(BusinessRuleError):
            await InventoryRepository(db).release(uuid4(), 2, strict=strict)
    else:
        await InventoryRepository(db).release(uuid4(), 2, strict=strict)


@pytest.mark.parametrize("note,expected", [(None, None), (" ", None), (" Checked ", "Checked")])
def test_note_normalization(note, expected):
    assert CODVerifyRequest(note=note).note == expected
    assert CODVerifyRequest().expected_updated_at is None


@pytest.mark.parametrize(
    "payload",
    [
        {"note": "x" * 501},
        {"note": "Line\nbreak"},
        {"expected_updated_at": "2026-11-01T12:00:00"},
        {"expected_expires_at": "2026-11-01T12:00:00"},
    ],
)
def test_invalid_decision_fields(payload):
    with pytest.raises(ValidationError):
        CODVerifyRequest(**payload)

"""Native PostgreSQL transactions prove seller decisions serialize before validation."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.exceptions import BusinessRuleError
from app.models.notification import NotificationOutbox
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.services import admin_service
from app.services.admin_service import AdminService


async def _decide(service, action, seller_id, admin_id, reason):
    """Use the same rollback-on-error boundary as the request session dependency."""
    try:
        method = getattr(service, f"{action}_seller")
        if action in {"reject", "suspend"}:
            return await method(seller_id, admin_id, reason)
        return await method(seller_id, admin_id)
    except BaseException:
        await service.db.rollback()
        raise


async def _wait_for_block(observer, blocker_pid, waiter_pid, task):
    """Observe a real PostgreSQL lock wait instead of guessing from elapsed time."""
    while True:
        if await observer.scalar(
            text("SELECT :blocker = ANY(pg_blocking_pids(:waiter))"),
            {"blocker": blocker_pid, "waiter": waiter_pid},
        ):
            return
        assert not task.done(), "Competing decision did not wait for the seller lock"
        await asyncio.sleep(0.02)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "initial,first_action,second_action,rollback_first",
    [
        ("pending_approval", "approve", "reject", False),
        ("pending_approval", "reject", "approve", False),
        ("pending_approval", "approve", "approve", False),
        ("pending_approval", "reject", "reject", False),
        ("pending_payment", "reject", "reject", False),
        ("active", "suspend", "suspend", False),
        ("suspended", "reinstate", "reinstate", False),
        ("pending_approval", "approve", "reject", True),
    ],
    ids=[
        "approve-beats-reject",
        "reject-beats-approve",
        "duplicate-approval",
        "duplicate-rejection",
        "unpaid-duplicate-rejection",
        "duplicate-suspension",
        "duplicate-reinstatement",
        "rollback-unblocks-rejection",
    ],
)
async def test_competing_seller_decisions(
    test_engine,
    monkeypatch,
    initial,
    first_action,
    second_action,
    rollback_first,
):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    seller_id, owner_id, first_admin, second_admin = (uuid4() for _ in range(4))
    async with sessions() as seed:
        seed.add_all(
            [
                User(
                    id=owner_id,
                    email="seller@example.test",
                    password_hash="test-only",
                    role=UserRole.seller,
                    has_verified_email=True,
                ),
                User(
                    id=first_admin,
                    email="admin1@example.test",
                    password_hash="test-only",
                    role=UserRole.admin,
                    has_verified_email=True,
                ),
                User(
                    id=second_admin,
                    email="admin2@example.test",
                    password_hash="test-only",
                    role=UserRole.admin,
                    has_verified_email=True,
                ),
            ]
        )
        await seed.flush()
        seed.add(
            Seller(
                id=seller_id,
                user_id=owner_id,
                brand_name="Race Test Label",
                slug="race-test-label",
                status=SellerStatus(initial),
            )
        )
        await seed.commit()

    locked, release = asyncio.Event(), asyncio.Event()
    first_reason, second_reason = (
        "First admin policy review reason.",
        "Second admin policy review reason.",
    )
    tasks = []
    if rollback_first:
        original_queue = admin_service.queue_notification

        async def queue_then_fail(db, key, task_name, *args):
            await original_queue(db, key, task_name, *args)
            if key.endswith(":approved"):
                raise RuntimeError("Injected failure after transactional outbox insert")

        monkeypatch.setattr(admin_service, "queue_notification", queue_then_fail)

    async with sessions() as first, sessions() as second, test_engine.connect() as observer:
        first_service, second_service = AdminService(first), AdminService(second)
        first_pid = await first.scalar(text("SELECT pg_backend_pid()"))
        second_pid = await second.scalar(text("SELECT pg_backend_pid()"))
        # Hold a strong identity-map reference: a locked query must refresh this value.
        cached = await second.get(Seller, seller_id)
        assert cached.status == SellerStatus(initial)
        original_first, original_second = first_service._get_seller, second_service._get_seller
        seen_by_second = []

        async def pause_after_lock(target):
            row = await original_first(target)
            locked.set()
            await release.wait()
            return row

        async def observe_locked_state(target):
            row = await original_second(target)
            assert row is cached
            seen_by_second.append(row.status)
            return row

        monkeypatch.setattr(first_service, "_get_seller", pause_after_lock)
        monkeypatch.setattr(second_service, "_get_seller", observe_locked_state)
        try:
            tasks.append(
                asyncio.create_task(
                    _decide(first_service, first_action, seller_id, first_admin, first_reason)
                )
            )
            await asyncio.wait_for(locked.wait(), timeout=5)
            tasks.append(
                asyncio.create_task(
                    _decide(second_service, second_action, seller_id, second_admin, second_reason)
                )
            )
            await asyncio.wait_for(
                _wait_for_block(observer, first_pid, second_pid, tasks[1]), timeout=5
            )
            release.set()
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=10
            )
            if rollback_first:
                assert isinstance(results[0], RuntimeError)
                assert isinstance(results[1], dict)
                assert seen_by_second == [SellerStatus(initial)]
            else:
                assert isinstance(results[0], dict)
                assert isinstance(results[1], BusinessRuleError)
                expected = {
                    "approve": "active",
                    "reject": "rejected",
                    "suspend": "suspended",
                    "reinstate": "active",
                }[first_action]
                assert seen_by_second == [SellerStatus(expected)]
        finally:
            release.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    winner = second_action if rollback_first else first_action
    winner_admin = second_admin if rollback_first else first_admin
    winner_reason = second_reason if rollback_first else first_reason
    async with sessions() as verify:
        saved = await verify.get(Seller, seller_id)
        assert (
            saved.status.value
            == {
                "approve": "active",
                "reject": "rejected",
                "suspend": "suspended",
                "reinstate": "active",
            }[winner]
        )
        assert saved.approved_by == (winner_admin if winner != "suspend" else None)
        assert saved.rejected_reason == (winner_reason if winner in {"reject", "suspend"} else None)
        assert (saved.approved_at is not None) == (winner in {"approve", "reinstate"})
        events = (await verify.scalars(select(NotificationOutbox))).all()
        if winner in {"approve", "reject"}:
            assert len(events) == 1
            approved = winner == "approve"
            event_key = f"seller:{seller_id}:decision:{'approved' if approved else 'rejected'}"
            assert events[0].event_key == event_key
            assert events[0].task_name == "notify_seller_decision"
            assert events[0].args == [
                str(seller_id),
                approved,
                None if approved else winner_reason,
                event_key,
            ]
        else:
            assert events == []

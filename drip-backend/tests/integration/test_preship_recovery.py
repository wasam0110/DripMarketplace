"""Durable completion, lost-queue recovery, bounded failure and concurrent replay."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_marketplace_regressions import market as marketplace_fixture
from test_release_native import db as committed_db

from app.core import database
from app.models.notification import Notification, NotificationOutbox
from app.services.notification_outbox import queue_notification
from app.tasks import notification_tasks as tasks

pytestmark = pytest.mark.integration
db = committed_db
market = marketplace_fixture


async def event(db, market, monkeypatch, test_engine):
    monkeypatch.setattr(
        database, "AsyncSessionLocal", async_sessionmaker(test_engine, expire_on_commit=False)
    )
    await queue_notification(
        db,
        "test:broadcast",
        "broadcast_notification",
        [str(market.buyer.id)],
        "Test",
        "Body",
        None,
        "broadcast-1",
    )
    await db.commit()
    return await db.scalar(
        select(NotificationOutbox).where(NotificationOutbox.event_key == "test:broadcast")
    )


async def test_lost_job_republished_then_concurrent_generations_complete_once(
    db,
    market,
    monkeypatch,
    test_engine,
):
    row = await event(db, market, monkeypatch, test_engine)
    queue = AsyncMock()
    await tasks.dispatch_notification_outbox({"redis": queue})
    first_id = queue.enqueue_job.await_args.kwargs["_job_id"]
    await db.refresh(row)
    row.published_at = datetime.now(UTC) - timedelta(hours=1)
    await db.commit()  # Simulate a published job lost from Redis.
    await tasks.dispatch_notification_outbox({"redis": queue})
    assert queue.enqueue_job.await_args.kwargs["_job_id"] != first_id
    await asyncio.wait_for(
        asyncio.gather(
            tasks.deliver_notification_outbox({}, str(row.id)),
            tasks.deliver_notification_outbox({}, str(row.id)),
        ),
        timeout=20,
    )
    await db.refresh(row)
    assert row.completed_at and row.delivery_attempts == 1
    assert await db.scalar(select(func.count(Notification.id))) == 1
    await tasks.dispatch_notification_outbox({"redis": queue})
    assert queue.enqueue_job.await_count == 2


async def test_delivery_failures_are_durable_and_bounded(db, market, monkeypatch, test_engine):
    row = await event(db, market, monkeypatch, test_engine)
    sender = AsyncMock(side_effect=RuntimeError("private provider detail"))
    monkeypatch.setattr(tasks, "broadcast_notification", sender)
    for _ in range(tasks.MAX_DELIVERIES + 2):
        await tasks.deliver_notification_outbox({}, str(row.id))
    await db.refresh(row)
    assert row.dead_lettered_at and not row.completed_at
    assert row.delivery_attempts == tasks.MAX_DELIVERIES
    assert row.last_error == "RuntimeError"
    assert sender.await_count == tasks.MAX_DELIVERIES
    queue = AsyncMock()
    await tasks.dispatch_notification_outbox({"redis": queue})
    queue.enqueue_job.assert_not_awaited()


async def test_publication_budget_retains_unfinished_event(db, market, monkeypatch, test_engine):
    row = await event(db, market, monkeypatch, test_engine)
    row.attempts = tasks.MAX_PUBLICATIONS
    await db.commit()
    queue = AsyncMock()
    await tasks.dispatch_notification_outbox({"redis": queue})
    await db.refresh(row)
    assert row.dead_lettered_at and row.last_error == "publication_budget_exhausted"
    queue.enqueue_job.assert_not_awaited()


async def test_replay_after_delivery_before_completion_does_not_duplicate(
    db,
    market,
    monkeypatch,
    test_engine,
):
    row = await event(db, market, monkeypatch, test_engine)
    # Delivery committed, but process died before recording the outbox acknowledgement.
    await tasks.broadcast_notification({}, *row.args)
    await tasks.deliver_notification_outbox({}, str(row.id))
    await db.refresh(row)
    assert row.completed_at
    assert await db.scalar(select(func.count(Notification.id))) == 1


async def test_unknown_task_is_dead_lettered_without_dynamic_dispatch(
    db,
    market,
    monkeypatch,
    test_engine,
):
    row = await event(db, market, monkeypatch, test_engine)
    row.task_name = "cleanup_soft_deleted_users"
    await db.commit()
    await tasks.deliver_notification_outbox({}, str(row.id))
    await db.refresh(row)
    assert row.dead_lettered_at and row.delivery_attempts == 1


async def test_admin_replay_records_actor_reason_and_prior_attempts(
    db,
    market,
    monkeypatch,
    test_engine,
    client,
):
    from app.core.security import create_access_token

    row = await event(db, market, monkeypatch, test_engine)
    row.dead_lettered_at = datetime.now(UTC)
    row.delivery_attempts = tasks.MAX_DELIVERIES
    await db.commit()
    path = f"/api/v1/admin/notifications/failed/{row.id}/replay"
    body = {"reason": "Provider configuration repaired"}
    buyer_token, _ = create_access_token(subject=str(market.buyer.id), role="customer")
    denied = await client.post(path, json=body, headers={"Authorization": f"Bearer {buyer_token}"})
    assert denied.status_code == 403
    admin_token, _ = create_access_token(subject=str(market.admin.id), role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}
    listing = await client.get("/api/v1/admin/notifications/failed", headers=headers)
    assert listing.status_code == 200 and len(listing.json()["data"]) == 1
    assert "args" not in listing.json()["data"][0]
    response = await client.post(path, json=body, headers=headers)
    assert response.status_code == 200
    await db.refresh(row)
    assert row.replay_history[0]["admin_id"] == str(market.admin.id)
    assert row.replay_history[0]["delivery_attempts"] == tasks.MAX_DELIVERIES
    assert row.replay_history[0]["reason"] == body["reason"]
    assert row.dead_lettered_at is None and row.delivery_attempts == 0
    repeated = await client.post(path, json=body, headers=headers)
    assert 400 <= repeated.status_code < 500
    event_id = str(row.id)
    await db.rollback()  # Release the rejected request's row lock before another worker.
    queue = AsyncMock()
    await tasks.dispatch_notification_outbox({"redis": queue})
    assert queue.enqueue_job.await_args.kwargs["_job_id"] == f"notification:{event_id}:1:1"
    await tasks.deliver_notification_outbox({}, event_id)
    await db.refresh(row)
    assert row.completed_at and len(row.replay_history) == 1


async def test_real_arq_recovers_deleted_job_and_persists_completion(
    db,
    market,
    monkeypatch,
    test_engine,
):
    import os
    from types import SimpleNamespace
    from urllib.parse import urlparse
    from uuid import uuid4

    from arq.connections import RedisSettings, create_pool
    from arq.worker import Worker

    url = os.environ.get("TEST_REDIS_URL")
    if not url:
        pytest.skip("Set TEST_REDIS_URL to a dedicated database /15")
    if urlparse(url).path != "/15":
        raise RuntimeError("Refusing a non-test Redis database")
    row = await event(db, market, monkeypatch, test_engine)
    queue = "preship-recovery:" + uuid4().hex
    pool = await create_pool(RedisSettings.from_dsn(url))
    job_ids = []

    async def enqueue(*args, **kwargs):
        job_ids.append(kwargs["_job_id"])
        return await pool.enqueue_job(*args, **kwargs, _queue_name=queue)

    try:
        await tasks.dispatch_notification_outbox({"redis": SimpleNamespace(enqueue_job=enqueue)})
        await pool.delete("arq:job:" + job_ids[0])
        await pool.zrem(queue, job_ids[0])
        await db.refresh(row)
        row.published_at = datetime.now(UTC) - timedelta(hours=1)
        await db.commit()
        await tasks.dispatch_notification_outbox({"redis": SimpleNamespace(enqueue_job=enqueue)})
        worker = Worker(
            [tasks.deliver_notification_outbox],
            redis_pool=pool,
            queue_name=queue,
            health_check_key=queue + ":health",
            burst=True,
            poll_delay=0.01,
            max_jobs=1,
            max_burst_jobs=1,
            handle_signals=False,
        )
        await asyncio.wait_for(worker.async_run(), timeout=20)
        await asyncio.gather(*worker.tasks.values(), return_exceptions=True)
        await db.refresh(row)
        assert row.completed_at and row.delivery_attempts == 1
        assert len(job_ids) == 2 and job_ids[0] != job_ids[1]
    finally:
        await pool.delete(
            queue,
            queue + ":health",
            *[
                f"arq:{kind}:{job_id}"
                for job_id in job_ids
                for kind in ("job", "result", "retry", "in-progress")
            ],
        )
        await pool.aclose()

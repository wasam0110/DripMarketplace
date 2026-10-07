"""Worker contracts: resource lifecycle, delivery failures and maintenance."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from arq import Retry

from app.core import database
from app.tasks import cleanup_tasks, email_tasks, worker


@pytest.fixture
def worker_db(monkeypatch):
    session = AsyncMock()
    session.__aenter__.return_value = session
    result = MagicMock(rowcount=2)
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    monkeypatch.setattr(database, "_session_factory", MagicMock(return_value=session))
    return session


EMAIL_CASES = [
    ("verification_email", "send_verification_email", ("a@example.com", "Ali", "token")),
    ("password_reset_email", "send_password_reset_email", ("a@example.com", "Ali", "token")),
    (
        "order_confirmation",
        "send_order_confirmation_email",
        ("a@example.com", "Ali", "WH1", 100, []),
    ),
    (
        "shipping_notification",
        "send_shipping_notification_email",
        ("a@example.com", "Ali", "WH1", "T1", "TCS", "Brand"),
    ),
    ("cod_timeout", "send_cod_timeout_email", ("a@example.com", "Ali", "WH1")),
    (
        "seller_approved",
        "send_seller_approved_email",
        ("a@example.com", "Brand", "https://example.test"),
    ),
]


@pytest.mark.parametrize("task,provider,args", EMAIL_CASES)
@pytest.mark.parametrize("success", [True, False])
async def test_email_delivery_retries_failures(monkeypatch, task, provider, args, success):
    sender = AsyncMock(return_value=success)
    monkeypatch.setattr(email_tasks, provider, sender)
    run = getattr(email_tasks, "task_send_" + task)
    if success:
        await run({"job_try": 2}, *args)
    else:
        with pytest.raises(Retry) as exc:
            await run({"job_try": 2}, *args)
        assert exc.value.defer_score == 60_000
    sender.assert_awaited_once_with(*args)


def test_worker_session_requires_startup(monkeypatch):
    monkeypatch.setattr(database, "_session_factory", None)
    with pytest.raises(RuntimeError, match="not initialised"):
        database.AsyncSessionLocal()


async def test_worker_session_uses_live_factory_and_shutdown_clears_it(worker_db, monkeypatch):
    engine = AsyncMock()
    monkeypatch.setattr(database, "_engine", engine)
    assert database.AsyncSessionLocal() is worker_db
    await database.close_db()
    engine.dispose.assert_awaited_once()
    with pytest.raises(RuntimeError):
        database.AsyncSessionLocal()


async def test_worker_startup_shutdown(monkeypatch):
    from app.core import redis

    callbacks = []
    for module, name in [
        (database, "init_db"),
        (redis, "init_redis"),
        (database, "close_db"),
        (redis, "close_redis"),
    ]:
        callback = AsyncMock()
        monkeypatch.setattr(module, name, callback)
        callbacks.append(callback)
    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    await worker.startup({})
    await worker.shutdown({})
    for callback in callbacks:
        callback.assert_awaited_once()


async def test_cart_cleanup_preserves_live_ttl(isolated_redis):
    await isolated_redis.set("cart:no-ttl", "item")
    await isolated_redis.set("cart:live", "item", ex=300)
    await isolated_redis.set("unrelated", "keep")
    await cleanup_tasks.cleanup_abandoned_carts({})
    assert 2_591_990 <= await isolated_redis.ttl("cart:no-ttl") <= 2_592_000
    assert 290 <= await isolated_redis.ttl("cart:live") <= 300
    assert await isolated_redis.ttl("unrelated") == -1


async def test_reset_cleanup_prunes_only_missing_tokens(isolated_redis):
    await isolated_redis.sadd("reset_tokens:all", "reset:live", "reset:gone")
    await isolated_redis.set("reset:live", "value", ex=60)
    await cleanup_tasks.cleanup_expired_reset_tokens({})
    assert await isolated_redis.smembers("reset_tokens:all") == {"reset:live"}


@pytest.mark.parametrize(
    "task", ["cleanup_expired_sessions", "cleanup_soft_deleted_users", "archive_old_notifications"]
)
async def test_database_cleanup_commits(worker_db, task):
    await getattr(cleanup_tasks, task)({})
    worker_db.execute.assert_awaited_once()
    worker_db.commit.assert_awaited_once()


async def test_orphan_cleanup_retains_recent_and_referenced_files(worker_db, monkeypatch):
    from app.integrations.supabase_storage import SupabaseStorage

    now = datetime.now(UTC)
    files = [
        {"name": "recent.webp", "url": "recent", "updated_at": now.isoformat()},
        {"name": "used.webp", "url": "used", "updated_at": (now - timedelta(days=2)).isoformat()},
        {
            "name": "orphan.webp",
            "url": "orphan",
            "updated_at": (now - timedelta(days=2)).isoformat(),
        },
    ]
    monkeypatch.setattr(SupabaseStorage, "list_all_files", AsyncMock(return_value=files))
    delete = AsyncMock()
    monkeypatch.setattr(SupabaseStorage, "delete", delete)
    worker_db.execute.side_effect = [
        SimpleNamespace(scalar_one_or_none=lambda: "image-id"),
        SimpleNamespace(scalar_one_or_none=lambda: None),
    ]
    await cleanup_tasks.cleanup_orphaned_images({})
    delete.assert_awaited_once_with("products", "orphan.webp")

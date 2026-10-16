"""Exercise actual ARQ serialization, retries and result storage on Redis."""

import asyncio
import os
import time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from arq.connections import RedisSettings, create_pool
from arq.worker import Worker
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_release_native import db as committed_db

from app.core.security import create_email_verify_token
from app.models.user import User
from app.tasks import email_tasks

db = committed_db

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("recover", [True, False])
@pytest.mark.parametrize("retain_result", [True, False])
async def test_email_job_retries_and_records_final_result(
    monkeypatch, recover, retain_result, db, test_engine
):
    import app.core.database as database
    from app.tasks.worker import WorkerSettings

    user = User(email="test@example.com", first_name="Test", password_hash="test-only")
    db.add(user)
    await db.commit()
    monkeypatch.setattr(
        database, "AsyncSessionLocal", async_sessionmaker(test_engine, expire_on_commit=False)
    )
    url = os.environ.get("TEST_REDIS_URL")
    if not url:
        pytest.skip("Set TEST_REDIS_URL to a dedicated Redis test database ending in /15")
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in {"redis", "rediss"} or parsed.path != "/15":
        raise RuntimeError("TEST_REDIS_URL must use dedicated test database /15")
    pool = await create_pool(RedisSettings.from_dsn(url))
    unique = uuid4().hex
    queue = "task6:" + unique
    sender = AsyncMock(side_effect=[False, True] if recover else None, return_value=False)
    monkeypatch.setattr(email_tasks, "send_verification_email", sender)
    job = await pool.enqueue_job(
        "task_send_verification_email",
        "test@example.com",
        "Test",
        create_email_verify_token(str(user.id)),
        _queue_name=queue,
        _job_id=unique,
    )
    workers = []
    try:
        for _attempt in range(2 if recover else 4):
            worker = Worker(
                [email_tasks.task_send_verification_email],
                redis_pool=pool,
                queue_name=queue,
                health_check_key=queue + ":health",
                burst=True,
                poll_delay=0.01,
                max_jobs=1,
                max_tries=3,
                max_burst_jobs=1,
                handle_signals=False,
                # Retained mode proves ARQ's result contract with synthetic data;
                # deployed settings must erase results even on exhausted retries.
                keep_result=3600 if retain_result else WorkerSettings.keep_result,
                keep_result_forever=WorkerSettings.keep_result_forever,
            )
            workers.append(worker)
            await asyncio.wait_for(worker.async_run(), timeout=10)
            result = await job.result_info()
            if result is not None or worker.jobs_complete or worker.jobs_failed:
                break
            # The production task defers 30s/60s/90s. Advance only this test job.
            assert await pool.zscore(queue, unique) is not None
            await pool.zadd(queue, {unique: int(time.time() * 1000) - 1})
        result = await job.result_info()
        if retain_result:
            assert result is not None and result.success is recover
        else:
            assert result is None
            assert not await pool.exists("arq:job:" + unique, "arq:result:" + unique)
            assert await pool.zscore(queue, unique) is None
            assert workers[-1].jobs_complete == int(recover)
            assert workers[-1].jobs_failed == int(not recover)
        assert sender.await_count == (2 if recover else 3)
        if not recover and retain_result:
            assert "max 3 retries exceeded" in str(result.result)
    finally:
        await pool.delete(
            queue,
            queue + ":health",
            "arq:job:" + unique,
            "arq:result:" + unique,
            "arq:retry:" + unique,
            "arq:in-progress:" + unique,
        )
        # ARQ 0.26.1 close() references Unix-only SIGUSR1 with signals disabled.
        # These burst workers already finished; close the shared pool directly.
        for worker in workers:
            await asyncio.gather(*worker.tasks.values(), return_exceptions=True)
        await pool.aclose()

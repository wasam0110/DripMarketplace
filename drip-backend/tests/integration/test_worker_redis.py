"""Exercise actual ARQ serialization, retries and result storage on Redis."""

import asyncio
import os
import time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from arq.connections import RedisSettings, create_pool
from arq.worker import Worker

from app.tasks import email_tasks

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("recover", [True, False])
async def test_email_job_retries_and_records_final_result(monkeypatch, recover):
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
        "not-a-live-token",
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
            )
            workers.append(worker)
            await asyncio.wait_for(worker.async_run(), timeout=10)
            result = await job.result_info()
            if result is not None:
                break
            # The production task defers 30s/60s/90s. Advance only this test job.
            assert await pool.zscore(queue, unique) is not None
            await pool.zadd(queue, {unique: int(time.time() * 1000) - 1})
        result = await job.result_info()
        assert result is not None and result.success is recover
        assert sender.await_count == (2 if recover else 3)
        if not recover:
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

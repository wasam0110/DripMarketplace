"""Synthetic failure injection into the real send_email function body.

No application settings, database, Redis, SDK or network transport is loaded.
The fake transaction models rollback after a failed commit; this proves service
call sequencing, not actual provider delivery or PostgreSQL crash behavior.
"""

import ast
import asyncio
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "drip-backend"))


async def main():
    source = ROOT / "drip-backend/app/services/notification_service.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "NotificationService")
    method = next(node for node in owner.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "send_email")
    namespace = {"Optional": Optional, "ExternalServiceError": RuntimeError}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), namespace)
    sender = AsyncMock(side_effect=["synthetic-receipt-one", "synthetic-receipt-two"])
    module = ModuleType("app.integrations.resend_client")
    module.ResendClient = lambda: SimpleNamespace(send=sender)
    sys.modules[module.__name__] = module
    saved = None
    pending = None

    async def get_by_delivery_key(key):
        return saved

    async def create(**fields):
        nonlocal pending
        pending = SimpleNamespace(**fields)
        return pending

    fail_commit = True

    async def commit():
        nonlocal saved
        if fail_commit:
            raise RuntimeError("synthetic database commit failure after provider success")
        saved = pending

    service = SimpleNamespace(log_repo=SimpleNamespace(get_by_delivery_key=get_by_delivery_key, create=create),
                              db=SimpleNamespace(commit=commit))
    payload = {"to": "synthetic@example.test", "subject": "Synthetic audit", "html": "<p>Fixture</p>",
               "delivery_key": "synthetic-event:email"}
    try:
        await namespace["send_email"](service, **payload)
    except RuntimeError as error:
        assert "commit failure" in str(error)
    else:
        raise AssertionError("First transaction must fail")
    assert sender.await_count == 1 and saved is None
    pending = None  # Emulate rollback on session close.
    fail_commit = False
    await namespace["send_email"](service, **payload)
    await namespace["send_email"](service, **payload)
    assert sender.await_count == 2  # A committed sent log suppresses only later attempts.
    assert all("delivery_key" not in call.kwargs for call in sender.await_args_list)
    from sqlalchemy.dialects.postgresql.asyncpg import dialect
    from app.models.notification import EmailLog
    expression = (EmailLog.sent_at >= "2026-11-01").compile(dialect=dialect())
    assert "app.core.config" not in sys.modules
    print(json.dumps({"provider_stub_calls_after_success_commit_failure_retry": sender.await_count,
                      "committed_sent_log_suppresses_third_call": True,
                      "delivery_key_forwarded_to_provider_adapter": False,
                      "email_log_date_comparison_sql": str(expression),
                      "date_filter_bind_type": type(expression.binds["sent_at_1"].type).__name__,
                      "settings_imported": False,
                      "scope": "mocked function-body sequencing and SQL compilation, not real provider or DB verification"}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

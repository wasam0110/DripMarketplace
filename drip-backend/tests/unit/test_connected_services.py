"""
tests/unit/test_connected_services.py
───────────────────────────────────────
Unit tests for Task 4: connected external services.

Covers contracts for:
  - Google OAuth (google_oauth.py)
  - Supabase Storage (integrations/supabase_storage.py)
  - Resend email client (integrations/resend_client.py)
  - ARQ worker registration (tasks/worker.py)

All network calls are mocked — no credentials or live services required.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE OAUTH
# ══════════════════════════════════════════════════════════════════════════════

class TestGoogleOAuth:

    def test_require_configuration_raises_when_unconfigured(self):
        from app.services.google_oauth import require_configuration
        from app.core.exceptions import ExternalServiceError
        from app.core.config import settings

        original_id     = settings.GOOGLE_CLIENT_ID
        original_secret = settings.GOOGLE_CLIENT_SECRET
        try:
            settings.GOOGLE_CLIENT_ID     = ""
            settings.GOOGLE_CLIENT_SECRET = ""
            with pytest.raises(ExternalServiceError, match="not configured"):
                require_configuration()
        finally:
            settings.GOOGLE_CLIENT_ID     = original_id
            settings.GOOGLE_CLIENT_SECRET = original_secret

    def test_require_configuration_passes_when_set(self):
        from app.services.google_oauth import require_configuration
        from app.core.config import settings

        original_id     = settings.GOOGLE_CLIENT_ID
        original_secret = settings.GOOGLE_CLIENT_SECRET
        try:
            settings.GOOGLE_CLIENT_ID     = "test-client-id.apps.googleusercontent.com"
            settings.GOOGLE_CLIENT_SECRET = "test-secret"
            require_configuration()
        finally:
            settings.GOOGLE_CLIENT_ID     = original_id
            settings.GOOGLE_CLIENT_SECRET = original_secret

    @pytest.mark.asyncio
    async def test_start_google_login_authorization_url_contains_required_params(self):
        from app.services.google_oauth import start_google_login
        from app.core.config import settings

        original_id     = settings.GOOGLE_CLIENT_ID
        original_secret = settings.GOOGLE_CLIENT_SECRET
        try:
            settings.GOOGLE_CLIENT_ID     = "test-client.apps.googleusercontent.com"
            settings.GOOGLE_CLIENT_SECRET = "test-secret"

            fake_response = MagicMock()
            fake_response.set_cookie = MagicMock()
            fake_response.headers = {}

            mock_redis = AsyncMock()
            mock_redis.setex = AsyncMock()

            with patch("app.services.google_oauth.get_redis", return_value=mock_redis):
                result = await start_google_login(fake_response)

        finally:
            settings.GOOGLE_CLIENT_ID     = original_id
            settings.GOOGLE_CLIENT_SECRET = original_secret

        auth_url = result["authorization_url"]
        assert "accounts.google.com/o/oauth2/v2/auth" in auth_url
        assert "client_id=test-client.apps.googleusercontent.com" in auth_url
        assert "response_type=code" in auth_url
        assert "scope=" in auth_url
        assert "openid" in auth_url
        assert "email" in auth_url
        assert "state=" in auth_url
        assert "nonce=" in auth_url
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url

    @pytest.mark.asyncio
    async def test_start_google_login_sets_state_cookie(self):
        from app.services.google_oauth import start_google_login
        from app.core.config import settings

        original_id     = settings.GOOGLE_CLIENT_ID
        original_secret = settings.GOOGLE_CLIENT_SECRET
        try:
            settings.GOOGLE_CLIENT_ID     = "test-client.apps.googleusercontent.com"
            settings.GOOGLE_CLIENT_SECRET = "test-secret"

            fake_response = MagicMock()
            fake_response.set_cookie = MagicMock()
            fake_response.headers = {}

            mock_redis = AsyncMock()
            mock_redis.setex = AsyncMock()

            with patch("app.services.google_oauth.get_redis", return_value=mock_redis):
                await start_google_login(fake_response)

        finally:
            settings.GOOGLE_CLIENT_ID     = original_id
            settings.GOOGLE_CLIENT_SECRET = original_secret

        assert fake_response.set_cookie.called
        assert mock_redis.setex.called
        args = mock_redis.setex.call_args[0]
        assert args[0].startswith("google-state:")
        assert args[1] == 600

    @pytest.mark.asyncio
    async def test_start_google_login_state_and_nonce_are_unique_per_call(self):
        from app.services.google_oauth import start_google_login
        from app.core.config import settings

        original_id     = settings.GOOGLE_CLIENT_ID
        original_secret = settings.GOOGLE_CLIENT_SECRET
        try:
            settings.GOOGLE_CLIENT_ID     = "cid"
            settings.GOOGLE_CLIENT_SECRET = "cs"

            states = []
            mock_redis = AsyncMock()
            mock_redis.setex = AsyncMock(side_effect=lambda k, *a: states.append(k))

            for _ in range(2):
                fake_response = MagicMock()
                fake_response.set_cookie = MagicMock()
                fake_response.headers = {}
                with patch("app.services.google_oauth.get_redis", return_value=mock_redis):
                    await start_google_login(fake_response)
        finally:
            settings.GOOGLE_CLIENT_ID     = original_id
            settings.GOOGLE_CLIENT_SECRET = original_secret

        assert len(states) == 2
        assert states[0] != states[1], "State must be unique per request"


# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE STORAGE
# ══════════════════════════════════════════════════════════════════════════════

class TestSupabaseStorage:

    def _make_storage(self):
        from app.integrations.supabase_storage import SupabaseStorage
        from app.core.config import settings
        settings.SUPABASE_URL              = "https://test.supabase.co"
        settings.SUPABASE_SERVICE_ROLE_KEY = "test-service-key"
        return SupabaseStorage()

    def test_get_public_url_format(self):
        s = self._make_storage()
        url = s.get_public_url("products", "seller/image.jpg")
        assert url == "https://test.supabase.co/storage/v1/object/public/products/seller/image.jpg"

    def test_headers_include_auth_and_apikey(self):
        s = self._make_storage()
        h = s._headers()
        assert h["Authorization"] == "Bearer test-service-key"
        assert h["apikey"] == "test-service-key"

    def test_headers_include_content_type_when_provided(self):
        s = self._make_storage()
        h = s._headers(content_type="image/webp")
        assert h["Content-Type"] == "image/webp"

    @pytest.mark.asyncio
    async def test_upload_posts_to_correct_url_and_returns_public_url(self):
        s = self._make_storage()
        mock_response = MagicMock()
        mock_response.status_code = 201

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)
        mock_client.post       = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await s.upload("products", "a/b.jpg", b"data", "image/jpeg")

        posted_url = mock_client.post.call_args[0][0]
        assert posted_url == "https://test.supabase.co/storage/v1/object/products/a/b.jpg"
        assert result == "https://test.supabase.co/storage/v1/object/public/products/a/b.jpg"

    @pytest.mark.asyncio
    async def test_upload_raises_storage_error_on_bad_status(self):
        from app.core.exceptions import StorageError
        s = self._make_storage()
        mock_response = MagicMock()
        mock_response.status_code = 403

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)
        mock_client.post       = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(StorageError):
                await s.upload("products", "a/b.jpg", b"data", "image/jpeg")

    @pytest.mark.asyncio
    async def test_delete_sends_delete_request(self):
        s = self._make_storage()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)
        mock_client.delete     = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await s.delete("products", "seller/image.jpg")

        url = mock_client.delete.call_args[0][0]
        assert url == "https://test.supabase.co/storage/v1/object/products/seller/image.jpg"

    @pytest.mark.asyncio
    async def test_delete_treats_404_as_success(self):
        s = self._make_storage()
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)
        mock_client.delete     = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await s.delete("products", "gone.jpg")  # Must not raise.

    @pytest.mark.asyncio
    async def test_list_all_files_posts_to_list_endpoint(self):
        s = self._make_storage()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=[
            {"name": "seller/img1.jpg", "updated_at": "2026-01-01T00:00:00Z"},
            {"name": "seller/img2.jpg", "updated_at": "2026-01-02T00:00:00Z"},
        ])

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)
        mock_client.post       = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            files = await s.list_all_files("products")

        posted_url = mock_client.post.call_args[0][0]
        assert "/storage/v1/object/list/products" in posted_url
        assert len(files) == 2
        assert all("url" in f for f in files)
        assert files[0]["url"].endswith("seller/img1.jpg")

    @pytest.mark.asyncio
    async def test_list_all_files_attaches_public_url(self):
        s = self._make_storage()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=[
            {"name": "folder/photo.webp", "updated_at": "2026-01-01T00:00:00Z"},
        ])

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)
        mock_client.post       = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            files = await s.list_all_files("products")

        assert files[0]["url"] == s.get_public_url("products", "folder/photo.webp")


# ══════════════════════════════════════════════════════════════════════════════
# RESEND EMAIL CLIENT
# ══════════════════════════════════════════════════════════════════════════════

class TestResendEmailClient:

    @pytest.mark.asyncio
    async def test_send_email_calls_resend_sdk(self):
        from app.integrations.resend_client import send_email
        from app.core.config import settings

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = {"id": "email-001"}
            result = await send_email(
                to="buyer@test.com",
                subject="Test subject",
                html="<p>body</p>",
            )

        assert result is True
        assert mock_thread.called
        call_args = mock_thread.call_args[0]
        assert call_args[0].__name__ == "send"
        payload = call_args[1]
        assert payload["to"] == ["buyer@test.com"]
        assert payload["subject"] == "Test subject"
        assert payload["html"] == "<p>body</p>"
        assert settings.FROM_EMAIL in payload["from"]

    @pytest.mark.asyncio
    async def test_send_email_accepts_list_of_recipients(self):
        from app.integrations.resend_client import send_email

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = {"id": "email-002"}
            await send_email(
                to=["a@test.com", "b@test.com"],
                subject="Multi",
                html="<p>hi</p>",
            )

        payload = mock_thread.call_args[0][1]
        assert payload["to"] == ["a@test.com", "b@test.com"]

    @pytest.mark.asyncio
    async def test_send_email_returns_false_on_exception_without_raising(self):
        from app.integrations.resend_client import send_email

        with patch("asyncio.to_thread", new_callable=AsyncMock, side_effect=Exception("API down")):
            result = await send_email(to="x@test.com", subject="s", html="h")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_includes_reply_to_when_provided(self):
        from app.integrations.resend_client import send_email

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = {}
            await send_email(
                to="x@test.com", subject="s", html="h",
                reply_to="support@wearhowz.com",
            )

        payload = mock_thread.call_args[0][1]
        assert payload.get("reply_to") == "support@wearhowz.com"

    @pytest.mark.asyncio
    async def test_send_verification_email_subject_and_token_in_html(self):
        from app.integrations.resend_client import send_verification_email

        captured = {}

        async def fake_send(to, subject, html, reply_to=None):
            captured["subject"] = subject
            captured["html"]    = html
            return True

        with patch("app.integrations.resend_client.send_email", side_effect=fake_send):
            await send_verification_email("u@test.com", "Ali", "tok-abc123")

        assert "verify" in captured["subject"].lower()
        assert "tok-abc123" in captured["html"]
        assert "Ali" in captured["html"]

    @pytest.mark.asyncio
    async def test_send_password_reset_email_subject_and_token_in_html(self):
        from app.integrations.resend_client import send_password_reset_email

        captured = {}

        async def fake_send(to, subject, html, reply_to=None):
            captured["subject"] = subject
            captured["html"]    = html
            return True

        with patch("app.integrations.resend_client.send_email", side_effect=fake_send):
            await send_password_reset_email("u@test.com", "Sara", "reset-xyz")

        assert "reset" in captured["subject"].lower() or "password" in captured["subject"].lower()
        assert "reset-xyz" in captured["html"]

    @pytest.mark.asyncio
    async def test_send_order_confirmation_email_includes_order_number_and_total(self):
        from app.integrations.resend_client import send_order_confirmation_email

        captured = {}

        async def fake_send(to, subject, html, reply_to=None):
            captured["subject"] = subject
            captured["html"]    = html
            return True

        with patch("app.integrations.resend_client.send_email", side_effect=fake_send):
            await send_order_confirmation_email(
                "buyer@test.com", "Ali",
                "WH-000123", 2600,
                [{"product_name": "Hoodie", "quantity": 1, "subtotal": 2600}],
            )

        assert "WH-000123" in captured["subject"] or "WH-000123" in captured["html"]
        assert "2,600" in captured["html"]

    @pytest.mark.asyncio
    async def test_send_shipping_notification_includes_tracking_number(self):
        from app.integrations.resend_client import send_shipping_notification_email

        captured = {}

        async def fake_send(to, subject, html, reply_to=None):
            captured["html"] = html
            return True

        with patch("app.integrations.resend_client.send_email", side_effect=fake_send):
            await send_shipping_notification_email(
                "buyer@test.com", "Ali", "WH-000456",
                "TCS-12345", "TCS", "Brand X",
            )

        assert "TCS-12345" in captured["html"]
        assert "TCS" in captured["html"]


# ══════════════════════════════════════════════════════════════════════════════
# ARQ WORKER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkerRegistration:

    def setup_method(self):
        from app.tasks.worker import WorkerSettings
        self.ws = WorkerSettings

    def _function_names(self) -> set[str]:
        return {fn.__name__ for fn in self.ws.functions}

    def _cron_names(self) -> set[str]:
        # arq CronJob.name is 'cron:<fn>' — use coroutine.__name__ for bare name.
        return {c.coroutine.__name__ for c in self.ws.cron_jobs}

    def test_all_email_tasks_registered(self):
        names = self._function_names()
        for expected in (
            "task_send_verification_email",
            "task_send_password_reset_email",
            "task_send_order_confirmation",
            "task_send_shipping_notification",
            "task_send_cod_timeout",
            "task_send_seller_approved",
        ):
            assert expected in names, f"Missing from functions: {expected}"

    def test_all_notification_tasks_registered(self):
        names = self._function_names()
        for expected in (
            "send_order_confirmation",
            "send_order_status_update",
            "send_payout_notification",
            "notify_seller_decision",
            "broadcast_notification",
        ):
            assert expected in names, f"Missing from functions: {expected}"

    def test_order_and_wallet_tasks_registered(self):
        names = self._function_names()
        for expected in (
            "cod_verification_timeout",
            "expire_pending_orders",
            "settle_commission",
            "move_pending_to_available",
        ):
            assert expected in names, f"Missing from functions: {expected}"

    def test_cleanup_tasks_registered(self):
        names = self._function_names()
        for expected in (
            "cleanup_abandoned_carts",
            "cleanup_expired_sessions",
            "cleanup_soft_deleted_users",
            "cleanup_expired_reset_tokens",
            "archive_old_notifications",
            "cleanup_orphaned_images",
        ):
            assert expected in names, f"Missing from functions: {expected}"

    def test_no_duplicate_function_names(self):
        names = [fn.__name__ for fn in self.ws.functions]
        duplicates = {n for n in names if names.count(n) > 1}
        assert not duplicates, f"Duplicate function names in WorkerSettings: {duplicates}"

    def test_send_order_confirmation_resolves_to_notification_tasks(self):
        from app.tasks.notification_tasks import send_order_confirmation as notif_version
        registered = next(
            fn for fn in self.ws.functions if fn.__name__ == "send_order_confirmation"
        )
        assert registered is notif_version

    def test_cleanup_tasks_have_cron_schedules(self):
        cron_names = self._cron_names()
        for expected in (
            "cleanup_abandoned_carts",
            "cleanup_expired_sessions",
            "cleanup_soft_deleted_users",
            "cleanup_expired_reset_tokens",
            "archive_old_notifications",
            "cleanup_orphaned_images",
        ):
            assert expected in cron_names, f"Missing from cron_jobs: {expected}"

    def test_move_pending_to_available_is_in_cron_jobs(self):
        assert "move_pending_to_available" in self._cron_names()

    def test_expire_pending_orders_is_in_cron_jobs(self):
        assert "expire_pending_orders" in self._cron_names()

    def test_max_tries_set_for_retries(self):
        assert self.ws.max_tries >= 3

    def test_retry_jobs_enabled(self):
        assert self.ws.retry_jobs is True
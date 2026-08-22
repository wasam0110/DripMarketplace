"""Integration tests — Block 9: Notifications."""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from app.api.deps import get_db, require_customer, require_admin
import app.models.user         # noqa
import app.models.notification # noqa

from app.api.v1.notifications import router as notif_router
from app.core.database import get_db
from app.core.exceptions import DRIPException


@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.include_router(notif_router)

    @test_app.exception_handler(DRIPException)
    async def drip_handler(request, exc):
        return JSONResponse(status_code=exc.http_status, content={"detail": exc.message})

    result = MagicMock()
    result.scalars.return_value.all.return_value        = []
    result.scalar_one_or_none.return_value              = None
    result.scalar_one.return_value                      = 0

    async def mock_db():
        session          = MagicMock()
        session.execute  = AsyncMock(return_value=result)
        session.commit   = AsyncMock()
        session.rollback = AsyncMock()
        session.flush    = AsyncMock()
        yield session

    test_app.dependency_overrides[get_db] = mock_db
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c

@pytest.fixture
def authenticated_client():
    test_app = FastAPI()
    test_app.include_router(notif_router)

    @test_app.exception_handler(DRIPException)
    async def drip_handler(request, exc):
        return JSONResponse(
            status_code=exc.http_status,
            content={"detail": exc.message},
        )

    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalar_one_or_none.return_value = None
    result.scalar_one.return_value = 0

    async def mock_db():
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.flush = AsyncMock()
        yield session

    async def mock_customer():
        return {
            "sub": str(uuid4()),
            "role": "customer",
        }

    async def mock_admin():
        return {
            "sub": str(uuid4()),
            "role": "admin",
        }

    test_app.dependency_overrides[get_db] = mock_db
    test_app.dependency_overrides[require_customer] = mock_customer
    test_app.dependency_overrides[require_admin] = mock_admin

    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c

class TestUserNotificationEndpoints:
    def test_list_no_auth(self, client):
        r = client.get("/notifications")
        assert r.status_code in (401, 422)

    def test_mark_read_no_auth(self, client):
        r = client.post(f"/notifications/{uuid4()}/read")
        assert r.status_code in (401, 422)

    def test_mark_all_read_no_auth(self, client):
        r = client.post("/notifications/read-all")
        assert r.status_code in (401, 422)

    def test_get_preferences_no_auth(self, client):
        r = client.get("/notifications/preferences")
        assert r.status_code in (401, 422)

    def test_update_preferences_no_auth(self, client):
        r = client.patch("/notifications/preferences",
                         json={"order_updates_email": False})
        assert r.status_code in (401, 422)

    def test_list_invalid_page(self, authenticated_client):
       r = authenticated_client.get("/notifications?page=0")
       assert r.status_code == 422


class TestAdminNotificationEndpoints:
    def test_broadcast_no_auth(self, client):
        r = client.post("/admin/notifications/broadcast", json={
            "title": "Test",
            "body": "Test broadcast message",
            "audience": "all"
        })
        assert r.status_code in (401, 422)

    def test_broadcast_invalid_audience(self, authenticated_client):
        r = authenticated_client.post("/admin/notifications/broadcast", json={
            "title": "Test",
            "body": "Test broadcast",
            "audience": "admins"
        })
        assert r.status_code == 422

    def test_broadcast_empty_title(self, authenticated_client):
        r = authenticated_client.post("/admin/notifications/broadcast", json={
            "title": "",
            "body": "Test broadcast",
            "audience": "all"
        })
        assert r.status_code == 422

    def test_email_log_no_auth(self, client):
        r = client.get("/admin/notifications/email-log")
        assert r.status_code in (401, 422)

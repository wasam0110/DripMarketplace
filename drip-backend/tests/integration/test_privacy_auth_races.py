"""Refresh rotation and deletion use the same user-before-session lock order."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_customer_privacy import ready_to_delete
from test_marketplace_regressions import market as marketplace_fixture
from test_preship_deletion import deletion
from test_release_native import db as committed_db

from app.core.exceptions import AuthenticationError
from app.core.security import hash_refresh_token
from app.models.user import UserSession
from app.repositories.user_repo import SessionRepository
from app.services.account_lifecycle import lock_active_user
from app.services.auth_service import AuthService
from app.services.customer_service import CustomerService

pytestmark = pytest.mark.integration
market = marketplace_fixture
db = committed_db


@pytest.mark.parametrize("first", ["delete", "refresh"])
async def test_refresh_deletion_race_leaves_no_sessions(test_engine, db, market, first):
    await ready_to_delete(db, market)
    uid = market.buyer.id
    raw_token = "synthetic-privacy-refresh-token"
    await SessionRepository.create(
        db,
        user_id=uid,
        token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await db.commit()

    async def remove(session):
        return await CustomerService(session).delete_account(uid, deletion())

    async def refresh(session):
        return await AuthService.refresh_token(session, raw_token)

    actions = {"delete": remove, "refresh": refresh}
    second = "refresh" if first == "delete" else "delete"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as winner:
        await lock_active_user(winner, uid)

        async def competing():
            async with factory() as session:
                return await actions[second](session)

        pending = asyncio.create_task(competing())
        try:
            await asyncio.sleep(0.1)
            assert not pending.done()
            await actions[first](winner)
            if first == "delete":
                with pytest.raises(AuthenticationError):
                    await asyncio.wait_for(pending, timeout=10)
            else:
                await asyncio.wait_for(pending, timeout=10)
        finally:
            if not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
    await db.refresh(market.buyer)
    assert market.buyer.deleted_at is not None
    assert (
        await db.scalar(select(func.count(UserSession.id)).where(UserSession.user_id == uid)) == 0
    )

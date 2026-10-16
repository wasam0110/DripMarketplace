"""Old Redis opt-outs survive migration and cannot override subsequent edits."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from test_marketplace_regressions import market as marketplace_fixture

from app.core.exceptions import ExternalServiceError
from app.models.notification import NotificationPreference
from app.schemas.notification import UpdatePreferencesRequest
from app.services.notification_service import NotificationService

pytestmark = pytest.mark.integration
market = marketplace_fixture


async def test_import_then_explicit_edit_is_not_overwritten(db, market, isolated_redis):
    key = f"notif_prefs:{market.buyer.id}"
    await isolated_redis.hset(
        key,
        mapping={
            "email_promotions": "0",
            "email_order_updates": "false",
            "email_new_arrivals": "1",
        },
    )
    service = NotificationService(db)
    prefs = await service.get_preferences(market.buyer.id)
    assert not prefs.promotions_email and not prefs.order_updates_email
    assert prefs.email_new_arrivals
    changed = await service.update_preferences(
        market.buyer.id, UpdatePreferencesRequest(order_updates_email=True)
    )
    assert changed.order_updates_email and not changed.promotions_email
    assert (await service.get_preferences(market.buyer.id)).order_updates_email
    assert await isolated_redis.exists(key)  # Keep old data until retention is approved.


async def test_conflicting_preexisting_records_preserve_opt_out(db, market, isolated_redis):
    db.add(NotificationPreference(user_id=market.buyer.id, promotions_email=False))
    await db.commit()
    await isolated_redis.hset(
        f"notif_prefs:{market.buyer.id}",
        mapping={"email_promotions": "1", "email_order_updates": "0"},
    )
    prefs = await NotificationService(db).get_preferences(market.buyer.id)
    assert not prefs.promotions_email and not prefs.order_updates_email


@pytest.mark.parametrize("failure", ["outage", "malformed"])
async def test_import_failure_never_assumes_consent(
    db, market, isolated_redis, monkeypatch, failure
):
    if failure == "outage":
        monkeypatch.setattr(isolated_redis, "hgetall", AsyncMock(side_effect=ConnectionError()))
    else:
        await isolated_redis.hset(
            f"notif_prefs:{market.buyer.id}", mapping={"email_promotions": "?"}
        )
    with pytest.raises(ExternalServiceError):
        await NotificationService(db).get_preferences(market.buyer.id)
    prefs = await db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == market.buyer.id)
    )
    assert not prefs.legacy_imported
    await db.rollback()

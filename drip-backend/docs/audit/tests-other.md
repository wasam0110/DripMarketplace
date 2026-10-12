# Backend source index: tests-other

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## tests/conftest.py

177 lines; SHA-256 `9c66acfe2e55f09c73a2b7453561f4c82ed67e032dbef68802f11e3614b10b5e`. [Open source](../../tests/conftest.py).

Backend imports: `app.core.config`, `app.core.database`, `app.core.security`, `app.models.base`.

- `test_engine` (async), lines 60-85: No function docstring; consult the source body and layer walkthrough.
  Calls: `RuntimeError`, `conn.execute`, `conn.run_sync`, `create_async_engine`, `engine.begin`, `engine.dispose`, `make_url`, `pytest.skip`, `setup.begin`, `setup.dispose`, `target.database.endswith`, `text` ... (13 distinct call expressions).
- `db` (async), lines 89-95: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncSession`, `connection.begin`, `test_engine.connect`, `transaction.rollback`.
  Mutation/I-O-related call names: `transaction.rollback`.
- `isolated_redis` (async), lines 99-105: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.aclose`, `fakeredis.aioredis.FakeRedis`, `monkeypatch.setattr`, `pytest_asyncio.fixture`.
- `client` (async), lines 111-128: Async HTTP client pointing at the FastAPI test app.
  Calls: `ASGITransport`, `AsyncClient`, `app.dependency_overrides.clear`.
- `client.override_get_db` (async), lines 116-117: No function docstring; consult the source body and layer walkthrough.
- `_make_auth_headers` (sync), lines 133-135: No function docstring; consult the source body and layer walkthrough.
  Calls: `create_access_token`.
- `customer_headers` (sync), lines 139-141: Auth headers for a generic customer user.
  Calls: `_make_auth_headers`.
- `seller_headers` (sync), lines 145-151: Auth headers for a generic seller user.
  Calls: `_make_auth_headers`.
- `admin_headers` (sync), lines 155-157: Auth headers for an admin user.
  Calls: `_make_auth_headers`.
- `valid_contact_payload` (sync), lines 163-168: No function docstring; consult the source body and layer walkthrough.
- `valid_address_payload` (sync), lines 172-177: No function docstring; consult the source body and layer walkthrough.

## tests/integration/test_admin_api.py

157 lines; SHA-256 `377a687adba6e5c9202b524d3a1f7d86734e28bb3bd3016f3340c9aa26d972bc`. [Open source](../../tests/integration/test_admin_api.py).

Backend imports: `app.api.v1.admin`, `app.core.database`, `app.core.exceptions`.

- `client` (sync), lines 24-51: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `FastAPI`, `JSONResponse`, `MagicMock`, `TestClient`, `test_app.exception_handler`, `test_app.include_router`.
- `client.drip_handler` (async), lines 31-32: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `test_app.exception_handler`.
- `client.mock_db` (async), lines 40-47: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`.
- Class `TestDashboard`, lines 54-61; bases: .
- `TestDashboard.test_no_auth` (sync), lines 55-57: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestDashboard.test_invalid_period` (sync), lines 59-61: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- Class `TestSellerAdmin`, lines 64-97; bases: .
- `TestSellerAdmin.test_list_no_auth` (sync), lines 65-67: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerAdmin.test_list_invalid_status` (sync), lines 69-71: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerAdmin.test_detail_no_auth` (sync), lines 73-75: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `uuid4`.
- `TestSellerAdmin.test_approve_no_auth` (sync), lines 77-79: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestSellerAdmin.test_reject_no_auth` (sync), lines 81-84: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestSellerAdmin.test_reject_short_reason` (sync), lines 86-88: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestSellerAdmin.test_suspend_no_auth` (sync), lines 90-93: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestSellerAdmin.test_reinstate_no_auth` (sync), lines 95-97: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- Class `TestOrderAdmin`, lines 100-107; bases: .
- `TestOrderAdmin.test_list_no_auth` (sync), lines 101-103: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestOrderAdmin.test_list_invalid_payment_method` (sync), lines 105-107: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- Class `TestCODQueue`, lines 110-121; bases: .
- `TestCODQueue.test_list_no_auth` (sync), lines 111-113: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestCODQueue.test_verify_no_auth` (sync), lines 115-117: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestCODQueue.test_cancel_no_auth` (sync), lines 119-121: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- Class `TestPayoutAdmin`, lines 124-143; bases: .
- `TestPayoutAdmin.test_list_no_auth` (sync), lines 125-127: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPayoutAdmin.test_list_invalid_status` (sync), lines 129-131: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPayoutAdmin.test_approve_no_auth` (sync), lines 133-135: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestPayoutAdmin.test_reject_no_auth` (sync), lines 137-139: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestPayoutAdmin.test_complete_no_auth` (sync), lines 141-143: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- Class `TestSettingsAdmin`, lines 146-157; bases: .
- `TestSettingsAdmin.test_get_no_auth` (sync), lines 147-149: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSettingsAdmin.test_update_no_auth` (sync), lines 151-153: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.patch`.
- `TestSettingsAdmin.test_update_invalid_rate` (sync), lines 155-157: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.patch`.

## tests/integration/test_analytics_api.py

118 lines; SHA-256 `f54f84558ace04e2958f8810b9fa47f988a8a48bcb7c81553df4638867057d32`. [Open source](../../tests/integration/test_analytics_api.py).

Backend imports: `app.api.v1.analytics.admin`, `app.api.v1.analytics.seller`, `app.core.database`, `app.core.exceptions`.

- `client` (sync), lines 21-46: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `FastAPI`, `JSONResponse`, `MagicMock`, `TestClient`, `test_app.exception_handler`, `test_app.include_router`.
- `client.drip_handler` (async), lines 27-28: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `test_app.exception_handler`.
- `client.mock_db` (async), lines 37-42: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`.
- Class `TestSellerAnalyticsEndpoints`, lines 49-76; bases: .
- `TestSellerAnalyticsEndpoints.test_overview_no_auth` (sync), lines 50-52: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerAnalyticsEndpoints.test_overview_invalid_period` (sync), lines 54-56: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerAnalyticsEndpoints.test_revenue_no_auth` (sync), lines 58-60: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerAnalyticsEndpoints.test_revenue_invalid_granularity` (sync), lines 62-64: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerAnalyticsEndpoints.test_top_products_no_auth` (sync), lines 66-68: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerAnalyticsEndpoints.test_top_products_invalid_sort` (sync), lines 70-72: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerAnalyticsEndpoints.test_inventory_health_no_auth` (sync), lines 74-76: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- Class `TestAdminAnalyticsEndpoints`, lines 79-118; bases: .
- `TestAdminAnalyticsEndpoints.test_platform_no_auth` (sync), lines 80-82: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminAnalyticsEndpoints.test_platform_invalid_period` (sync), lines 84-86: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminAnalyticsEndpoints.test_revenue_no_auth` (sync), lines 88-90: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminAnalyticsEndpoints.test_top_sellers_no_auth` (sync), lines 92-94: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminAnalyticsEndpoints.test_cohort_no_auth` (sync), lines 96-98: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminAnalyticsEndpoints.test_cohort_over_limit` (sync), lines 100-102: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminAnalyticsEndpoints.test_payment_methods_no_auth` (sync), lines 104-106: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminAnalyticsEndpoints.test_cities_no_auth` (sync), lines 108-110: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminAnalyticsEndpoints.test_conversion_no_auth` (sync), lines 112-114: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminAnalyticsEndpoints.test_search_queries_no_auth` (sync), lines 116-118: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.

## tests/integration/test_auth_api.py

164 lines; SHA-256 `01bf2b562379fefb4682a52c5eb057e52eda55d3cf2ed0aa9cfc0a16140834c5`. [Open source](../../tests/integration/test_auth_api.py).

Backend imports: `app.core.middleware`, `app.core.security`, `app.models.user`.

- `test_register_returns_created` (async), lines 17-34: No function docstring; consult the source body and layer walkthrough.
  Calls: `body['message'].lower`, `client.post`, `response.json`, `uuid.uuid4`.
- `test_login_sets_refresh_cookie` (async), lines 39-66: No function docstring; consult the source body and layer walkthrough.
  Calls: `User`, `client.post`, `db.add`, `db.commit`, `db.refresh`, `hash_password`, `response.json`, `uuid.uuid4`.
  Mutation/I-O-related call names: `db.commit`.
- `test_login_rejects_invalid_password` (async), lines 71-93: No function docstring; consult the source body and layer walkthrough.
  Calls: `User`, `client.post`, `db.add`, `db.commit`, `hash_password`, `uuid.uuid4`.
  Mutation/I-O-related call names: `db.commit`.
- `test_me_requires_authentication` (async), lines 98-101: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `test_forgot_password_does_not_enumerate_accounts` (async), lines 106-115: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `response.json`, `response.json()['message'].lower`.
- `test_register_validation_rejects_weak_password` (async), lines 120-133: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `test_rate_limit_middleware_returns_429` (async), lines 138-164: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `monkeypatch.setattr`, `staticmethod`.
- `test_rate_limit_middleware_returns_429.deny_all` (async), lines 142-147: No function docstring; consult the source body and layer walkthrough.

## tests/integration/test_b4_workflows.py

322 lines; SHA-256 `710f539ef35b69b717f58ddd80147a3454bada9fd6ed07a0197bf661597a9dce`. [Open source](../../tests/integration/test_b4_workflows.py).

Backend imports: `app.models.order`, `app.models.return_`, `app.models.seller`, `app.models.user`, `app.schemas.return_`, `app.services.order_access`, `app.services.order_service`, `app.services.return_service`.

- `_competitor_seller` (async), lines 29-47: No function docstring; consult the source body and layer walkthrough.
  Calls: `Seller`, `User`, `db.add`, `db.commit`, `db.flush`, `uuid4`.
  Mutation/I-O-related call names: `db.commit`, `db.flush`.
- `test_seller_return_queue_detail_and_owned_lifecycle` (async), lines 50-114: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await client.get(detail_url, headers=headers)).json`, `_competitor_seller`, `_fulfil_and_collect_cod`, `_request_single_item_return`, `actor_headers`, `client.get`, `client.post`, `detail.json`, `queue.json`, `str`.
- `test_seller_can_reject_owned_return_and_customer_can_dispute` (async), lines 117-135: No function docstring; consult the source body and layer walkthrough.
  Calls: `_fulfil_and_collect_cod`, `_request_single_item_return`, `actor_headers`, `client.post`.
- `test_admin_dispute_detail_reply_and_terminal_state` (async), lines 138-210: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await client.get(url, headers=headers)).json`, `AdminReturnActionRequest`, `OpenDisputeRequest`, `ReturnService`, `_fulfil_and_collect_cod`, `_request_single_item_return`, `actor_headers`, `client.get`, `client.post`, `customer_view.json`, `customer_view.json()['messages'][-1]['body'].startswith`, `db.scalar` ... (22 distinct call expressions).
- `test_guest_capability_can_cancel_only_its_order` (async), lines 213-240: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).create_guest_order`, `actor_headers`, `client.post`, `create_guest_token`, `db.get`, `db.refresh`, `guest_payload`, `uuid4`.
- `test_guest_capability_can_create_and_read_only_its_return` (async), lines 243-322: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).create_guest_order`, `UUID`, `actor_headers`, `admin_detail.json`, `client.get`, `client.post`, `create_guest_token`, `created_return.json`, `datetime.now`, `db.commit`, `db.get` ... (20 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.

## tests/integration/test_dispute_authorization.py

209 lines; SHA-256 `d68114286bd3fa90098a51ec9ee527551575a170e79c376c17b633fe38b3e372`. [Open source](../../tests/integration/test_dispute_authorization.py).

Backend imports: `app.core.exceptions`, `app.core.security`, `app.models.order`, `app.models.return_`, `app.models.user`, `app.schemas.return_`, `app.services.order_service`, `app.services.return_service`.

- `auth_headers` (sync), lines 30-36: No function docstring; consult the source body and layer walkthrough.
  Calls: `create_access_token`, `str`.
- `dispute_case` (async), lines 40-69: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminReturnActionRequest`, `CreateReturnRequest`, `OpenDisputeRequest`, `OrderService`, `OrderService(db).create_guest_order`, `ReturnService`, `SimpleNamespace`, `datetime.now`, `db.commit`, `db.get`, `db.scalar`, `guest_payload` ... (18 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `message_count` (async), lines 72-77: No function docstring; consult the source body and layer walkthrough.
  Calls: `db.scalar`, `func.count`, `select`, `select(func.count(DisputeMessage.id)).where`.
- `test_owner_can_reply_and_cannot_spoof_sender` (async), lines 81-96: No function docstring; consult the source body and layer walkthrough.
  Calls: `auth_headers`, `client.post`, `db.commit`, `db.scalar`, `message_count`, `pytest.mark.parametrize`, `response.json`, `select`, `select(DisputeMessage).where`, `str`.
  Mutation/I-O-related call names: `db.commit`.
- `test_non_owner_cannot_reply_or_probe_state` (async), lines 101-127: No function docstring; consult the source body and layer walkthrough.
  Calls: `User`, `auth_headers`, `client.post`, `db.add`, `db.commit`, `message_count`, `pytest.mark.parametrize`, `response.json`, `str`, `uuid4`.
  Mutation/I-O-related call names: `db.commit`.
- `test_owner_cannot_reply_to_terminal_dispute` (async), lines 134-144: No function docstring; consult the source body and layer walkthrough.
  Calls: `auth_headers`, `client.post`, `db.commit`, `message_count`, `pytest.mark.parametrize`, `response.json`.
  Mutation/I-O-related call names: `db.commit`.
- `test_reply_requires_authentication` (async), lines 147-150: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `message_count`.
- `test_missing_return_is_not_found` (async), lines 153-161: No function docstring; consult the source body and layer walkthrough.
  Calls: `auth_headers`, `client.post`, `message_count`, `response.json`, `uuid4`.
- `test_owned_return_without_dispute_is_not_found` (async), lines 164-181: No function docstring; consult the source body and layer walkthrough.
  Calls: `Return`, `auth_headers`, `client.post`, `db.add`, `db.commit`, `db.get`, `message_count`, `response.json`.
  Mutation/I-O-related call names: `db.commit`.
- `test_service_also_enforces_ownership` (async), lines 184-191: No function docstring; consult the source body and layer walkthrough.
  Calls: `AddDisputeMessageRequest`, `ReturnService`, `ReturnService(db).add_message`, `message_count`, `pytest.raises`.
- `test_admin_review_and_resolution_remain_available` (async), lines 194-209: No function docstring; consult the source body and layer walkthrough.
  Calls: `auth_headers`, `client.get`, `client.post`, `len`, `message_count`, `response.json`, `str`.

## tests/integration/test_marketplace_regressions.py

1745 lines; SHA-256 `32b3a34e1b53b9d5ccb9afd94662bc0f9297360a4c3571e9043561f14a5ad363`. [Open source](../../tests/integration/test_marketplace_regressions.py).

Backend imports: `app.api.deps`, `app.api.v1.admin.brands`, `app.api.v1.admin.reviews`, `app.core.config`, `app.core.exceptions`, `app.core.security`, `app.integrations.payfast`, `app.models.admin`, `app.models.coupon`, `app.models.order`, `app.models.payment`, `app.models.product`, `app.models.review`, `app.models.seller`, `app.models.user`, `app.models.wallet`, `app.schemas.admin`, `app.schemas.order`, `app.schemas.payment`, `app.schemas.product`, `app.schemas.return_`, `app.schemas.seller`, `app.schemas.user`, `app.schemas.wallet`, `app.services.admin_service`, `app.services.analytics_service`, `app.services.cart_service`, `app.services.commission_service`, `app.services.customer_service`, `app.services.order_service`, `app.services.payment_service`, `app.services.product_service`, `app.services.return_service`, `app.services.seller_service`, `app.services.slot_service`, `app.services.wallet_service`.

- `market` (async), lines 47-111: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `Product`, `ProductImage`, `ProductInventory`, `ProductVariant`, `Seller`, `SellerWallet`, `SimpleNamespace`, `User`, `db.add`, `db.add_all`, `db.commit` ... (13 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`, `db.flush`.
- `guest_payload` (sync), lines 114-123: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateGuestOrderRequest`.
- `test_guest_checkout_payment_idempotence_and_access` (async), lines 126-144: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `OrderService`, `OrderService(db).create_guest_order`, `PaymentService`, `db.refresh`, `db.scalar`, `func.count`, `guest_payload`, `pytest.raises`, `select`, `service.get_status`, `service.initiate`.
- `test_guest_quote_is_authoritative_public_and_read_only` (async), lines 147-198: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `SystemSetting`, `client.post`, `db.add_all`, `db.commit`, `db.refresh`, `db.scalar`, `func.count`, `len`, `response.json`, `select`, `str`.
  Mutation/I-O-related call names: `db.commit`.
- `test_guest_quote_merges_duplicates_and_matches_created_order` (async), lines 201-221: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateGuestOrderRequest`, `GuestCheckoutQuoteRequest`, `OrderService`, `len`, `service.create_guest_order`, `service.quote_guest_checkout`.
- `test_guest_quote_reports_payment_availability` (async), lines 224-237: No function docstring; consult the source body and layer walkthrough.
  Calls: `GuestCheckoutQuoteRequest`, `OrderService`, `OrderService(db).quote_guest_checkout`, `monkeypatch.setattr`.
- `test_guest_quote_rejects_coupon_and_unavailable_stock` (async), lines 240-257: No function docstring; consult the source body and layer walkthrough.
  Calls: `GuestCheckoutQuoteRequest`, `OrderService`, `db.commit`, `pytest.raises`, `service.quote_guest_checkout`.
  Mutation/I-O-related call names: `db.commit`.
- `test_coupon_changes_persisted_order_and_seller_totals` (async), lines 260-281: No function docstring; consult the source body and layer walkthrough.
  Calls: `Coupon`, `CreateOrderRequest`, `Decimal`, `OrderService`, `OrderService(db, isolated_redis).create_order`, `db.add`, `db.commit`, `db.get`, `db.scalar`, `isolated_redis.hgetall`, `isolated_redis.hset`, `select` ... (14 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_hidden_products_cannot_be_ordered` (async), lines 284-290: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).create_guest_order`, `ProductService`, `ProductService(db).get_variants`, `db.commit`, `guest_payload`, `pytest.raises`.
  Mutation/I-O-related call names: `db.commit`.
- `test_invalid_fulfilment_and_unpaid_delivery_are_rejected` (async), lines 293-303: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).create_guest_order`, `OrderService(db).update_seller_order_status`, `UpdateSellerOrderRequest`, `db.scalar`, `guest_payload`, `pytest.raises`, `select`, `select(SellerOrder).where`.
- `test_fulfilment_deducts_inventory_once_and_collection_settles` (async), lines 306-334: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).verify_cod`, `Decimal`, `OrderService`, `OrderService(db).create_guest_order`, `PaymentService`, `PaymentService(db).initiate`, `PaymentService(db).record_cod_collection`, `UpdateSellerOrderRequest`, `db.refresh`, `db.scalar`, `guest_payload` ... (16 distinct call expressions).
- `test_refund_request_is_pending_capped_and_idempotent` (async), lines 337-357: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).create_guest_order`, `PaymentService`, `PaymentService(db).initiate`, `RefundRequest`, `db.commit`, `db.get`, `guest_payload`, `pytest.raises`, `service.confirm_refund`, `service.refund`.
  Mutation/I-O-related call names: `db.commit`.
- `test_admin_refund_queue_detail_history_and_balances` (async), lines 360-474: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `OrderService`, `OrderService(db).create_guest_order`, `PaymentService`, `PaymentService(db).initiate`, `RefundRequest`, `User`, `actor_headers`, `client.get`, `client.post`, `completed.json`, `completed_detail.json` ... (24 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`, `db.flush`.
- `test_admin_refund_reads_validate_filters_and_missing_records` (async), lines 477-490: No function docstring; consult the source body and layer walkthrough.
  Calls: `actor_headers`, `client.get`, `uuid4`.
- `test_seller_cannot_edit_another_brand` (async), lines 493-495: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db)._require_owned`, `pytest.raises`, `uuid4`.
- `test_all_analytics_queries_run` (async), lines 498-514: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminAnalyticsService`, `SellerAnalyticsService`, `admin.get_cities`, `admin.get_cohort`, `admin.get_conversion`, `admin.get_payment_methods`, `admin.get_platform_analytics`, `admin.get_platform_revenue`, `admin.get_search_queries`, `admin.get_top_sellers`, `seller.get_inventory_health`, `seller.get_overview` ... (14 distinct call expressions).
- `test_payment_callback_amount_signature_and_replay` (async), lines 517-559: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `OrderService`, `OrderService(db).create_guest_order`, `PayFastClient`, `PaymentService`, `db.commit`, `db.get`, `dict`, `gateway.callback_hash`, `guest_payload`, `monkeypatch.setattr`, `pytest.raises` ... (15 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_payfast_status_reconciliation_is_verified_and_idempotent` (async), lines 562-597: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `OrderService`, `OrderService(db).create_guest_order`, `PayFastClient`, `PaymentService`, `db.commit`, `db.get`, `db.refresh`, `guest_payload`, `monkeypatch.setattr`, `service.initiate`, `service.reconcile_payfast` ... (13 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_payfast_status_reconciliation_rejects_mismatched_basket` (async), lines 600-635: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `OrderService`, `OrderService(db).create_guest_order`, `PayFastClient`, `PaymentService`, `db.commit`, `db.get`, `guest_payload`, `monkeypatch.setattr`, `service.initiate`, `service.reconcile_payfast`, `str` ... (13 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_roles_deleted_accounts_and_password_version` (async), lines 638-660: No function docstring; consult the source body and layer walkthrough.
  Calls: `create_access_token`, `datetime.now`, `db.commit`, `get_current_user_payload`, `pytest.raises`, `require_seller`, `str`.
  Mutation/I-O-related call names: `db.commit`.
- `test_product_controls_price_cursor_and_visibility` (async), lines 663-699: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateVariantRequest`, `Decimal`, `Product`, `ProductService`, `UpdateProductRequest`, `UpdateVariantRequest`, `db.add`, `db.commit`, `len`, `next`, `service.add_variant`, `service.get_catalogue` ... (15 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_analytics_uses_recorded_events_and_cohorts` (async), lines 702-726: No function docstring; consult the source body and layer walkthrough.
  Calls: `AddToCartRequest`, `AdminAnalyticsService`, `CartService`, `CartService(db, isolated_redis).add_item`, `CreateOrderRequest`, `OrderService`, `OrderService(db, isolated_redis).create_order`, `ProductService`, `ProductService(db).get_catalogue`, `ProductService(db).get_product_detail`, `db.commit`, `db.get` ... (15 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_review_moderation_and_single_vote` (async), lines 729-752: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateReviewRequest`, `CustomerService`, `ModerateReviewRequest`, `db.get`, `db.refresh`, `moderate_review`, `service.create_review`, `service.delete_review`, `service.vote_review`, `str`.
  Mutation/I-O-related call names: `service.delete_review`.
- `test_guest_token_scoped_to_one_order` (async), lines 755-761: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).create_guest_order`, `OrderService(db).get_order_by_number`, `PaymentService`, `PaymentService(db).initiate`, `guest_payload`, `pytest.raises`.
- `test_seller_registration_payment_and_dashboard` (async), lines 764-790: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).approve_seller`, `SellerRegistrationPaymentRequest`, `SellerRegistrationRequest`, `SellerService`, `SellerService(db).get_dashboard`, `SellerService(db).register`, `db.get`, `record_registration_payment`, `str`.
- `test_wallet_withdrawal_rejection_and_transfer_receipt` (async), lines 793-844: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `SellerBankAccount`, `WalletService`, `WithdrawalRequest`, `db.add`, `db.commit`, `db.scalar`, `func.count`, `next`, `pytest.raises`, `select`, `select(SellerWallet).where` ... (19 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_recorded_slot_revenue_and_dashboard_period` (async), lines 847-872: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminAnalyticsService`, `AdminAnalyticsService(db).get_platform_analytics`, `AdminService`, `AdminService(db).get_dashboard`, `Decimal`, `SlotPurchaseRequest`, `SlotService`, `SlotService(db).purchase_slots`, `datetime.now`, `db.commit`, `db.scalar`, `pytest.raises` ... (15 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_http_guest_checkout_and_browser_token_header` (async), lines 875-911: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `allowed.json`, `app.dependency_overrides.pop`, `client.get`, `client.options`, `client.post`, `created.json`, `guest_payload`, `guest_payload(market).model_dump`, `httpx.ASGITransport`, `httpx.AsyncClient`.
- `test_http_guest_checkout_and_browser_token_header.override_db` (async), lines 882-883: No function docstring; consult the source body and layer walkthrough.
- `test_runtime_settings_drive_pricing_checkout_and_commission` (async), lines 914-959: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `CartService`, `CartService(db, isolated_redis).get_cart`, `CommissionService`, `CommissionService(db).settle`, `Decimal`, `OrderService`, `OrderService(db).create_guest_order`, `Payment`, `SlotService`, `SlotService(db).get_pricing`, `admin.update_settings` ... (21 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_zero_registration_fee_still_charges_optional_slots` (async), lines 969-1000: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `Decimal`, `SellerRegistrationRequest`, `SellerService`, `SellerService(db).get_profile`, `SellerService(db).register`, `admin.approve_seller`, `admin.get_dashboard`, `admin.update_settings`, `db.get`, `pytest.mark.parametrize`, `pytest.raises`.
- `actor_headers` (sync), lines 1003-1009: No function docstring; consult the source body and layer walkthrough.
  Calls: `create_access_token`, `str`.
- `test_http_runtime_pricing_and_payment_due_snapshot` (async), lines 1012-1052: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `SellerRegistrationPaymentRequest`, `SellerRegistrationRequest`, `SellerService`, `SellerService(db).get_profile`, `SellerService(db).register`, `client.get`, `db.get`, `quote.json`, `record_registration_payment`, `service.update_settings`, `str`.
- `test_http_wallet_precision_roles_and_duplicate_payout_actions` (async), lines 1055-1134: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `SellerBankAccount`, `actor_headers`, `client.get`, `client.post`, `completed.json`, `db.add`, `db.commit`, `db.scalar`, `first.json`, `func.count`, `history.json` ... (22 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_dashboard_periods_precision_and_filtered_order_totals` (async), lines 1137-1199: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `CommissionLedger`, `Decimal`, `OrderService`, `OrderService(db).create_guest_order`, `SellerService`, `SellerService(db).get_dashboard`, `actor_headers`, `admin.get_dashboard`, `admin.list_orders`, `admin.list_sellers`, `client.get` ... (26 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `_fulfil_and_collect_cod` (async), lines 1205-1239: Shared helper: logged-in user COD order → fully fulfilled → COD collected.
  Calls: `AdminService`, `AdminService(db).verify_cod`, `CreateOrderRequest`, `OrderService`, `OrderService(db, isolated_redis).create_order`, `PaymentService`, `PaymentService(db).initiate`, `PaymentService(db).record_cod_collection`, `UpdateSellerOrderRequest`, `db.get`, `db.scalar`, `isolated_redis.hset` ... (17 distinct call expressions).
- `_do_return_and_process` (async), lines 1242-1265: Create return → approve → receive → process_refund. Returns refund_id.
  Calls: `AdminReturnActionRequest`, `CreateReturnRequest`, `ReturnService`, `ReturnService(db).approve_return`, `ReturnService(db).mark_received`, `ReturnService(db).process_refund`, `ReturnService(db).request_return`, `UUID`, `db.scalar`, `select`, `select(OrderItem).where`, `str`.
- `_request_single_item_return` (async), lines 1268-1289: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateReturnRequest`, `ReturnService`, `ReturnService(db).request_return`, `db.scalar`, `select`, `select(OrderItem).where`, `str`.
- `test_admin_return_detail_is_enriched_and_admin_only` (async), lines 1292-1343: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `_fulfil_and_collect_cod`, `_request_single_item_return`, `actor_headers`, `client.get`, `customer_detail.json`, `response.json`, `str`, `uuid4`.
- `test_admin_return_detail_tracks_actions_and_linked_refund` (async), lines 1346-1389: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await client.get(url, headers=headers)).json`, `AdminReturnActionRequest`, `Decimal`, `PaymentService`, `PaymentService(db).confirm_refund`, `ReturnService`, `UUID`, `_fulfil_and_collect_cod`, `_request_single_item_return`, `actor_headers`, `client.get`, `service.approve_return` ... (14 distinct call expressions).
- `test_return_refund_reverses_seller_pending_balance` (async), lines 1392-1427: Full happy path: COD collected → commission in pending → return 1 of 2 units
  Calls: `Decimal`, `PaymentService`, `PaymentService(db).confirm_refund`, `_do_return_and_process`, `_fulfil_and_collect_cod`, `db.refresh`, `db.scalar`, `select`, `select(WalletTransaction).where`.
- `test_return_refund_reverses_seller_available_balance` (async), lines 1430-1464: When funds have been released from the hold period (released_at set), the
  Calls: `Decimal`, `PaymentService`, `PaymentService(db).confirm_refund`, `_do_return_and_process`, `_fulfil_and_collect_cod`, `datetime.now`, `db.commit`, `db.refresh`, `db.scalar`, `select`, `select(CommissionLedger).where`, `select(WalletTransaction).where`.
  Mutation/I-O-related call names: `db.commit`.
- `test_return_refund_idempotent_no_double_reversal` (async), lines 1467-1496: Calling confirm_refund twice with the same reference must not:
  Calls: `Decimal`, `PaymentService`, `PaymentService(db).confirm_refund`, `_do_return_and_process`, `_fulfil_and_collect_cod`, `db.refresh`, `db.scalar`, `func.count`, `select`, `select(func.count(WalletTransaction.id)).where`.
- `test_refund_before_settlement_reduces_gross_at_settle_time` (async), lines 1499-1564: Edge case: admin confirms a direct refund before COD is collected.
  Calls: `AdminService`, `AdminService(db).verify_cod`, `CreateOrderRequest`, `Decimal`, `OrderService`, `OrderService(db, isolated_redis).create_order`, `PaymentService`, `PaymentService(db).confirm_refund`, `PaymentService(db).initiate`, `PaymentService(db).record_cod_collection`, `Refund`, `UpdateSellerOrderRequest` ... (23 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_direct_refund_prorates_across_two_sellers` (async), lines 1567-1705: Multi-brand order with two settled sellers.
  Calls: `(await db.execute(select(WalletTransaction).where(WalletTransaction.reference.like(f'return-refund:{refund.id}%'), WalletTransaction.type == WalletTxType.debit_adjustment))).scalars`, `(await db.execute(select(WalletTransaction).where(WalletTransaction.reference.like(f'return-refund:{refund.id}%'), WalletTransaction.type == WalletTxType.debit_adjustment))).scalars().all`, `CommissionLedger`, `CommissionService`, `CommissionService(db).reverse_for_refund`, `Decimal`, `Order`, `Pmt`, `Refund`, `SO`, `Seller`, `SellerWallet` ... (25 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`, `db.flush`.
- `test_seller_already_withdrawn_platform_absorbs_shortfall` (async), lines 1708-1745: If the seller has already withdrawn all funds (available_balance = 0,
  Calls: `Decimal`, `PaymentService`, `PaymentService(db).confirm_refund`, `_do_return_and_process`, `_fulfil_and_collect_cod`, `datetime.now`, `db.commit`, `db.refresh`, `db.scalar`, `select`, `select(CommissionLedger).where`, `select(WalletTransaction).where`.
  Mutation/I-O-related call names: `db.commit`.

## tests/integration/test_notification_api.py

141 lines; SHA-256 `7a702a3e3883f3fd844acf23c03caf284a24ceaa94df9616d1fb5869852ebb21`. [Open source](../../tests/integration/test_notification_api.py).

Backend imports: `app.api.deps`, `app.api.v1.notifications`, `app.core.database`, `app.core.exceptions`.

- `client` (sync), lines 18-41: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `FastAPI`, `JSONResponse`, `MagicMock`, `TestClient`, `test_app.exception_handler`, `test_app.include_router`.
- `client.drip_handler` (async), lines 23-24: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `test_app.exception_handler`.
- `client.mock_db` (async), lines 31-37: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`.
- `authenticated_client` (sync), lines 44-85: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `FastAPI`, `JSONResponse`, `MagicMock`, `TestClient`, `str`, `test_app.exception_handler`, `test_app.include_router`, `uuid4`.
- `authenticated_client.drip_handler` (async), lines 49-53: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `test_app.exception_handler`.
- `authenticated_client.mock_db` (async), lines 60-66: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`.
- `authenticated_client.mock_customer` (async), lines 68-72: No function docstring; consult the source body and layer walkthrough.
  Calls: `str`, `uuid4`.
- `authenticated_client.mock_admin` (async), lines 74-78: No function docstring; consult the source body and layer walkthrough.
  Calls: `str`, `uuid4`.
- Class `TestUserNotificationEndpoints`, lines 87-111; bases: .
- `TestUserNotificationEndpoints.test_list_no_auth` (sync), lines 88-90: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestUserNotificationEndpoints.test_mark_read_no_auth` (sync), lines 92-94: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestUserNotificationEndpoints.test_mark_all_read_no_auth` (sync), lines 96-98: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestUserNotificationEndpoints.test_get_preferences_no_auth` (sync), lines 100-102: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestUserNotificationEndpoints.test_update_preferences_no_auth` (sync), lines 104-107: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.patch`.
- `TestUserNotificationEndpoints.test_list_invalid_page` (sync), lines 109-111: No function docstring; consult the source body and layer walkthrough.
  Calls: `authenticated_client.get`.
- Class `TestAdminNotificationEndpoints`, lines 114-141; bases: .
- `TestAdminNotificationEndpoints.test_broadcast_no_auth` (sync), lines 115-121: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestAdminNotificationEndpoints.test_broadcast_invalid_audience` (sync), lines 123-129: No function docstring; consult the source body and layer walkthrough.
  Calls: `authenticated_client.post`.
- `TestAdminNotificationEndpoints.test_broadcast_empty_title` (sync), lines 131-137: No function docstring; consult the source body and layer walkthrough.
  Calls: `authenticated_client.post`.
- `TestAdminNotificationEndpoints.test_email_log_no_auth` (sync), lines 139-141: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.

## tests/integration/test_order_api.py

161 lines; SHA-256 `b2d0ad2bf509fa369ef2ec36233bb20137d4dff55beba643efc85a5008e9a190`. [Open source](../../tests/integration/test_order_api.py).

Backend imports: `app.api.v1.cart`, `app.api.v1.orders`, `app.core.database`, `app.core.exceptions`.

- `client` (sync), lines 22-46: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `FastAPI`, `JSONResponse`, `MagicMock`, `TestClient`, `test_app.exception_handler`, `test_app.include_router`.
- `client.drip_handler` (async), lines 28-29: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `test_app.exception_handler`.
- `client.mock_db` (async), lines 36-42: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`.
- Class `TestOrderEndpoints`, lines 61-100; bases: .
- `TestOrderEndpoints.test_place_order_no_auth` (sync), lines 62-64: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestOrderEndpoints.test_place_order_invalid_payment_method` (sync), lines 66-68: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestOrderEndpoints.test_place_order_missing_address` (sync), lines 70-72: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestOrderEndpoints.test_guest_order_no_items` (sync), lines 74-78: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestOrderEndpoints.test_guest_order_invalid_phone` (sync), lines 80-84: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `str`, `uuid4`.
- `TestOrderEndpoints.test_list_orders_no_auth` (sync), lines 86-88: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestOrderEndpoints.test_get_order_no_auth` (sync), lines 90-92: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `uuid4`.
- `TestOrderEndpoints.test_cancel_order_no_auth` (sync), lines 94-96: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestOrderEndpoints.test_get_order_by_number_requires_access` (sync), lines 98-100: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- Class `TestCouponEndpoints`, lines 103-110; bases: .
- `TestCouponEndpoints.test_validate_no_auth` (sync), lines 104-106: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestCouponEndpoints.test_validate_zero_subtotal` (sync), lines 108-110: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- Class `TestSellerOrderEndpoints`, lines 113-135; bases: .
- `TestSellerOrderEndpoints.test_list_seller_orders_no_auth` (sync), lines 114-116: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerOrderEndpoints.test_list_seller_orders_invalid_status` (sync), lines 118-120: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerOrderEndpoints.test_update_status_no_auth` (sync), lines 122-125: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.put`, `uuid4`.
- `TestSellerOrderEndpoints.test_update_status_shipped_no_tracking` (sync), lines 127-130: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.put`, `uuid4`.
- `TestSellerOrderEndpoints.test_update_status_invalid_status` (sync), lines 132-135: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.put`, `uuid4`.
- Class `TestCartEndpoints`, lines 138-161; bases: .
- `TestCartEndpoints.test_get_cart_no_auth` (sync), lines 139-141: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestCartEndpoints.test_add_to_cart_no_auth` (sync), lines 143-145: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `str`, `uuid4`.
- `TestCartEndpoints.test_add_to_cart_zero_qty` (sync), lines 147-149: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `str`, `uuid4`.
- `TestCartEndpoints.test_update_cart_item_no_auth` (sync), lines 151-153: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.patch`, `uuid4`.
- `TestCartEndpoints.test_remove_cart_item_no_auth` (sync), lines 155-157: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.delete`, `uuid4`.
  Mutation/I-O-related call names: `client.delete`.
- `TestCartEndpoints.test_clear_cart_no_auth` (sync), lines 159-161: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.

## tests/integration/test_payment_api.py

104 lines; SHA-256 `643562c7282a20b08cfdc747b6cb9429ebb56b8abec6ebc6100ae80b597c3613`. [Open source](../../tests/integration/test_payment_api.py).

Backend imports: `app.api.v1.payments`, `app.core.database`, `app.core.exceptions`.

- `client` (sync), lines 22-45: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `FastAPI`, `JSONResponse`, `MagicMock`, `TestClient`, `test_app.exception_handler`, `test_app.include_router`.
- `client.drip_handler` (async), lines 27-28: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `test_app.exception_handler`.
- `client.mock_db` (async), lines 35-41: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`.
- Class `TestCustomerEndpoints`, lines 48-66; bases: .
- `TestCustomerEndpoints.test_initiate_no_auth` (sync), lines 49-52: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `str`, `uuid4`.
- `TestCustomerEndpoints.test_status_no_auth` (sync), lines 54-56: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `uuid4`.
- `TestCustomerEndpoints.test_retry_no_auth` (sync), lines 58-61: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestCustomerEndpoints.test_retry_invalid_method` (sync), lines 63-66: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- Class `TestCallbackEndpoints`, lines 69-74; bases: .
- `TestCallbackEndpoints.test_stripe_callback_retired` (sync), lines 70-74: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- Class `TestAdminEndpoints`, lines 77-103; bases: .
- `TestAdminEndpoints.test_gateway_status_no_auth` (sync), lines 78-80: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminEndpoints.test_list_payments_no_auth` (sync), lines 82-84: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminEndpoints.test_list_payments_invalid_status` (sync), lines 86-88: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminEndpoints.test_refund_no_auth` (sync), lines 90-93: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestAdminEndpoints.test_refund_short_reason` (sync), lines 95-98: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestAdminEndpoints.test_refund_zero_amount` (sync), lines 100-103: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.

## tests/integration/test_product_api.py

135 lines; SHA-256 `9bfbae26a9b2aad56698fff1ad242e834108b3d78f5e212e45b8920696690c9d`. [Open source](../../tests/integration/test_product_api.py).

Backend imports: `app.api.v1.products`, `app.core.database`, `app.core.exceptions`.

- `client` (sync), lines 20-52: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `FastAPI`, `JSONResponse`, `MagicMock`, `TestClient`, `test_app.exception_handler`, `test_app.include_router`.
- `client.drip_handler` (async), lines 33-34: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `test_app.exception_handler`.
- `client.mock_db` (async), lines 36-47: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`.
- Class `TestPublicEndpoints`, lines 55-82; bases: .
- `TestPublicEndpoints.test_catalogue_ok` (sync), lines 56-58: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPublicEndpoints.test_catalogue_invalid_sort` (sync), lines 60-62: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPublicEndpoints.test_catalogue_price_range` (sync), lines 64-66: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPublicEndpoints.test_get_product_not_found` (sync), lines 68-70: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `uuid4`.
- `TestPublicEndpoints.test_search_too_short` (sync), lines 72-74: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPublicEndpoints.test_search_valid` (sync), lines 76-78: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPublicEndpoints.test_variants_endpoint` (sync), lines 80-82: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `uuid4`.
- Class `TestSellerEndpoints`, lines 85-125; bases: .
- `TestSellerEndpoints.test_list_seller_products_no_auth` (sync), lines 86-88: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerEndpoints.test_create_product_no_auth` (sync), lines 90-92: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestSellerEndpoints.test_create_product_invalid_price` (sync), lines 94-100: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestSellerEndpoints.test_create_product_missing_fields` (sync), lines 102-104: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestSellerEndpoints.test_publish_no_auth` (sync), lines 106-108: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestSellerEndpoints.test_unpublish_no_auth` (sync), lines 110-112: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestSellerEndpoints.test_delete_no_auth` (sync), lines 114-116: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.delete`, `uuid4`.
  Mutation/I-O-related call names: `client.delete`.
- `TestSellerEndpoints.test_upload_images_no_auth` (sync), lines 118-121: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestSellerEndpoints.test_invalid_status_filter` (sync), lines 123-125: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- Class `TestAdminEndpoints`, lines 128-135; bases: .
- `TestAdminEndpoints.test_admin_list_no_auth` (sync), lines 129-131: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminEndpoints.test_admin_hide_no_auth` (sync), lines 133-135: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.

## tests/integration/test_release_journeys.py

737 lines; SHA-256 `aed2064c5e9ded8871e6734bac23eba4ca5805215cb3a724a2b0fdbc78559978`. [Open source](../../tests/integration/test_release_journeys.py).

Backend imports: `app.api.deps`, `app.core`, `app.core.config`, `app.core.exceptions`, `app.core.security`, `app.integrations`, `app.integrations.supabase_storage`, `app.models.notification`, `app.models.order`, `app.models.product`, `app.models.review`, `app.models.seller`, `app.models.user`, `app.models.wallet`, `app.repositories.user_repo`, `app.schemas`, `app.schemas.notification`, `app.schemas.order`, `app.schemas.return_`, `app.schemas.seller`, `app.services`, `app.services.admin_service`, `app.services.auth_service`, `app.services.cart_service`, `app.services.customer_service`, `app.services.image_service`, `app.services.notification_service`, `app.services.order_service`, `app.services.product_service`, `app.services.return_service`, `app.services.seller_service`, `app.tasks`.

- `headers` (sync), lines 27-31: No function docstring; consult the source body and layer walkthrough.
  Calls: `create_access_token`, `str`.
- `request` (async), lines 34-37: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.request`, `headers`, `response.json`.
- `test_customer_profile_address_wishlist_preferences` (async), lines 40-110: No function docstring; consult the source body and layer walkthrough.
  Calls: `len`, `request`, `str`, `sum`.
- `test_customer_review_moderation_edit_and_delete` (async), lines 113-152: No function docstring; consult the source body and layer walkthrough.
  Calls: `db.commit`, `db.get`, `len`, `request`, `str`.
  Mutation/I-O-related call names: `db.commit`.
- `test_customer_password_revokes_tokens_and_account_deletion` (async), lines 155-186: No function docstring; consult the source body and layer walkthrough.
  Calls: `CustomerService`, `db.commit`, `db.refresh`, `get_current_user_payload`, `hash_password`, `headers`, `headers(market.buyer)['Authorization'].removeprefix`, `pytest.raises`, `service.change_password`, `service.delete_account`, `service.get_profile`, `user.ChangePasswordRequest` ... (14 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`, `service.delete_account`.
- `test_customer_avatar_uses_validated_storage_upload` (async), lines 189-205: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `CustomerService`, `CustomerService(db).upload_avatar`, `Image.new`, `Image.new('RGB', (2, 2), 'red').save`, `db.refresh`, `image.getvalue`, `io.BytesIO`, `monkeypatch.setattr`.
  Mutation/I-O-related call names: `CustomerService(db).upload_avatar`.
- `test_auth_registration_verification_rotation_reset_and_logout` (async), lines 208-237: No function docstring; consult the source body and layer walkthrough.
  Calls: `AuthService.change_password`, `AuthService.forgot_password`, `AuthService.login`, `AuthService.logout`, `AuthService.refresh_token`, `AuthService.register`, `AuthService.reset_password`, `AuthService.verify_email`, `auth.RegisterRequest`, `datetime.now`, `db.scalar`, `decode_access_token` ... (16 distinct call expressions).
- `test_admin_totp_policy_and_seller_refresh` (async), lines 240-261: No function docstring; consult the source body and layer walkthrough.
  Calls: `AuthService.login`, `AuthService.refresh_token`, `AuthService.setup_totp`, `AuthService.verify_and_enable_totp`, `db.commit`, `decode_access_token`, `hash_password`, `pyotp.TOTP`, `pyotp.TOTP(setup.secret).now`, `pytest.raises`, `str`.
  Mutation/I-O-related call names: `db.commit`.
- `test_seller_product_lifecycle_and_public_visibility` (async), lines 264-319: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `ProductService`, `ProductService(db).add_images`, `len`, `monkeypatch.setattr`, `request`, `reversed`, `str`.
- `test_notifications_delivery_preferences_and_jobs` (async), lines 322-395: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `BroadcastRequest`, `NotificationService`, `OrderService`, `OrderService(db).create_guest_order`, `Payout`, `UpdatePreferencesRequest`, `db.add`, `db.commit`, `db.get`, `db.scalar`, `guest_payload` ... (27 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`, `notification_tasks.send_order_confirmation`, `notification_tasks.send_order_status_update`, `notification_tasks.send_payout_notification`.
- `test_user_repository_state_changes_and_invalid_fields` (async), lines 398-421: No function docstring; consult the source body and layer walkthrough.
  Calls: `len`, `pytest.raises`, `repo.bulk_update`, `repo.count`, `repo.exists`, `repo.get_by_field`, `repo.get_by_id`, `repo.get_for_update`, `repo.list_all`, `repo.restore`, `repo.soft_delete`, `repo.update`.
  Mutation/I-O-related call names: `repo.soft_delete`.
- `test_cart_customer_order_and_cancellation` (async), lines 424-458: No function docstring; consult the source body and layer walkthrough.
  Calls: `AddToCartRequest`, `CancelOrderRequest`, `CartService`, `CreateOrderRequest`, `OrderService`, `cart.add_item`, `cart.get_cart`, `cart.get_raw_items`, `cart.remove_item`, `cart.sync`, `cart.update_item`, `db.refresh` ... (21 distinct call expressions).
- `test_admin_seller_bank_and_cod_management` (async), lines 461-507: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `CreateBankAccountRequest`, `OrderService`, `OrderService(db).create_guest_order`, `SellerProfileUpdateRequest`, `SellerService`, `admin.cancel_cod`, `admin.get_seller`, `admin.list_cod_queue`, `admin.reinstate_seller`, `admin.reject_seller`, `admin.suspend_seller` ... (21 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`, `service.delete_bank_account`.
- `test_return_rejection_dispute_and_resolution` (async), lines 510-568: No function docstring; consult the source body and layer walkthrough.
  Calls: `AddDisputeMessageRequest`, `AdminReturnActionRequest`, `CreateReturnRequest`, `OpenDisputeRequest`, `OrderService`, `OrderService(db).create_guest_order`, `ResolveDisputeRequest`, `ReturnService`, `datetime.now`, `db.commit`, `db.get`, `db.scalar` ... (28 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_storefront_category_visibility_brand_and_banner_lifecycle` (async), lines 571-613: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).create_banner`, `Category`, `db.add_all`, `db.commit`, `db.flush`, `len`, `request`.
  Mutation/I-O-related call names: `db.commit`, `db.flush`.
- `test_readonly_admin_seller_endpoints_use_real_queries` (async), lines 616-635: No function docstring; consult the source body and layer walkthrough.
  Calls: `app.openapi`, `request`.
- `test_browser_auth_cookie_refresh_reset_and_logout` (async), lines 638-673: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `client.get`, `client.post`, `logged.json`, `monkeypatch.setattr`, `verified.json`.
- `test_google_signed_identity_callback_and_replay` (async), lines 676-737: No function docstring; consult the source body and layer walkthrough.
  Calls: `(datetime.now(UTC) + timedelta(minutes=5)).timestamp`, `AsyncMock`, `MagicMock`, `Request`, `Response`, `datetime.now`, `datetime.now(UTC).timestamp`, `db.scalar`, `f'state={state}&code=test-code'.encode`, `f'{google.STATE_COOKIE}={state}'.encode`, `func.count`, `google.finish_google_login` ... (27 distinct call expressions).

## tests/integration/test_release_native.py

334 lines; SHA-256 `9fbf2d20458f5891607fd71bcf540442845f0ab77700e465f505a05d2b2846fd`. [Open source](../../tests/integration/test_release_native.py).

Backend imports: `app.api.v1.health`, `app.core`, `app.core.config`, `app.core.exceptions`, `app.integrations.payfast`, `app.models.base`, `app.models.order`, `app.models.payment`, `app.models.return_`, `app.models.seller`, `app.models.wallet`, `app.repositories.inventory_repo`, `app.repositories.notification_repo`, `app.schemas.payment`, `app.schemas.return_`, `app.schemas.wallet`, `app.services.commission_service`, `app.services.order_service`, `app.services.payment_service`, `app.services.return_service`, `app.services.wallet_service`, `app.tasks`, `app.tasks.cleanup_tasks`, `app.tasks.order_tasks`, `app.tasks.wallet_tasks`.

- `db` (async), lines 42-45: No function docstring; consult the source body and layer walkthrough.
  Calls: `async_sessionmaker`, `async_sessionmaker(test_engine, expire_on_commit=False)`.
  Mutation/I-O-related call names: `async_sessionmaker(test_engine, expire_on_commit=False)`.
- `race` (async), lines 48-58: No function docstring; consult the source body and layer walkthrough.
  Calls: `action`, `async_sessionmaker`, `async_sessionmaker(engine, expire_on_commit=False)`, `asyncio.Event`, `asyncio.create_task`, `asyncio.gather`, `asyncio.wait_for`, `range`, `ready.set`, `ready.wait`, `run`.
  Mutation/I-O-related call names: `async_sessionmaker(engine, expire_on_commit=False)`.
- `race.run` (async), lines 51-54: No function docstring; consult the source body and layer walkthrough.
  Calls: `action`, `async_sessionmaker`, `async_sessionmaker(engine, expire_on_commit=False)`, `ready.wait`.
  Mutation/I-O-related call names: `async_sessionmaker(engine, expire_on_commit=False)`.
- `test_competing_stock_reservations_do_not_oversell` (async), lines 61-70: No function docstring; consult the source body and layer walkthrough.
  Calls: `InventoryRepository`, `InventoryRepository(session).reserve`, `db.refresh`, `race`, `session.commit`, `sorted`.
  Mutation/I-O-related call names: `session.commit`.
- `test_competing_stock_reservations_do_not_oversell.reserve` (async), lines 62-65: No function docstring; consult the source body and layer walkthrough.
  Calls: `InventoryRepository`, `InventoryRepository(session).reserve`, `session.commit`.
  Mutation/I-O-related call names: `session.commit`.
- `test_competing_withdrawals_cannot_spend_same_balance` (async), lines 73-93: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `SellerBankAccount`, `WalletService`, `WalletService(session).request_withdrawal`, `WithdrawalRequest`, `db.add`, `db.commit`, `db.refresh`, `db.scalar`, `func.count`, `isinstance`, `race` ... (15 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `paid_order` (async), lines 96-104: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).create_guest_order`, `PaymentService`, `PaymentService(db).initiate`, `db.commit`, `db.get`, `db.scalar`, `guest_payload`, `select`, `select(SellerOrder).where`.
  Mutation/I-O-related call names: `db.commit`.
- `test_concurrent_settlement_and_release_are_once_only` (async), lines 107-135: No function docstring; consult the source body and layer walkthrough.
  Calls: `CommissionService`, `CommissionService(session).settle`, `Decimal`, `async_sessionmaker`, `asyncio.gather`, `asyncio.wait_for`, `datetime.now`, `db.commit`, `db.scalar`, `func.count`, `monkeypatch.setattr`, `move_pending_to_available` ... (18 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_concurrent_refund_confirmation_reverses_once` (async), lines 138-161: No function docstring; consult the source body and layer walkthrough.
  Calls: `CommissionService`, `CommissionService(db).settle`, `Decimal`, `PaymentService`, `PaymentService(db).refund`, `PaymentService(session).confirm_refund`, `Refund.processed_at.isnot`, `RefundRequest`, `all`, `db.scalar`, `func.count`, `isinstance` ... (18 distinct call expressions).
- `test_competing_admin_and_seller_return_decisions_allow_one_winner` (async), lines 164-202: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminReturnActionRequest`, `CreateReturnRequest`, `OrderService`, `OrderService(db).create_guest_order`, `ReturnService`, `ReturnService(db).request_return`, `db.commit`, `db.get`, `db.scalar`, `guest_payload`, `isinstance`, `race` ... (18 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_competing_admin_and_seller_return_decisions_allow_one_winner.opposing_decisions` (async), lines 190-196: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `service.approve_return`, `service.seller_reject_return`.
- `test_concurrent_payment_callbacks_preserve_one_transition` (async), lines 205-235: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `OrderService`, `OrderService(db).create_guest_order`, `PayFastClient`, `PaymentService`, `PaymentService(db).initiate`, `PaymentService(session).handle_payfast_callback`, `db.commit`, `db.get`, `db.refresh`, `gateway.callback_hash`, `guest_payload` ... (15 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_expiry_workers_release_reservation_once` (async), lines 238-253: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).create_guest_order`, `async_sessionmaker`, `asyncio.gather`, `asyncio.wait_for`, `datetime.now`, `db.commit`, `db.get`, `db.refresh`, `expire_pending_orders`, `guest_payload`, `monkeypatch.setattr` ... (13 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_notification_read_archive_and_ownership` (async), lines 256-288: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationRepository`, `archive_old_notifications`, `async_sessionmaker`, `datetime.now`, `db.commit`, `db.refresh`, `monkeypatch.setattr`, `repo.create`, `repo.list_by_user`, `repo.mark_all_read`, `repo.mark_read`, `repo.unread_count` ... (13 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `test_fresh_migrations_round_trip_and_all_model_columns` (async), lines 291-310: No function docstring; consult the source body and layer walkthrough.
  Calls: `Config`, `command.downgrade`, `command.upgrade`, `connection.execute`, `connection.run_sync`, `select`, `select(table).limit`, `test_engine.begin`.
- `test_fresh_migrations_round_trip_and_all_model_columns.migrations` (sync), lines 302-306: No function docstring; consult the source body and layer walkthrough.
  Calls: `command.downgrade`, `command.upgrade`.
- `test_native_worker_startup_health_and_shutdown` (async), lines 313-334: No function docstring; consult the source body and layer walkthrough.
  Calls: `database.AsyncSessionLocal`, `database.atomic`, `health_check`, `monkeypatch.setattr`, `os.environ.get`, `pytest.skip`, `session.scalar`, `text`, `worker.shutdown`, `worker.startup`.

## tests/integration/test_return_api.py

144 lines; SHA-256 `a2f8625b6e60c70d69be757e76ea21d563286c4948f9dc069c9b65a7dab947d2`. [Open source](../../tests/integration/test_return_api.py).

Backend imports: `app.api.v1.returns`, `app.core.database`, `app.core.exceptions`, `app.models.user`.

- `client` (sync), lines 28-56: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `FastAPI`, `JSONResponse`, `MagicMock`, `TestClient`, `str`, `str(user_id).endswith`, `test_app.exception_handler`, `test_app.include_router`.
- `client.drip_handler` (async), lines 33-34: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `test_app.exception_handler`.
- `client.mock_db` (async), lines 41-52: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `str`, `str(user_id).endswith`.
- `client.mock_db.get_user` (async), lines 45-47: No function docstring; consult the source body and layer walkthrough.
  Calls: `MagicMock`, `str`, `str(user_id).endswith`.
- Class `TestCustomerReturnEndpoints`, lines 59-96; bases: .
- `TestCustomerReturnEndpoints.test_request_return_no_auth` (sync), lines 60-62: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestCustomerReturnEndpoints.test_request_return_short_reason` (sync), lines 64-66: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestCustomerReturnEndpoints.test_request_return_empty_items` (sync), lines 68-70: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestCustomerReturnEndpoints.test_list_returns_no_auth` (sync), lines 72-74: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestCustomerReturnEndpoints.test_get_return_no_auth` (sync), lines 76-78: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `uuid4`.
- `TestCustomerReturnEndpoints.test_open_dispute_no_auth` (sync), lines 80-83: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestCustomerReturnEndpoints.test_open_dispute_short_message` (sync), lines 85-87: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestCustomerReturnEndpoints.test_get_dispute_no_auth` (sync), lines 89-91: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `uuid4`.
- `TestCustomerReturnEndpoints.test_add_message_no_auth` (sync), lines 93-96: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- Class `TestAdminReturnEndpoints`, lines 99-144; bases: .
- `TestAdminReturnEndpoints.test_list_returns_no_auth` (sync), lines 100-102: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminReturnEndpoints.test_list_returns_invalid_status` (sync), lines 104-106: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminReturnEndpoints.test_approve_no_auth` (sync), lines 108-110: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestAdminReturnEndpoints.test_reject_no_auth` (sync), lines 112-114: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestAdminReturnEndpoints.test_received_no_auth` (sync), lines 116-118: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestAdminReturnEndpoints.test_refund_no_auth` (sync), lines 120-122: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestAdminReturnEndpoints.test_list_disputes_no_auth` (sync), lines 124-126: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminReturnEndpoints.test_list_disputes_invalid_status` (sync), lines 128-130: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminReturnEndpoints.test_resolve_dispute_no_auth` (sync), lines 132-137: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestAdminReturnEndpoints.test_resolve_invalid_in_favor_of` (sync), lines 139-144: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.

## tests/integration/test_seed_user_database.py

26 lines; SHA-256 `c63e790a6b4a33bb9a4c42435f0c7ca3b5fd5c27a618a904297e497a03176601`. [Open source](../../tests/integration/test_seed_user_database.py).

Backend imports: `app.schemas.auth`.

- `test_bootstrap_account_never_overwrites_existing_credentials_or_role` (async), lines 11-26: No function docstring; consult the source body and layer walkthrough.
  Calls: `PasswordHasher`, `PasswordHasher().verify`, `RegisterRequest`, `connection.get_raw_connection`, `customer.model_copy`, `db.connection`, `driver.fetchrow`, `insert_user`, `pytest.raises`.

## tests/integration/test_seller_api.py

177 lines; SHA-256 `7220339f20d39ad3fb4ee59f842a0e1176eadf9509ac5bbe41f9da62f128f301`. [Open source](../../tests/integration/test_seller_api.py).

Backend imports: `app.api.deps`, `app.api.v1.analytics.seller`, `app.api.v1.orders`, `app.api.v1.sellers`, `app.core.database`, `app.core.exceptions`.

- `client` (sync), lines 19-53: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `FastAPI`, `JSONResponse`, `MagicMock`, `TestClient`, `app.exception_handler`, `app.include_router`, `pytest.fixture`.
- `client.drip_handler` (async), lines 32-36: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `app.exception_handler`.
- `client.mock_db` (async), lines 39-48: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`.
- Class `TestSlotPriceEndpoint`, lines 68-91; bases: .
- `TestSlotPriceEndpoint.test_zero_extra` (sync), lines 69-75: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `r.json`.
- `TestSlotPriceEndpoint.test_twenty_extra` (sync), lines 77-83: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `r.json`.
- `TestSlotPriceEndpoint.test_negative_rejected` (sync), lines 85-87: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSlotPriceEndpoint.test_over_limit_rejected` (sync), lines 89-91: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- Class `TestRegisterEndpoint`, lines 94-115; bases: .
- `TestRegisterEndpoint.test_empty_payload_rejected` (sync), lines 95-97: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestRegisterEndpoint.test_invalid_phone_rejected` (sync), lines 99-103: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestRegisterEndpoint.test_weak_password_rejected` (sync), lines 105-109: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestRegisterEndpoint.test_short_description_rejected` (sync), lines 111-115: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- Class `TestPrivateEndpoints`, lines 118-177; bases: .
- `TestPrivateEndpoints.test_get_profile_no_auth` (sync), lines 121-123: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPrivateEndpoints.test_patch_profile_no_auth` (sync), lines 125-127: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.patch`.
- `TestPrivateEndpoints.test_dashboard_no_auth` (sync), lines 129-131: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPrivateEndpoints.test_dashboard_invalid_period` (sync), lines 133-135: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPrivateEndpoints.test_orders_no_auth` (sync), lines 137-139: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPrivateEndpoints.test_orders_invalid_status` (sync), lines 141-143: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPrivateEndpoints.test_order_detail_requires_auth` (sync), lines 145-147: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `uuid4`.
- `TestPrivateEndpoints.test_bank_accounts_no_auth` (sync), lines 149-151: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPrivateEndpoints.test_bank_account_empty_body` (sync), lines 153-155: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestPrivateEndpoints.test_analytics_no_auth` (sync), lines 157-159: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPrivateEndpoints.test_analytics_invalid_period` (sync), lines 161-163: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPrivateEndpoints.test_analytics_invalid_granularity` (sync), lines 165-167: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestPrivateEndpoints.test_slot_purchase_zero_qty` (sync), lines 169-172: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.
- `TestPrivateEndpoints.test_slot_purchase_bad_method` (sync), lines 174-177: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`.

## tests/integration/test_wallet_api.py

116 lines; SHA-256 `f9f14e8ef13c8a9dcf7e008d6bc823d316801b1f6b184e75fbb3218c578e683d`. [Open source](../../tests/integration/test_wallet_api.py).

Backend imports: `app.api.v1.wallet`, `app.core.database`, `app.core.exceptions`.

- `client` (sync), lines 23-47: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `FastAPI`, `JSONResponse`, `MagicMock`, `TestClient`, `test_app.exception_handler`, `test_app.include_router`.
- `client.drip_handler` (async), lines 28-29: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `test_app.exception_handler`.
- `client.mock_db` (async), lines 37-43: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`.
- Class `TestSellerWalletEndpoints`, lines 50-94; bases: .
- `TestSellerWalletEndpoints.test_summary_no_auth` (sync), lines 51-53: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerWalletEndpoints.test_transactions_no_auth` (sync), lines 55-57: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerWalletEndpoints.test_transactions_invalid_type` (sync), lines 59-61: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerWalletEndpoints.test_withdraw_no_auth` (sync), lines 63-68: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `str`, `uuid4`.
- `TestSellerWalletEndpoints.test_withdraw_below_minimum` (sync), lines 70-75: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `str`, `uuid4`.
- `TestSellerWalletEndpoints.test_withdraw_zero` (sync), lines 77-82: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `str`, `uuid4`.
- `TestSellerWalletEndpoints.test_payouts_no_auth` (sync), lines 84-86: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerWalletEndpoints.test_payouts_invalid_status` (sync), lines 88-90: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestSellerWalletEndpoints.test_commission_no_auth` (sync), lines 92-94: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- Class `TestAdminWalletEndpoints`, lines 97-116; bases: .
- `TestAdminWalletEndpoints.test_overview_no_auth` (sync), lines 98-100: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminWalletEndpoints.test_admin_payouts_no_auth` (sync), lines 102-104: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminWalletEndpoints.test_admin_payouts_invalid_status` (sync), lines 106-108: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestAdminWalletEndpoints.test_approve_no_auth` (sync), lines 110-112: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestAdminWalletEndpoints.test_reject_no_auth` (sync), lines 114-116: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.

## tests/integration/test_worker_redis.py

82 lines; SHA-256 `0adefad2e07ff0734dc696524b09a06e73cb2ebed9284ed660ac839258c96dc8`. [Open source](../../tests/integration/test_worker_redis.py).

Backend imports: `app.tasks`.

- `test_email_job_retries_and_records_final_result` (async), lines 19-82: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `RedisSettings.from_dsn`, `RuntimeError`, `Worker`, `asyncio.gather`, `asyncio.wait_for`, `create_pool`, `int`, `job.result_info`, `monkeypatch.setattr`, `os.environ.get`, `pool.aclose` ... (26 distinct call expressions).
  Mutation/I-O-related call names: `pool.delete`, `pool.enqueue_job`.

## tests/load/__init__.py

0 lines; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. [Open source](../../tests/load/__init__.py).


## tests/load/locustfile.py

331 lines; SHA-256 `47d5ab5573db071293599d146f4845e9dd29650e04cc9ae493d27d22ba6de95f`. [Open source](../../tests/load/locustfile.py).

- `_rnd` (sync), lines 41-42: No function docstring; consult the source body and layer walkthrough.
  Calls: `''.join`, `random.choices`.
- Class `BrowseUser`, lines 58-109; bases: FastHttpUser.
- `BrowseUser.browse_catalogue` (sync), lines 68-78: GET /products with random filters.
  Calls: `random.choice`, `random.randint`, `random.random`, `resp.failure`, `resp.success`, `self.client.get`, `task`.
- `BrowseUser.search_products` (sync), lines 81-84: No function docstring; consult the source body and layer walkthrough.
  Calls: `random.choice`, `self.client.get`, `task`.
- `BrowseUser.search_suggestions` (sync), lines 87-89: No function docstring; consult the source body and layer walkthrough.
  Calls: `random.choice`, `self.client.get`, `task`.
- `BrowseUser.view_product_detail` (sync), lines 92-105: Simulate loading a product detail page via a random slug.
  Calls: `random.choice`, `resp.failure`, `resp.success`, `self.client.get`, `task`.
- `BrowseUser.health_check` (sync), lines 108-109: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- Class `CustomerUser`, lines 114-183; bases: FastHttpUser.
- `CustomerUser.on_start` (sync), lines 122-147: Log in at the start of each virtual user session.
  Calls: `_rnd`, `os.getenv`, `resp.json`, `resp.json().get`, `self.client.post`.
- `CustomerUser.browse_catalogue` (sync), lines 150-151: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `CustomerUser.view_product` (sync), lines 154-163: No function docstring; consult the source body and layer walkthrough.
  Calls: `resp.success`, `self.client.get`, `task`, `uuid4`.
- `CustomerUser.view_my_orders` (sync), lines 166-167: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `CustomerUser.view_profile` (sync), lines 170-171: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `CustomerUser.view_wishlist` (sync), lines 174-175: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `CustomerUser.view_cart` (sync), lines 178-179: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `CustomerUser.view_notifications` (sync), lines 182-183: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- Class `SellerUser`, lines 188-254; bases: FastHttpUser.
- `SellerUser.on_start` (sync), lines 196-223: No function docstring; consult the source body and layer walkthrough.
  Calls: `_rnd`, `os.getenv`, `resp.json`, `resp.json().get`, `self.client.post`.
- `SellerUser.view_seller_dashboard` (sync), lines 226-230: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `SellerUser.list_seller_orders` (sync), lines 233-234: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `SellerUser.view_inventory` (sync), lines 237-238: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `SellerUser.view_low_stock` (sync), lines 241-242: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `SellerUser.view_seller_profile` (sync), lines 245-246: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `SellerUser.view_wallet_balance` (sync), lines 249-250: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `SellerUser.view_bank_accounts` (sync), lines 253-254: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- Class `AdminUser`, lines 259-298; bases: FastHttpUser.
- `AdminUser.on_start` (sync), lines 267-278: No function docstring; consult the source body and layer walkthrough.
  Calls: `os.getenv`, `resp.json`, `resp.json().get`, `self.client.post`.
- `AdminUser.view_admin_dashboard` (sync), lines 281-282: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `AdminUser.view_admin_orders` (sync), lines 285-286: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `AdminUser.view_cod_queue` (sync), lines 289-290: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `AdminUser.view_admin_inventory` (sync), lines 293-294: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `AdminUser.view_payouts` (sync), lines 297-298: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.client.get`, `task`.
- `on_test_start` (sync), lines 304-309: No function docstring; consult the source body and layer walkthrough.
  Calls: `print`.
- `on_test_stop` (sync), lines 313-331: No function docstring; consult the source body and layer walkthrough.
  Calls: `print`, `stats.total.get_response_time_percentile`.

## tests/security/__init__.py

0 lines; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. [Open source](../../tests/security/__init__.py).


## tests/security/test_auth.py

307 lines; SHA-256 `ebcb84b179d07acc7f5977d4925b89cf7f0f12bc9252a5505c8682c940180580`. [Open source](../../tests/security/test_auth.py).

- `client` (async), lines 30-36: No function docstring; consult the source body and layer walkthrough.
  Calls: `ASGITransport`, `AsyncClient`.
- Class `TestRateLimiting`, lines 44-92; bases: .
- `TestRateLimiting.test_login_rate_limit` (async), lines 45-54: 6th failed login within the window must return 429.
  Calls: `client.post`, `int`, `range`, `resp.headers.get`, `resp.json`.
- `TestRateLimiting.test_register_rate_limit` (async), lines 56-83: Rapid registration attempts should be rate-limited.
  Calls: `all`, `client.post`, `range`, `uuid4`.
- `TestRateLimiting.test_password_reset_rate_limit` (async), lines 85-92: Repeated forgot-password requests for same email should be throttled.
  Calls: `client.post`, `range`.
- Class `TestJWTSecurity`, lines 99-155; bases: .
- `TestJWTSecurity.test_tampered_token_rejected` (async), lines 100-128: Altering the payload of a valid token must return 401.
  Calls: `base64.urlsafe_b64decode`, `base64.urlsafe_b64encode`, `base64.urlsafe_b64encode(json.dumps(decoded).encode()).rstrip`, `base64.urlsafe_b64encode(json.dumps(decoded).encode()).rstrip(b'=').decode`, `client.get`, `client.post`, `json.dumps`, `json.dumps(decoded).encode`, `json.loads`, `len`, `pytest.skip`, `resp.json` ... (15 distinct call expressions).
- `TestJWTSecurity.test_expired_token_rejected` (async), lines 130-141: An expired JWT must return 401 with TOKEN_EXPIRED code.
  Calls: `client.get`.
- `TestJWTSecurity.test_no_token_rejected` (async), lines 143-146: Protected routes must return 401 when no token is supplied.
  Calls: `client.get`.
- `TestJWTSecurity.test_malformed_token_rejected` (async), lines 148-155: Garbage tokens must return 401.
  Calls: `client.get`.
- Class `TestSellerIsolation`, lines 162-211; bases: .
- `TestSellerIsolation.test_seller_cannot_edit_other_sellers_product` (async), lines 163-175: Seller A editing Seller B's product must return 403.
  Calls: `client.patch`.
- `TestSellerIsolation.test_seller_cannot_delete_other_sellers_product` (async), lines 177-187: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.delete`.
  Mutation/I-O-related call names: `client.delete`.
- `TestSellerIsolation.test_seller_cannot_view_other_sellers_wallet` (async), lines 189-196: Wallet endpoint must scope to the authenticated seller.
  Calls: `client.get`.
- `TestSellerIsolation.test_seller_cannot_update_other_sellers_inventory` (async), lines 200-211: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.put`.
- Class `TestRBAC`, lines 218-255; bases: .
- `TestRBAC.test_customer_cannot_access_admin_dashboard` (async), lines 219-223: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestRBAC.test_customer_cannot_access_seller_dashboard` (async), lines 225-229: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestRBAC.test_seller_cannot_access_admin_dashboard` (async), lines 231-235: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`.
- `TestRBAC.test_seller_cannot_approve_payouts` (async), lines 237-244: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `uuid4`.
- `TestRBAC.test_unauthenticated_cannot_place_order` (async), lines 246-255: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `str`, `uuid4`.
- Class `TestPaymentCallbackSecurity`, lines 262-271; bases: .
- `TestPaymentCallbackSecurity.test_payfast_callback_rejects_invalid_hmac` (async), lines 263-266: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `str`, `uuid4`.
- `TestPaymentCallbackSecurity.test_payfast_callback_rejects_missing_signature` (async), lines 268-271: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `str`, `uuid4`.
- Class `TestInputSecurity`, lines 278-307; bases: .
- `TestInputSecurity.test_sql_injection_in_search` (async), lines 279-287: SQL injection attempts in query params must be safely handled.
  Calls: `client.get`.
- `TestInputSecurity.test_xss_in_product_search` (async), lines 289-295: XSS payloads in search must return safe responses (not echoed raw).
  Calls: `client.get`.
- `TestInputSecurity.test_oversized_request_body_rejected` (async), lines 297-301: Very large request bodies should be rejected (413 or 422).
  Calls: `client.post`.
- `TestInputSecurity.test_path_traversal_in_product_slug` (async), lines 303-307: Path traversal in slug must not leak filesystem info.
  Calls: `client.get`.



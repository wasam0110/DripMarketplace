# Backend source index: tests-unit

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## tests/unit/test_admin.py

62 lines; SHA-256 `bba60ee671abd7230374c36d74f15747013f79cbb0aa17c2ce0600cfe3371ea1`. [Open source](../../tests/unit/test_admin.py).

Backend imports: `app.schemas.admin`.

- Class `TestSellerActionSchemas`, lines 11?22; bases: .
- `TestSellerActionSchemas.test_reject_valid` (sync), lines 12?14: No function docstring; consult the source body and layer walkthrough.
  Calls: `RejectSellerRequest`, `len`.
- `TestSellerActionSchemas.test_reject_too_short` (sync), lines 16?18: No function docstring; consult the source body and layer walkthrough.
  Calls: `RejectSellerRequest`, `pytest.raises`.
- `TestSellerActionSchemas.test_suspend_valid` (sync), lines 20?22: No function docstring; consult the source body and layer walkthrough.
  Calls: `SuspendSellerRequest`.
- Class `TestUpdateSettingsSchema`, lines 25?52; bases: .
- `TestUpdateSettingsSchema.test_valid_commission` (sync), lines 26?28: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSettingsRequest`.
- `TestUpdateSettingsSchema.test_commission_above_one_rejected` (sync), lines 30?32: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSettingsRequest`, `pytest.raises`.
- `TestUpdateSettingsSchema.test_commission_negative_rejected` (sync), lines 34?36: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSettingsRequest`, `pytest.raises`.
- `TestUpdateSettingsSchema.test_cod_timeout_below_min` (sync), lines 38?40: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSettingsRequest`, `pytest.raises`.
- `TestUpdateSettingsSchema.test_cod_timeout_above_max` (sync), lines 42?44: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSettingsRequest`, `pytest.raises`.
- `TestUpdateSettingsSchema.test_valid_registration_fee` (sync), lines 46?48: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSettingsRequest`.
- `TestUpdateSettingsSchema.test_all_none_valid` (sync), lines 50?52: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSettingsRequest`.
- Class `TestCODVerifySchema`, lines 55?62; bases: .
- `TestCODVerifySchema.test_no_note_ok` (sync), lines 56?58: No function docstring; consult the source body and layer walkthrough.
  Calls: `CODVerifyRequest`.
- `TestCODVerifySchema.test_with_note` (sync), lines 60?62: No function docstring; consult the source body and layer walkthrough.
  Calls: `CODVerifyRequest`.

## tests/unit/test_analytics.py

93 lines; SHA-256 `03f5c65c6475878cf5b00ca92f45f89863e3dc113a39dd08a7989fc0ab2f3b93`. [Open source](../../tests/unit/test_analytics.py).

Backend imports: `app.schemas.analytics`, `app.services.analytics_service`.

- Class `TestPeriodHelpers`, lines 7?33; bases: .
- `TestPeriodHelpers.test_7d` (sync), lines 8?9: No function docstring; consult the source body and layer walkthrough.
  Calls: `_period_to_days`.
- `TestPeriodHelpers.test_30d` (sync), lines 11?12: No function docstring; consult the source body and layer walkthrough.
  Calls: `_period_to_days`.
- `TestPeriodHelpers.test_90d` (sync), lines 14?15: No function docstring; consult the source body and layer walkthrough.
  Calls: `_period_to_days`.
- `TestPeriodHelpers.test_1y` (sync), lines 17?18: No function docstring; consult the source body and layer walkthrough.
  Calls: `_period_to_days`.
- `TestPeriodHelpers.test_unknown_defaults_to_30` (sync), lines 20?21: No function docstring; consult the source body and layer walkthrough.
  Calls: `_period_to_days`.
- `TestPeriodHelpers.test_date_from_7d_is_recent` (sync), lines 23?27: No function docstring; consult the source body and layer walkthrough.
  Calls: `_date_from`, `datetime.now`.
- `TestPeriodHelpers.test_date_from_1y` (sync), lines 29?33: No function docstring; consult the source body and layer walkthrough.
  Calls: `_date_from`, `datetime.now`.
- Class `TestGranularity`, lines 36?47; bases: .
- `TestGranularity.test_day` (sync), lines 37?38: No function docstring; consult the source body and layer walkthrough.
  Calls: `_trunc`.
- `TestGranularity.test_week` (sync), lines 40?41: No function docstring; consult the source body and layer walkthrough.
  Calls: `_trunc`.
- `TestGranularity.test_month` (sync), lines 43?44: No function docstring; consult the source body and layer walkthrough.
  Calls: `_trunc`.
- `TestGranularity.test_unknown_defaults_to_day` (sync), lines 46?47: No function docstring; consult the source body and layer walkthrough.
  Calls: `_trunc`.
- Class `TestAnalyticsSchemas`, lines 50?93; bases: .
- `TestAnalyticsSchemas.test_seller_overview_schema` (sync), lines 51?58: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerAnalyticsOverview`.
- `TestAnalyticsSchemas.test_platform_analytics_schema` (sync), lines 60?68: No function docstring; consult the source body and layer walkthrough.
  Calls: `PlatformAnalytics`.
- `TestAnalyticsSchemas.test_revenue_day_row` (sync), lines 70?75: No function docstring; consult the source body and layer walkthrough.
  Calls: `RevenueDayRow`.
- `TestAnalyticsSchemas.test_payment_method_stat` (sync), lines 77?80: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentMethodStat`.
- `TestAnalyticsSchemas.test_inventory_health_schema` (sync), lines 82?88: No function docstring; consult the source body and layer walkthrough.
  Calls: `InventoryHealthResponse`.
- `TestAnalyticsSchemas.test_city_row` (sync), lines 90?93: No function docstring; consult the source body and layer walkthrough.
  Calls: `CityRow`.

## tests/unit/test_commission_service.py

239 lines; SHA-256 `a2b25bebd630e5db893b318fbf933e32207f320ee412135085c9a9c3b625c2ab`. [Open source](../../tests/unit/test_commission_service.py).

Backend imports: `app.core.exceptions`, `app.models.order`, `app.models.payment`, `app.models.seller`, `app.services.commission_service`.

- `_make_service` (sync), lines 29?66: Return a CommissionService wired to mocked repos and a mock DB session.
  Calls: `AsyncMock`, `CommissionService`, `Decimal`, `MagicMock`, `statement.column_descriptions[0].get`, `uuid4`.
- `_make_service.scalar_result` (async), lines 40?46: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `MagicMock`, `statement.column_descriptions[0].get`.
- `_make_seller_order` (sync), lines 69?76: No function docstring; consult the source body and layer walkthrough.
  Calls: `MagicMock`, `uuid4`.
- Class `TestCommissionRate`, lines 83?111; bases: .
- `TestCommissionRate.test_rate_is_fifteen_percent` (sync), lines 84?85: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`.
- `TestCommissionRate.test_commission_on_round_amount` (sync), lines 87?92: No function docstring; consult the source body and layer walkthrough.
  Calls: `(subtotal * COMMISSION_RATE).quantize`, `Decimal`.
- `TestCommissionRate.test_commission_on_typical_order` (sync), lines 94?99: PKR 2,499 order — 15% commission.
  Calls: `(subtotal * COMMISSION_RATE).quantize`, `Decimal`.
- `TestCommissionRate.test_commission_on_minimum_price` (sync), lines 101?105: Minimum product price is PKR 100. Commission should be PKR 15.
  Calls: `(subtotal * COMMISSION_RATE).quantize`, `Decimal`.
- `TestCommissionRate.test_commission_on_maximum_price` (sync), lines 107?111: Maximum product price is PKR 500,000.
  Calls: `(subtotal * COMMISSION_RATE).quantize`, `Decimal`.
- Class `TestCommissionRounding`, lines 118?146; bases: .
- `TestCommissionRounding.test_rounding` (sync), lines 128?134: No function docstring; consult the source body and layer walkthrough.
  Calls: `(s * COMMISSION_RATE).quantize`, `Decimal`, `pytest.mark.parametrize`.
- `TestCommissionRounding.test_seller_net_plus_commission_equals_subtotal` (sync), lines 136?146: No money is created or lost in the split.
  Calls: `(s * COMMISSION_RATE).quantize`, `Decimal`, `abs`.
- Class `TestCommissionSettle`, lines 153?220; bases: .
- `TestCommissionSettle.test_settle_creates_commission_ledger_entry` (async), lines 155?164: settle() must create one CommissionLedger entry.
  Calls: `Decimal`, `_make_seller_order`, `_make_service`, `svc.comm_repo.create.assert_awaited_once`, `svc.settle`.
- `TestCommissionSettle.test_settle_credits_seller_pending_balance` (async), lines 167?174: settle() must credit the seller's pending balance.
  Calls: `Decimal`, `_make_seller_order`, `_make_service`, `svc.settle`, `svc.wallet_repo.credit_pending.assert_awaited_once`.
- `TestCommissionSettle.test_settle_is_idempotent` (async), lines 177?186: Calling settle() twice for the same SellerOrder must be a no-op on the 2nd call.
  Calls: `Decimal`, `_make_seller_order`, `_make_service`, `svc.comm_repo.create.assert_not_awaited`, `svc.settle`, `svc.wallet_repo.credit_pending.assert_not_awaited`.
- `TestCommissionSettle.test_settle_raises_for_missing_order` (async), lines 189?200: settle() must raise NotFoundError when the SellerOrder doesn't exist.
  Calls: `AsyncMock`, `MagicMock`, `_make_service`, `pytest.raises`, `svc.settle`, `uuid4`.
- `TestCommissionSettle.test_settle_correct_commission_amount` (async), lines 203?220: settle() must pass the correct PKR amounts to the repo.
  Calls: `(subtotal * COMMISSION_RATE).quantize`, `Decimal`, `_make_seller_order`, `_make_service`, `abs`, `kwargs.get`, `len`, `str`, `svc.settle`.
- Class `TestCommissionConfig`, lines 227?239; bases: .
- `TestCommissionConfig.test_rate_is_a_decimal` (sync), lines 228?229: No function docstring; consult the source body and layer walkthrough.
  Calls: `isinstance`.
- `TestCommissionConfig.test_rate_expressed_as_fraction` (sync), lines 231?234: Rate should be stored as a fraction (0.15), not a percentage (15).
  Calls: `Decimal`.
- `TestCommissionConfig.test_commission_plus_seller_net_covers_full_subtotal` (sync), lines 236?239: 15% + 85% = 100%.
  Calls: `Decimal`.

## tests/unit/test_connected_services.py

557 lines; SHA-256 `45bffa41832b7b4237e5c60e5194b3421be9348eef7e3c9fddc2887cc241698f`. [Open source](../../tests/unit/test_connected_services.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.integrations.resend_client`, `app.integrations.supabase_storage`, `app.services.google_oauth`, `app.tasks.notification_tasks`, `app.tasks.worker`.

- Class `TestGoogleOAuth`, lines 28?153; bases: .
- `TestGoogleOAuth.test_require_configuration_raises_when_unconfigured` (sync), lines 29?43: No function docstring; consult the source body and layer walkthrough.
  Calls: `pytest.raises`, `require_configuration`.
- `TestGoogleOAuth.test_require_configuration_passes_when_set` (sync), lines 45?57: No function docstring; consult the source body and layer walkthrough.
  Calls: `require_configuration`.
- `TestGoogleOAuth.test_start_google_login_authorization_url_contains_required_params` (async), lines 60?94: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `patch`, `start_google_login`.
- `TestGoogleOAuth.test_start_google_login_sets_state_cookie` (async), lines 97?125: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `args[0].startswith`, `patch`, `start_google_login`.
- `TestGoogleOAuth.test_start_google_login_state_and_nonce_are_unique_per_call` (async), lines 128?153: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `len`, `patch`, `range`, `start_google_login`, `states.append`.
- Class `TestSupabaseStorage`, lines 161?299; bases: .
- `TestSupabaseStorage._make_storage` (sync), lines 162?168: No function docstring; consult the source body and layer walkthrough.
  Calls: `SupabaseStorage`.
- `TestSupabaseStorage.test_get_public_url_format` (sync), lines 170?173: No function docstring; consult the source body and layer walkthrough.
  Calls: `s.get_public_url`, `self._make_storage`.
- `TestSupabaseStorage.test_headers_include_auth_and_apikey` (sync), lines 175?179: No function docstring; consult the source body and layer walkthrough.
  Calls: `s._headers`, `self._make_storage`.
- `TestSupabaseStorage.test_headers_include_content_type_when_provided` (sync), lines 181?184: No function docstring; consult the source body and layer walkthrough.
  Calls: `s._headers`, `self._make_storage`.
- `TestSupabaseStorage.test_upload_posts_to_correct_url_and_returns_public_url` (async), lines 187?202: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `patch`, `s.upload`, `self._make_storage`.
  Mutation/I-O-related call names: `s.upload`.
- `TestSupabaseStorage.test_upload_raises_storage_error_on_bad_status` (async), lines 205?219: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `patch`, `pytest.raises`, `s.upload`, `self._make_storage`.
  Mutation/I-O-related call names: `s.upload`.
- `TestSupabaseStorage.test_delete_sends_delete_request` (async), lines 222?237: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `patch`, `s.delete`, `self._make_storage`.
  Mutation/I-O-related call names: `s.delete`.
- `TestSupabaseStorage.test_delete_treats_404_as_success` (async), lines 240?251: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `patch`, `s.delete`, `self._make_storage`.
  Mutation/I-O-related call names: `s.delete`.
- `TestSupabaseStorage.test_list_all_files_posts_to_list_endpoint` (async), lines 254?278: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `all`, `files[0]['url'].endswith`, `len`, `patch`, `s.list_all_files`, `self._make_storage`.
- `TestSupabaseStorage.test_list_all_files_attaches_public_url` (async), lines 281?299: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `patch`, `s.get_public_url`, `s.list_all_files`, `self._make_storage`.
- Class `TestResendEmailClient`, lines 307?456; bases: .
- `TestResendEmailClient._configured_resend` (sync), lines 309?312: No function docstring; consult the source body and layer walkthrough.
  Calls: `monkeypatch.setattr`, `pytest.fixture`.
- `TestResendEmailClient.test_send_email_calls_resend_sdk` (async), lines 315?335: No function docstring; consult the source body and layer walkthrough.
  Calls: `patch`, `send_email`.
  Mutation/I-O-related call names: `send_email`.
- `TestResendEmailClient.test_send_email_accepts_list_of_recipients` (async), lines 338?350: No function docstring; consult the source body and layer walkthrough.
  Calls: `patch`, `send_email`.
  Mutation/I-O-related call names: `send_email`.
- `TestResendEmailClient.test_send_email_returns_false_on_exception_without_raising` (async), lines 353?359: No function docstring; consult the source body and layer walkthrough.
  Calls: `Exception`, `patch`, `send_email`.
  Mutation/I-O-related call names: `send_email`.
- `TestResendEmailClient.test_send_email_includes_reply_to_when_provided` (async), lines 362?375: No function docstring; consult the source body and layer walkthrough.
  Calls: `patch`, `payload.get`, `send_email`.
  Mutation/I-O-related call names: `send_email`.
- `TestResendEmailClient.test_send_verification_email_subject_and_token_in_html` (async), lines 378?393: No function docstring; consult the source body and layer walkthrough.
  Calls: `captured['subject'].lower`, `patch`, `send_verification_email`.
  Mutation/I-O-related call names: `send_verification_email`.
- `TestResendEmailClient.test_send_verification_email_subject_and_token_in_html.fake_send` (async), lines 383?386: No function docstring; consult the source body and layer walkthrough.
- `TestResendEmailClient.test_send_password_reset_email_subject_and_token_in_html` (async), lines 396?410: No function docstring; consult the source body and layer walkthrough.
  Calls: `captured['subject'].lower`, `patch`, `send_password_reset_email`.
  Mutation/I-O-related call names: `send_password_reset_email`.
- `TestResendEmailClient.test_send_password_reset_email_subject_and_token_in_html.fake_send` (async), lines 401?404: No function docstring; consult the source body and layer walkthrough.
- `TestResendEmailClient.test_send_order_confirmation_email_includes_order_number_and_total` (async), lines 413?433: No function docstring; consult the source body and layer walkthrough.
  Calls: `patch`, `send_order_confirmation_email`.
  Mutation/I-O-related call names: `send_order_confirmation_email`.
- `TestResendEmailClient.test_send_order_confirmation_email_includes_order_number_and_total.fake_send` (async), lines 418?421: No function docstring; consult the source body and layer walkthrough.
- `TestResendEmailClient.test_send_shipping_notification_includes_tracking_number` (async), lines 436?456: No function docstring; consult the source body and layer walkthrough.
  Calls: `patch`, `send_shipping_notification_email`.
  Mutation/I-O-related call names: `send_shipping_notification_email`.
- `TestResendEmailClient.test_send_shipping_notification_includes_tracking_number.fake_send` (async), lines 441?443: No function docstring; consult the source body and layer walkthrough.
- Class `TestWorkerRegistration`, lines 464?557; bases: .
- `TestWorkerRegistration.setup_method` (sync), lines 465?468: No function docstring; consult the source body and layer walkthrough.
- `TestWorkerRegistration._function_names` (sync), lines 470?471: No function docstring; consult the source body and layer walkthrough.
- `TestWorkerRegistration._cron_names` (sync), lines 473?475: No function docstring; consult the source body and layer walkthrough.
- `TestWorkerRegistration.test_all_email_tasks_registered` (sync), lines 477?487: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._function_names`.
- `TestWorkerRegistration.test_all_notification_tasks_registered` (sync), lines 489?498: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._function_names`.
- `TestWorkerRegistration.test_order_and_wallet_tasks_registered` (sync), lines 500?508: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._function_names`.
- `TestWorkerRegistration.test_cleanup_tasks_registered` (sync), lines 510?520: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._function_names`.
- `TestWorkerRegistration.test_no_duplicate_function_names` (sync), lines 522?525: No function docstring; consult the source body and layer walkthrough.
  Calls: `names.count`.
- `TestWorkerRegistration.test_send_order_confirmation_resolves_to_notification_tasks` (sync), lines 527?533: No function docstring; consult the source body and layer walkthrough.
  Calls: `next`.
- `TestWorkerRegistration.test_cleanup_tasks_have_cron_schedules` (sync), lines 535?545: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._cron_names`.
- `TestWorkerRegistration.test_move_pending_to_available_is_in_cron_jobs` (sync), lines 547?548: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._cron_names`.
- `TestWorkerRegistration.test_expire_pending_orders_is_in_cron_jobs` (sync), lines 550?551: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._cron_names`.
- `TestWorkerRegistration.test_max_tries_set_for_retries` (sync), lines 553?554: No function docstring; consult the source body and layer walkthrough.
- `TestWorkerRegistration.test_retry_jobs_enabled` (sync), lines 556?557: No function docstring; consult the source body and layer walkthrough.

## tests/unit/test_marketplace_contracts.py

52 lines; SHA-256 `a6ee8dd0fa399a35821663b070b702fae2a74cc17cba8a0eee58793de84923c7`. [Open source](../../tests/unit/test_marketplace_contracts.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.core.security`, `app.services.google_oauth`, `app.services.image_service`.

- `test_unique_routes_and_gap_contracts` (sync), lines 11?16: No function docstring; consult the source body and layer walkthrough.
  Calls: `Counter`, `Counter(routes).items`, `app.openapi`, `getattr`.
- `test_corrupt_image_validation` (sync), lines 20?24: No function docstring; consult the source body and layer walkthrough.
  Calls: `ImageService`, `pytest.mark.parametrize`, `pytest.raises`, `service.to_webp`, `service.validate`.
- `test_logout_revocation_and_redis_outage` (async), lines 27?34: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `RuntimeError`, `datetime.now`, `is_token_revoked`, `monkeypatch.setattr`, `pytest.raises`, `revoke_token`, `timedelta`.
- `test_google_configuration_and_browser_state` (async), lines 37?52: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `Request`, `Response`, `finish_google_login`, `monkeypatch.setattr`, `pytest.raises`, `start_google_login`.

## tests/unit/test_notifications.py

65 lines; SHA-256 `fd331b59f6796e8ed02106130b4dcee9d58834ae455ebe777c23779fd0537ac4`. [Open source](../../tests/unit/test_notifications.py).

Backend imports: `app.schemas.notification`.

- Class `TestUpdatePreferencesSchema`, lines 11?26; bases: .
- `TestUpdatePreferencesSchema.test_all_none_valid` (sync), lines 12?14: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdatePreferencesRequest`.
- `TestUpdatePreferencesSchema.test_set_false` (sync), lines 16?18: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdatePreferencesRequest`.
- `TestUpdatePreferencesSchema.test_partial_update` (sync), lines 20?26: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdatePreferencesRequest`.
- Class `TestBroadcastSchema`, lines 29?65; bases: .
- `TestBroadcastSchema.test_valid_all` (sync), lines 30?36: No function docstring; consult the source body and layer walkthrough.
  Calls: `BroadcastRequest`.
- `TestBroadcastSchema.test_valid_sellers` (sync), lines 38?40: No function docstring; consult the source body and layer walkthrough.
  Calls: `BroadcastRequest`.
- `TestBroadcastSchema.test_invalid_audience` (sync), lines 42?44: No function docstring; consult the source body and layer walkthrough.
  Calls: `BroadcastRequest`, `pytest.raises`.
- `TestBroadcastSchema.test_empty_title_rejected` (sync), lines 46?48: No function docstring; consult the source body and layer walkthrough.
  Calls: `BroadcastRequest`, `pytest.raises`.
- `TestBroadcastSchema.test_title_too_long` (sync), lines 50?52: No function docstring; consult the source body and layer walkthrough.
  Calls: `BroadcastRequest`, `pytest.raises`.
- `TestBroadcastSchema.test_body_too_long` (sync), lines 54?56: No function docstring; consult the source body and layer walkthrough.
  Calls: `BroadcastRequest`, `pytest.raises`.
- `TestBroadcastSchema.test_with_action_url` (sync), lines 58?65: No function docstring; consult the source body and layer walkthrough.
  Calls: `BroadcastRequest`.

## tests/unit/test_orders.py

139 lines; SHA-256 `0eae0187fc6a1a58348e5db0cb9424be8cb96803402ff98faa4f420b1b39c420`. [Open source](../../tests/unit/test_orders.py).

Backend imports: `app.schemas.order`.

- Class `TestShippingAddress`, lines 31?46; bases: .
- `TestShippingAddress.test_valid` (sync), lines 32?34: No function docstring; consult the source body and layer walkthrough.
  Calls: `ShippingAddressInput`.
- `TestShippingAddress.test_invalid_phone` (sync), lines 36?38: No function docstring; consult the source body and layer walkthrough.
  Calls: `ShippingAddressInput`, `pytest.raises`.
- `TestShippingAddress.test_phone_with_country_code` (sync), lines 40?42: No function docstring; consult the source body and layer walkthrough.
  Calls: `ShippingAddressInput`.
- `TestShippingAddress.test_short_street_rejected` (sync), lines 44?46: No function docstring; consult the source body and layer walkthrough.
  Calls: `ShippingAddressInput`, `pytest.raises`.
- Class `TestCreateOrderRequest`, lines 49?60; bases: .
- `TestCreateOrderRequest.test_valid_cod` (sync), lines 50?52: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateOrderRequest`.
- `TestCreateOrderRequest.test_valid_payfast` (sync), lines 54?56: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateOrderRequest`.
- `TestCreateOrderRequest.test_invalid_payment_method` (sync), lines 58?60: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateOrderRequest`, `pytest.raises`.
- Class `TestCreateGuestOrderRequest`, lines 63?87; bases: .
- `TestCreateGuestOrderRequest.test_valid_guest_order` (sync), lines 72?75: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateGuestOrderRequest`, `len`.
- `TestCreateGuestOrderRequest.test_empty_items_rejected` (sync), lines 77?79: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateGuestOrderRequest`, `pytest.raises`.
- `TestCreateGuestOrderRequest.test_invalid_guest_phone` (sync), lines 81?83: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateGuestOrderRequest`, `pytest.raises`.
- `TestCreateGuestOrderRequest.test_invalid_email` (sync), lines 85?87: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateGuestOrderRequest`, `pytest.raises`.
- Class `TestCartSchemas`, lines 90?111; bases: .
- `TestCartSchemas.test_add_to_cart_valid` (sync), lines 91?95: No function docstring; consult the source body and layer walkthrough.
  Calls: `AddToCartRequest`.
- `TestCartSchemas.test_add_to_cart_zero_rejected` (sync), lines 97?101: No function docstring; consult the source body and layer walkthrough.
  Calls: `AddToCartRequest`, `pytest.raises`.
- `TestCartSchemas.test_add_to_cart_over_limit` (sync), lines 103?107: No function docstring; consult the source body and layer walkthrough.
  Calls: `AddToCartRequest`, `pytest.raises`.
- `TestCartSchemas.test_update_cart_zero_allowed` (sync), lines 109?111: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateCartItemRequest`.
- Class `TestCouponValidation`, lines 114?121; bases: .
- `TestCouponValidation.test_valid` (sync), lines 115?117: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValidateCouponRequest`.
- `TestCouponValidation.test_zero_subtotal_rejected` (sync), lines 119?121: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValidateCouponRequest`, `pytest.raises`.
- Class `TestUpdateSellerOrderRequest`, lines 124?139; bases: .
- `TestUpdateSellerOrderRequest.test_shipped_requires_tracking` (sync), lines 125?127: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSellerOrderRequest`, `pytest.raises`.
- `TestUpdateSellerOrderRequest.test_shipped_with_tracking_ok` (sync), lines 129?131: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSellerOrderRequest`.
- `TestUpdateSellerOrderRequest.test_processing_no_tracking_ok` (sync), lines 133?135: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSellerOrderRequest`.
- `TestUpdateSellerOrderRequest.test_invalid_status` (sync), lines 137?139: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSellerOrderRequest`, `pytest.raises`.

## tests/unit/test_payments.py

235 lines; SHA-256 `e012967491863c58c5fe4e991d42e73b5d786267620ae64f5ab8b8c27a360b24`. [Open source](../../tests/unit/test_payments.py).

Backend imports: `app.integrations.payfast`, `app.schemas.payment`.

- Class `TestPaymentSchemas`, lines 13?36; bases: .
- `TestPaymentSchemas.test_initiate_valid` (sync), lines 14?16: No function docstring; consult the source body and layer walkthrough.
  Calls: `InitiatePaymentRequest`.
- `TestPaymentSchemas.test_retry_valid` (sync), lines 18?20: No function docstring; consult the source body and layer walkthrough.
  Calls: `RetryPaymentRequest`.
- `TestPaymentSchemas.test_retry_invalid_method` (sync), lines 22?24: No function docstring; consult the source body and layer walkthrough.
  Calls: `RetryPaymentRequest`, `pytest.raises`.
- `TestPaymentSchemas.test_refund_valid` (sync), lines 26?28: No function docstring; consult the source body and layer walkthrough.
  Calls: `RefundRequest`.
- `TestPaymentSchemas.test_refund_zero_amount` (sync), lines 30?32: No function docstring; consult the source body and layer walkthrough.
  Calls: `RefundRequest`, `pytest.raises`.
- `TestPaymentSchemas.test_refund_short_reason` (sync), lines 34?36: No function docstring; consult the source body and layer walkthrough.
  Calls: `RefundRequest`, `pytest.raises`.
- Class `TestPayFastHostedCheckout`, lines 39?235; bases: .
- `TestPayFastHostedCheckout.make_client` (sync), lines 40?56: No function docstring; consult the source body and layer walkthrough.
  Calls: `PayFastClient`, `httpx.AsyncClient`, `httpx.MockTransport`.
- `TestPayFastHostedCheckout.test_token_request_matches_documented_form_and_returns_token` (async), lines 59?85: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get_checkout_token`, `http.aclose`, `httpx.Response`, `parse_qs`, `requests.append`, `requests[0].content.decode`, `requests[0].url.path.endswith`, `self.make_client`.
- `TestPayFastHostedCheckout.test_token_request_matches_documented_form_and_returns_token.handler` (sync), lines 66?70: No function docstring; consult the source body and layer walkthrough.
  Calls: `httpx.Response`, `requests.append`.
- `TestPayFastHostedCheckout.test_token_response_rejects_merchant_mismatch_and_missing_token` (async), lines 88?106: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get_checkout_token`, `http.aclose`, `httpx.Response`, `iter`, `next`, `pytest.raises`, `self.make_client`.
- `TestPayFastHostedCheckout.test_checkout_payload_uses_documented_fields_without_secured_key` (sync), lines 108?151: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `asyncio.run`, `client.build_checkout_payload`, `client.checkout_url.endswith`, `date`, `http.aclose`, `httpx.Response`, `self.make_client`.
- `TestPayFastHostedCheckout.test_callback_verification_success_failure_and_tampering` (sync), lines 153?176: No function docstring; consult the source body and layer walkthrough.
  Calls: `asyncio.run`, `client.callback_hash`, `client.parse_callback`, `http.aclose`, `httpx.Response`, `pytest.raises`, `self.make_client`.
- `TestPayFastHostedCheckout.test_status_reconciliation_uses_bearer_token_and_basket_path` (async), lines 179?209: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.check_status`, `date`, `dict`, `http.aclose`, `httpx.Response`, `parse_qs`, `request.content.decode`, `request.url.path.endswith`, `requests.append`, `self.make_client`.
- `TestPayFastHostedCheckout.test_status_reconciliation_uses_bearer_token_and_basket_path.handler` (sync), lines 187?193: No function docstring; consult the source body and layer walkthrough.
  Calls: `httpx.Response`, `parse_qs`, `request.content.decode`, `request.url.path.endswith`, `requests.append`.
- `TestPayFastHostedCheckout.test_live_urls_and_invalid_amount` (sync), lines 211?235: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `__import__`, `__import__('datetime').date`, `asyncio.run`, `client.build_checkout_payload`, `http.aclose`, `httpx.Response`, `pytest.raises`, `self.make_client`.

## tests/unit/test_products.py

122 lines; SHA-256 `74dce0fdee0e0f5e6c27e72db40dd4f94fb049666ee9d00eba357acd5bdcb5ab`. [Open source](../../tests/unit/test_products.py).

Backend imports: `app.schemas.product`, `app.services.product_service`.

- Class `TestSlugify`, lines 30?41; bases: .
- `TestSlugify.test_basic` (sync), lines 31?32: No function docstring; consult the source body and layer walkthrough.
  Calls: `_slugify`.
- `TestSlugify.test_strips_non_ascii` (sync), lines 34?35: No function docstring; consult the source body and layer walkthrough.
  Calls: `_slugify`.
- `TestSlugify.test_max_length` (sync), lines 37?38: No function docstring; consult the source body and layer walkthrough.
  Calls: `_slugify`, `len`.
- `TestSlugify.test_numbers_preserved` (sync), lines 40?41: No function docstring; consult the source body and layer walkthrough.
  Calls: `_slugify`.
- Class `TestCreateProductSchema`, lines 44?82; bases: .
- `TestCreateProductSchema.test_valid_minimal` (sync), lines 45?49: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateProductRequest`.
- `TestCreateProductSchema.test_price_too_low` (sync), lines 51?53: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateProductRequest`, `pytest.raises`.
- `TestCreateProductSchema.test_price_too_high` (sync), lines 55?57: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateProductRequest`, `pytest.raises`.
- `TestCreateProductSchema.test_sale_price_must_be_less_than_price` (sync), lines 59?61: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateProductRequest`, `pytest.raises`.
- `TestCreateProductSchema.test_sale_price_equal_to_price_rejected` (sync), lines 63?65: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateProductRequest`, `pytest.raises`.
- `TestCreateProductSchema.test_valid_sale_price` (sync), lines 67?69: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateProductRequest`.
- `TestCreateProductSchema.test_name_too_short` (sync), lines 71?73: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateProductRequest`, `pytest.raises`.
- `TestCreateProductSchema.test_description_too_short` (sync), lines 75?77: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateProductRequest`, `pytest.raises`.
- `TestCreateProductSchema.test_with_variants` (sync), lines 79?82: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateProductRequest`, `len`.
- Class `TestCreateVariantSchema`, lines 85?108; bases: .
- `TestCreateVariantSchema.test_valid_alpha` (sync), lines 86?88: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateVariantRequest`.
- `TestCreateVariantSchema.test_valid_numeric` (sync), lines 90?92: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateVariantRequest`.
- `TestCreateVariantSchema.test_valid_one_size` (sync), lines 94?96: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateVariantRequest`.
- `TestCreateVariantSchema.test_invalid_size_type` (sync), lines 98?100: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateVariantRequest`, `pytest.raises`.
- `TestCreateVariantSchema.test_negative_stock_rejected` (sync), lines 102?104: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateVariantRequest`, `pytest.raises`.
- `TestCreateVariantSchema.test_price_override_too_low` (sync), lines 106?108: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateVariantRequest`, `pytest.raises`.
- Class `TestUpdateProductSchema`, lines 111?122; bases: .
- `TestUpdateProductSchema.test_empty_rejected` (sync), lines 112?114: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateProductRequest`, `pytest.raises`.
- `TestUpdateProductSchema.test_single_field_ok` (sync), lines 116?118: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateProductRequest`.
- `TestUpdateProductSchema.test_price_validation` (sync), lines 120?122: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateProductRequest`, `pytest.raises`.

## tests/unit/test_release_core.py

122 lines; SHA-256 `a739f93e238fa67f5bb4d01c0133b8b6d31913101b7e295dbc1fba3e2df8d086`. [Open source](../../tests/unit/test_release_core.py).

Backend imports: `app.core`, `app.core.config`, `app.core.exceptions`, `app.core.logging`, `app.services.image_service`.

- `test_cache_round_trip_expiry_and_scoped_invalidation` (async), lines 14?24: No function docstring; consult the source body and layer walkthrough.
  Calls: `isolated_redis.ttl`, `redis.cache_delete`, `redis.cache_delete_pattern`, `redis.cache_get`, `redis.cache_set`.
  Mutation/I-O-related call names: `redis.cache_delete`, `redis.cache_delete_pattern`.
- `test_cache_outage_is_nonfatal` (async), lines 27?34: No function docstring; consult the source body and layer walkthrough.
  Calls: `monkeypatch.setattr`, `pytest.raises`, `redis.cache_delete`, `redis.cache_delete_pattern`, `redis.cache_get`, `redis.cache_set`, `redis.get_redis`.
  Mutation/I-O-related call names: `redis.cache_delete`, `redis.cache_delete_pattern`.
- `test_request_session_rolls_back_and_closes` (async), lines 37?47: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `ValueError`, `anext`, `database._json_deserializer`, `database._json_serializer`, `database.get_db`, `dependency.athrow`, `monkeypatch.setattr`, `pytest.raises`, `session.close.assert_awaited_once`, `session.rollback.assert_awaited_once`.
  Mutation/I-O-related call names: `session.rollback.assert_awaited_once`.
- `test_database_initialization_failure_disposes_on_close` (async), lines 50?59: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `ConnectionError`, `MagicMock`, `database.close_db`, `database.init_db`, `engine.dispose.assert_awaited_once`, `monkeypatch.setattr`, `pytest.raises`.
- `test_redis_initialization_failure_and_cleanup` (async), lines 62?69: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `ConnectionError`, `client.aclose.assert_awaited_once`, `monkeypatch.setattr`, `pytest.raises`, `redis.close_redis`, `redis.init_redis`.
- `test_image_conversion_and_delete_boundaries` (async), lines 72?85: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `Image.new`, `Image.new('L', (8, 8), 100).save`, `ImageService`, `data.getvalue`, `delete.assert_awaited_once_with`, `delete.assert_not_awaited`, `io.BytesIO`, `monkeypatch.setattr`, `pytest.raises`, `service.delete`, `service.storage.get_public_url` ? (14 distinct call expressions).
  Mutation/I-O-related call names: `delete.assert_awaited_once_with`, `delete.assert_not_awaited`, `service.delete`.
- `test_log_scrubber_redacts_credentials` (sync), lines 88?94: No function docstring; consult the source body and layer walkthrough.
  Calls: `_scrub_sensitive`.
- `test_structured_logging_configuration_restores_host_logging` (sync), lines 97?122: No function docstring; consult the source body and layer walkthrough.
  Calls: `configure_logging`, `get_logger`, `get_logger('release-test').info`, `logging.getLogger`, `logging.getLogger(name).setLevel`, `monkeypatch.setattr`, `named_levels.items`, `structlog.configure`, `structlog.get_config`, `structlog.get_config().copy`.

## tests/unit/test_repository_utilities.py

21 lines; SHA-256 `2ff6cae6884b9676c5ef6f9ba77d3e248dfa2d0a1acf72fe882a3ac85828482c`. [Open source](../../tests/unit/test_repository_utilities.py).

- `test_migration_helper_defaults_to_read_only` (sync), lines 7?13: No function docstring; consult the source body and layer walkthrough.
  Calls: `Mock`, `current.assert_called_once`, `fix_migration.main`, `monkeypatch.setattr`, `upgrade.assert_not_called`.
- `test_migration_upgrade_requires_explicit_option` (sync), lines 16?21: No function docstring; consult the source body and layer walkthrough.
  Calls: `Mock`, `fix_migration.main`, `monkeypatch.setattr`.

## tests/unit/test_returns.py

101 lines; SHA-256 `2e60907e60f2836be784625b1615da920325a94ebdd9aadc9385b6282196f7a2`. [Open source](../../tests/unit/test_returns.py).

Backend imports: `app.schemas.return_`.

- Class `TestCreateReturnSchema`, lines 21?49; bases: .
- `TestCreateReturnSchema.test_valid` (sync), lines 22?24: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateReturnRequest`, `len`.
- `TestCreateReturnSchema.test_reason_too_short` (sync), lines 26?28: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateReturnRequest`, `pytest.raises`.
- `TestCreateReturnSchema.test_empty_items_rejected` (sync), lines 30?32: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateReturnRequest`, `pytest.raises`.
- `TestCreateReturnSchema.test_zero_quantity_rejected` (sync), lines 34?39: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateReturnRequest`, `pytest.raises`.
- `TestCreateReturnSchema.test_multiple_items` (sync), lines 41?49: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateReturnRequest`, `len`.
- Class `TestDisputeSchemas`, lines 52?67; bases: .
- `TestDisputeSchemas.test_open_dispute_valid` (sync), lines 53?55: No function docstring; consult the source body and layer walkthrough.
  Calls: `OpenDisputeRequest`, `len`.
- `TestDisputeSchemas.test_open_dispute_too_short` (sync), lines 57?59: No function docstring; consult the source body and layer walkthrough.
  Calls: `OpenDisputeRequest`, `pytest.raises`.
- `TestDisputeSchemas.test_add_message_valid` (sync), lines 61?63: No function docstring; consult the source body and layer walkthrough.
  Calls: `AddDisputeMessageRequest`.
- `TestDisputeSchemas.test_add_message_empty` (sync), lines 65?67: No function docstring; consult the source body and layer walkthrough.
  Calls: `AddDisputeMessageRequest`, `pytest.raises`.
- Class `TestResolveDisputeSchema`, lines 70?91; bases: .
- `TestResolveDisputeSchema.test_in_favor_customer` (sync), lines 71?76: No function docstring; consult the source body and layer walkthrough.
  Calls: `ResolveDisputeRequest`.
- `TestResolveDisputeSchema.test_in_favor_seller` (sync), lines 78?83: No function docstring; consult the source body and layer walkthrough.
  Calls: `ResolveDisputeRequest`.
- `TestResolveDisputeSchema.test_invalid_in_favor_of` (sync), lines 85?87: No function docstring; consult the source body and layer walkthrough.
  Calls: `ResolveDisputeRequest`, `pytest.raises`.
- `TestResolveDisputeSchema.test_short_resolution_note` (sync), lines 89?91: No function docstring; consult the source body and layer walkthrough.
  Calls: `ResolveDisputeRequest`, `pytest.raises`.
- Class `TestAdminReturnSchema`, lines 94?101; bases: .
- `TestAdminReturnSchema.test_no_note_ok` (sync), lines 95?97: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminReturnActionRequest`.
- `TestAdminReturnSchema.test_with_note` (sync), lines 99?101: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminReturnActionRequest`.

## tests/unit/test_schema_validators.py

168 lines; SHA-256 `7935fc9e7e5d0bf093fc5d0ab1249eee242e3725f812e0039ae0e9467e311dec`. [Open source](../../tests/unit/test_schema_validators.py).

Backend imports: `app.schemas`.

- `test_password_policy` (sync), lines 35?41: No function docstring; consult the source body and layer walkthrough.
  Calls: `getattr`, `model`, `pytest.mark.parametrize`, `pytest.raises`.
- `test_registration_rejects_invalid_email` (sync), lines 54?56: No function docstring; consult the source body and layer walkthrough.
  Calls: `auth.RegisterRequest`, `pytest.mark.parametrize`, `pytest.raises`.
- `test_registration_normalization` (sync), lines 69?73: No function docstring; consult the source body and layer walkthrough.
  Calls: `auth.RegisterRequest`, `pytest.mark.parametrize`.
- `test_registration_invalid_fields` (sync), lines 79?81: No function docstring; consult the source body and layer walkthrough.
  Calls: `auth.RegisterRequest`, `pytest.mark.parametrize`, `pytest.raises`.
- `test_totp_format` (sync), lines 87?92: No function docstring; consult the source body and layer walkthrough.
  Calls: `auth.VerifyTOTPRequest`, `pytest.mark.parametrize`, `pytest.raises`.
- `test_password_confirmation_and_email_normalization` (sync), lines 95?103: No function docstring; consult the source body and layer walkthrough.
  Calls: `auth.ChangePasswordRequest`, `auth.ForgotPasswordRequest`, `auth.LoginRequest`, `pytest.raises`, `user.ChangePasswordRequest`.
- `test_profile_invalid_fields` (sync), lines 110?112: No function docstring; consult the source body and layer walkthrough.
  Calls: `pytest.mark.parametrize`, `pytest.raises`, `user.UpdateProfileRequest`.
- `test_profile_optional_and_valid_fields` (sync), lines 115?118: No function docstring; consult the source body and layer walkthrough.
  Calls: `user.UpdateProfileRequest`.
- `test_address_limits` (sync), lines 131?135: No function docstring; consult the source body and layer walkthrough.
  Calls: `pytest.mark.parametrize`, `pytest.raises`, `user.CreateAddressRequest`.
- `test_address_normalization_and_optional_label` (sync), lines 138?143: No function docstring; consult the source body and layer walkthrough.
  Calls: `user.CreateAddressRequest`, `value.model_dump`.
- `test_review_limits` (sync), lines 149?151: No function docstring; consult the source body and layer walkthrough.
  Calls: `pytest.mark.parametrize`, `pytest.raises`, `user.CreateReviewRequest`, `uuid4`.
- `test_review_normalization_and_deletion_confirmation` (sync), lines 154?168: No function docstring; consult the source body and layer walkthrough.
  Calls: `pytest.raises`, `user.CreateReviewRequest`, `user.DeleteAccountRequest`, `user.UpdateReviewRequest`, `uuid4`.

## tests/unit/test_security.py

121 lines; SHA-256 `cd0d4cf69dbe2ba08ffd39383f5488f7fc159eabdf053f4fcfa1510e51c0dffb`. [Open source](../../tests/unit/test_security.py).

Backend imports: `app.core`, `app.core.config`.

- `rsa_keys` (sync), lines 15?32: No function docstring; consult the source body and layer walkthrough.
  Calls: `monkeypatch.setattr`, `private_key.private_bytes`, `private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode`, `private_key.public_key`, `private_key.public_key().public_bytes`, `private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode`, `rsa.generate_private_key`, `serialization.NoEncryption`.
- `test_password_hash_and_verify` (sync), lines 36?43: No function docstring; consult the source body and layer walkthrough.
  Calls: `hashed.startswith`, `security.hash_password`, `security.verify_password`.
- `test_refresh_token_generation_and_hashing` (sync), lines 47?55: No function docstring; consult the source body and layer walkthrough.
  Calls: `len`, `security.generate_refresh_token`, `security.hash_refresh_token`.
- `test_rs256_access_token_encode_decode` (sync), lines 59?73: No function docstring; consult the source body and layer walkthrough.
  Calls: `security.create_access_token`, `security.decode_access_token`.
- `test_email_verification_token` (sync), lines 77?83: No function docstring; consult the source body and layer walkthrough.
  Calls: `security.create_email_verify_token`, `security.decode_email_verify_token`.
- `test_password_reset_token` (sync), lines 87?93: No function docstring; consult the source body and layer walkthrough.
  Calls: `security.create_password_reset_token`, `security.decode_password_reset_token`.
- `test_totp_generation_and_verification` (sync), lines 97?102: No function docstring; consult the source body and layer walkthrough.
  Calls: `len`, `pyotp.TOTP`, `pyotp.TOTP(secret).now`, `security.generate_totp_secret`, `security.verify_totp`.
- `test_invalid_totp_raises` (sync), lines 106?110: No function docstring; consult the source body and layer walkthrough.
  Calls: `pytest.raises`, `security.generate_totp_secret`, `security.verify_totp`.
- `test_refresh_cookie_parameters` (sync), lines 114?121: No function docstring; consult the source body and layer walkthrough.
  Calls: `security.get_cookie_params`.

## tests/unit/test_sellers.py

156 lines; SHA-256 `3837e122ae3b601ea08312a2456c79201a540f13002f7d790cf5e5d33344cee2`. [Open source](../../tests/unit/test_sellers.py).

Backend imports: `app.schemas.seller`, `app.services.seller_service`, `app.services.slot_service`.

- Class `TestSlotPricing`, lines 31?50; bases: .
- `TestSlotPricing.test_zero_extra` (sync), lines 32?36: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`.
- `TestSlotPricing.test_ten_extra` (sync), lines 38?42: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`.
- `TestSlotPricing.test_hundred_extra` (sync), lines 44?47: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`.
- `TestSlotPricing.test_price_per_slot_is_fifty` (sync), lines 49?50: No function docstring; consult the source body and layer walkthrough.
- Class `TestSlugify`, lines 53?64; bases: .
- `TestSlugify.test_basic` (sync), lines 54?55: No function docstring; consult the source body and layer walkthrough.
  Calls: `_slugify`.
- `TestSlugify.test_strips_non_ascii` (sync), lines 57?58: No function docstring; consult the source body and layer walkthrough.
  Calls: `_slugify`.
- `TestSlugify.test_underscores_become_dashes` (sync), lines 60?61: No function docstring; consult the source body and layer walkthrough.
  Calls: `_slugify`.
- `TestSlugify.test_max_length` (sync), lines 63?64: No function docstring; consult the source body and layer walkthrough.
  Calls: `_slugify`, `len`.
- Class `TestSellerRegistrationSchema`, lines 67?94; bases: .
- `TestSellerRegistrationSchema.test_valid` (sync), lines 68?70: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerRegistrationRequest`.
- `TestSellerRegistrationSchema.test_invalid_phone` (sync), lines 72?74: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerRegistrationRequest`, `pytest.raises`.
- `TestSellerRegistrationSchema.test_phone_with_country_code` (sync), lines 76?78: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerRegistrationRequest`.
- `TestSellerRegistrationSchema.test_password_no_uppercase` (sync), lines 80?82: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerRegistrationRequest`, `pytest.raises`.
- `TestSellerRegistrationSchema.test_password_no_digit` (sync), lines 84?86: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerRegistrationRequest`, `pytest.raises`.
- `TestSellerRegistrationSchema.test_negative_extra_slots` (sync), lines 88?90: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerRegistrationRequest`, `pytest.raises`.
- `TestSellerRegistrationSchema.test_description_too_short` (sync), lines 92?94: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerRegistrationRequest`, `pytest.raises`.
- Class `TestSlotPurchaseSchema`, lines 97?108; bases: .
- `TestSlotPurchaseSchema.test_valid` (sync), lines 98?100: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`.
- `TestSlotPurchaseSchema.test_zero_quantity_rejected` (sync), lines 102?104: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`, `pytest.raises`.
- `TestSlotPurchaseSchema.test_invalid_payment_method` (sync), lines 106?108: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`, `pytest.raises`.
- Class `TestProfileUpdateSchema`, lines 111?126; bases: .
- `TestProfileUpdateSchema.test_empty_rejected` (sync), lines 112?114: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerProfileUpdateRequest`, `pytest.raises`.
- `TestProfileUpdateSchema.test_single_field_ok` (sync), lines 116?118: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerProfileUpdateRequest`.
- `TestProfileUpdateSchema.test_bad_hex_color` (sync), lines 120?122: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerProfileUpdateRequest`, `pytest.raises`.
- `TestProfileUpdateSchema.test_valid_hex_color` (sync), lines 124?126: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerProfileUpdateRequest`.
- Class `TestBankAccountSchema`, lines 129?142; bases: .
- `TestBankAccountSchema.test_empty_rejected` (sync), lines 130?135: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateBankAccountRequest`, `pytest.raises`.
- `TestBankAccountSchema.test_bank_fields_ok` (sync), lines 137?142: No function docstring; consult the source body and layer walkthrough.
  Calls: `CreateBankAccountRequest`.
- Class `TestOrderStatusSchema`, lines 145?156; bases: .
- `TestOrderStatusSchema.test_shipped_without_tracking_rejected` (sync), lines 146?148: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateOrderStatusRequest`, `pytest.raises`.
- `TestOrderStatusSchema.test_shipped_with_tracking_ok` (sync), lines 150?152: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateOrderStatusRequest`.
- `TestOrderStatusSchema.test_processing_no_tracking_ok` (sync), lines 154?156: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateOrderStatusRequest`.

## tests/unit/test_slot_service.py

239 lines; SHA-256 `2a73ce657010f47d9654a86a890ce72e977309f90d2b2c2cbcfcb81a939b7daa`. [Open source](../../tests/unit/test_slot_service.py).

Backend imports: `app.core.exceptions`, `app.models.seller`, `app.schemas.seller`, `app.services.slot_service`.

- Class `TestSlotConstants`, lines 36?44; bases: .
- `TestSlotConstants.test_registration_fee_is_5000` (sync), lines 37?38: No function docstring; consult the source body and layer walkthrough.
- `TestSlotConstants.test_base_slots_is_50` (sync), lines 40?41: No function docstring; consult the source body and layer walkthrough.
- `TestSlotConstants.test_extra_slot_price_is_50` (sync), lines 43?44: No function docstring; consult the source body and layer walkthrough.
- Class `TestSlotPricing`, lines 51?100; bases: .
- `TestSlotPricing.test_zero_extra_slots` (sync), lines 52?58: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`.
- `TestSlotPricing.test_one_extra_slot` (sync), lines 60?64: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`.
- `TestSlotPricing.test_ten_extra_slots` (sync), lines 66?70: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`.
- `TestSlotPricing.test_hundred_extra_slots` (sync), lines 72?75: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`.
- `TestSlotPricing.test_ten_thousand_extra_slots` (sync), lines 77?80: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`.
- `TestSlotPricing.test_returns_pricing_response_type` (sync), lines 82?84: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`, `isinstance`.
- `TestSlotPricing.test_total_cost_formula` (sync), lines 87?90: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`, `pytest.mark.parametrize`.
- `TestSlotPricing.test_total_slots_formula` (sync), lines 93?95: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService.calculate_pricing`, `pytest.mark.parametrize`.
- `TestSlotPricing.test_base_slots_always_included` (sync), lines 97?100: Even with 0 extra, seller gets BASE_SLOTS.
  Calls: `SlotService.calculate_pricing`.
- Class `TestSlotPurchaseRequestSchema`, lines 107?135; bases: .
- `TestSlotPurchaseRequestSchema.test_valid_wallet_payment` (sync), lines 108?111: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`.
- `TestSlotPurchaseRequestSchema.test_retired_gateway_rejected` (sync), lines 113?115: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`, `pytest.raises`.
- `TestSlotPurchaseRequestSchema.test_zero_quantity_rejected` (sync), lines 117?119: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`, `pytest.raises`.
- `TestSlotPurchaseRequestSchema.test_negative_quantity_rejected` (sync), lines 121?123: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`, `pytest.raises`.
- `TestSlotPurchaseRequestSchema.test_invalid_payment_method_rejected` (sync), lines 125?127: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`, `pytest.raises`.
- `TestSlotPurchaseRequestSchema.test_quantity_above_max_rejected` (sync), lines 129?131: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`, `pytest.raises`.
- `TestSlotPurchaseRequestSchema.test_quantity_one_is_valid` (sync), lines 133?135: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`.
- `_mock_service` (sync), lines 142?170: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `Decimal`, `MagicMock`, `SlotService`, `uuid4`.
- Class `TestSlotPurchaseFlow`, lines 173?215; bases: .
- `TestSlotPurchaseFlow.test_inactive_seller_raises_permission_error` (async), lines 175?182: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`, `_mock_service`, `pytest.raises`, `svc.purchase_slots`, `uuid4`.
- `TestSlotPurchaseFlow.test_suspended_seller_raises_permission_error` (async), lines 185?192: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPurchaseRequest`, `_mock_service`, `pytest.raises`, `svc.purchase_slots`, `uuid4`.
- `TestSlotPurchaseFlow.test_insufficient_wallet_balance_raises` (async), lines 195?202: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `SlotPurchaseRequest`, `_mock_service`, `pytest.raises`, `svc.purchase_slots`, `uuid4`.
- `TestSlotPurchaseFlow.test_seller_not_found_raises` (async), lines 205?215: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `SlotPurchaseRequest`, `SlotService`, `pytest.raises`, `svc.purchase_slots`, `uuid4`.
- Class `TestSlotCostInvariants`, lines 222?239; bases: .
- `TestSlotCostInvariants.test_wallet_debit_equals_quantity_times_price` (sync), lines 224?228: The debit amount must exactly equal qty × EXTRA_SLOT_PRICE.
  Calls: `Decimal`, `SlotService.calculate_pricing`, `pytest.mark.parametrize`, `str`.
- `TestSlotCostInvariants.test_no_free_slots_beyond_base` (sync), lines 230?233: Extra slots always cost money; there is no free tier above BASE_SLOTS.
  Calls: `SlotService.calculate_pricing`.
- `TestSlotCostInvariants.test_registration_fee_constant_regardless_of_extra_slots` (sync), lines 235?239: The registration_fee field is always REGISTRATION_FEE, regardless of extras.
  Calls: `SlotService.calculate_pricing`.

## tests/unit/test_task_dispatch.py

233 lines; SHA-256 `f29ab1dbd370801f0549ee167043c5dd636c6fbc650e0b40d39186075736adb7`. [Open source](../../tests/unit/test_task_dispatch.py).

Backend imports: `app.core`, `app.core.config`, `app.integrations.supabase_storage`, `app.services.notification_service`, `app.tasks`.

- `worker_db` (sync), lines 15?22: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `MagicMock`, `monkeypatch.setattr`.
- `test_email_delivery_retries_failures` (async), lines 49?59: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `getattr`, `monkeypatch.setattr`, `pytest.mark.parametrize`, `pytest.raises`, `run`, `sender.assert_awaited_once_with`.
  Mutation/I-O-related call names: `sender.assert_awaited_once_with`.
- `test_worker_session_requires_startup` (sync), lines 62?65: No function docstring; consult the source body and layer walkthrough.
  Calls: `database.AsyncSessionLocal`, `monkeypatch.setattr`, `pytest.raises`.
- `test_worker_session_uses_live_factory_and_shutdown_clears_it` (async), lines 68?75: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `database.AsyncSessionLocal`, `database.close_db`, `engine.dispose.assert_awaited_once`, `monkeypatch.setattr`, `pytest.raises`.
- `test_worker_startup_shutdown` (async), lines 78?95: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `callback.assert_awaited_once`, `callbacks.append`, `monkeypatch.setattr`, `worker.shutdown`, `worker.startup`.
- `test_cart_cleanup_preserves_live_ttl` (async), lines 98?105: No function docstring; consult the source body and layer walkthrough.
  Calls: `cleanup_tasks.cleanup_abandoned_carts`, `isolated_redis.set`, `isolated_redis.ttl`.
- `test_reset_cleanup_prunes_only_missing_tokens` (async), lines 108?112: No function docstring; consult the source body and layer walkthrough.
  Calls: `cleanup_tasks.cleanup_expired_reset_tokens`, `isolated_redis.sadd`, `isolated_redis.set`, `isolated_redis.smembers`.
- `test_database_cleanup_commits` (async), lines 118?121: No function docstring; consult the source body and layer walkthrough.
  Calls: `getattr`, `getattr(cleanup_tasks, task)`, `pytest.mark.parametrize`, `worker_db.commit.assert_awaited_once`, `worker_db.execute.assert_awaited_once`.
  Mutation/I-O-related call names: `worker_db.commit.assert_awaited_once`.
- `test_orphan_cleanup_retains_recent_and_referenced_files` (async), lines 124?153: No function docstring; consult the source body and layer walkthrough.
  Calls: `(now - timedelta(days=2)).isoformat`, `AsyncMock`, `SimpleNamespace`, `cleanup_tasks.cleanup_orphaned_images`, `datetime.now`, `delete.assert_awaited_once_with`, `monkeypatch.setattr`, `now.isoformat`, `timedelta`.
  Mutation/I-O-related call names: `delete.assert_awaited_once_with`.
- `test_orphan_cleanup_skips_unverifiable_timestamps` (async), lines 156?181: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `SimpleNamespace`, `cleanup_tasks.cleanup_orphaned_images`, `delete.assert_not_awaited`, `monkeypatch.setattr`, `range`.
  Mutation/I-O-related call names: `delete.assert_not_awaited`.
- `test_notification_tasks_retry_failures` (async), lines 209?219: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncMock`, `RuntimeError`, `getattr`, `getattr(notification_tasks, task_name)`, `monkeypatch.setattr`, `pytest.mark.parametrize`, `pytest.raises`.
- `test_broadcast_task_rolls_back_and_retries` (async), lines 222?233: No function docstring; consult the source body and layer walkthrough.
  Calls: `RuntimeError`, `notification_tasks.broadcast_notification`, `pytest.raises`, `worker_db.rollback.assert_awaited_once`.
  Mutation/I-O-related call names: `worker_db.rollback.assert_awaited_once`.

## tests/unit/test_wallet.py

60 lines; SHA-256 `c5b996632a957db7b615a1eef67adaa8e3a036e963f963854e6cf3917d53b533`. [Open source](../../tests/unit/test_wallet.py).

Backend imports: `app.schemas.wallet`, `app.services.commission_service`.

- Class `TestCommissionMath`, lines 10?26; bases: .
- `TestCommissionMath.test_rate_is_fifteen_percent` (sync), lines 11?12: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`.
- `TestCommissionMath.test_seller_gets_85_percent` (sync), lines 14?19: No function docstring; consult the source body and layer walkthrough.
  Calls: `(gross * COMMISSION_RATE).quantize`, `Decimal`.
- `TestCommissionMath.test_commission_plus_seller_equals_gross` (sync), lines 21?26: No function docstring; consult the source body and layer walkthrough.
  Calls: `(g * COMMISSION_RATE).quantize`, `Decimal`.
- Class `TestWithdrawalSchema`, lines 29?50; bases: .
- `TestWithdrawalSchema.test_valid_minimum` (sync), lines 32?34: No function docstring; consult the source body and layer walkthrough.
  Calls: `WithdrawalRequest`.
- `TestWithdrawalSchema.test_valid_large` (sync), lines 36?38: No function docstring; consult the source body and layer walkthrough.
  Calls: `WithdrawalRequest`.
- `TestWithdrawalSchema.test_below_minimum_rejected` (sync), lines 40?42: No function docstring; consult the source body and layer walkthrough.
  Calls: `WithdrawalRequest`, `pytest.raises`.
- `TestWithdrawalSchema.test_above_maximum_rejected` (sync), lines 44?46: No function docstring; consult the source body and layer walkthrough.
  Calls: `WithdrawalRequest`, `pytest.raises`.
- `TestWithdrawalSchema.test_zero_rejected` (sync), lines 48?50: No function docstring; consult the source body and layer walkthrough.
  Calls: `WithdrawalRequest`, `pytest.raises`.
- Class `TestAdminPayoutSchema`, lines 53?60; bases: .
- `TestAdminPayoutSchema.test_valid_with_note` (sync), lines 54?56: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminPayoutActionRequest`.
- `TestAdminPayoutSchema.test_valid_no_note` (sync), lines 58?60: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminPayoutActionRequest`.



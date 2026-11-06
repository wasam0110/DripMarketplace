# Graph Report - MultiMarket  (2026-11-06)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 5952 nodes · 20976 edges · 213 communities (133 shown, 80 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2744 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `495315e1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 141
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 163
- Community 164
- Community 166
- Community 167
- Community 169
- Community 171
- Community 172
- Community 179
- Community 180
- Community 181
- Community 182
- Community 196
- Community 200
- Community 201
- Community 202
- Community 203
- Community 205
- Community 207

## God Nodes (most connected - your core abstractions)
1. `BusinessRuleError` - 233 edges
2. `ErrorNotice()` - 184 edges
3. `Button()` - 171 edges
4. `OrderService` - 166 edges
5. `NotFoundError` - 154 edges
6. `PaymentService` - 147 edges
7. `Order` - 137 edges
8. `CustomerService` - 137 edges
9. `ReturnService` - 134 edges
10. `AdminService` - 124 edges

## Surprising Connections (you probably didn't know these)
- `test_policy_defaults_compatibility_aliases_and_sql_constraints()` --uses--> `Product`  [INFERRED]
  drip-backend/tests/unit/test_catalogue_policy.py → drip-backend/app/models/product.py
- `test_user_repository_state_changes_and_invalid_fields()` --uses--> `UserRepository`  [INFERRED]
  drip-backend/tests/integration/test_release_journeys.py → drip-backend/app/repositories/user_repo.py
- `test_development_health_schema_preserves_degraded_response()` --uses--> `ErrorResponse`  [INFERRED]
  drip-backend/tests/unit/test_error_contract.py → drip-backend/app/schemas/common.py
- `session()` --indirect_call--> `useAuth()`  [INFERRED]
  drip-frontend/src/admin/AdminOrdersPage.test.tsx → drip-frontend/src/auth/AuthProvider.tsx
- `session()` --indirect_call--> `useAuth()`  [INFERRED]
  drip-frontend/src/admin/AdminRefundsPage.test.tsx → drip-frontend/src/auth/AuthProvider.tsx

## Import Cycles
- None detected.

## Communities (213 total, 80 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (95): PayFastClient, Payment, PaymentCallback, PaymentStatus, Refund, Return, ReturnItem, ReturnStatus (+87 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (62): upgrade(), upgrade(), upgrade(), upgrade(), SystemSetting, AuditMixin, Base, SoftDeleteMixin (+54 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (139): ChangePasswordPage(), empty, PasswordForm(), submit(), DeleteAccountPage(), PasswordChange, valid, validatePasswordChange() (+131 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (86): cancel_order(), get_order(), get_order_by_number(), _get_redis(), get_seller_order(), list_orders(), list_seller_orders(), place_guest_order() (+78 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (36): admin_dashboard(), admin_order_detail(), list_all_orders(), get_settings(), update_settings(), OrderStatus, OrderStatusHistory, SellerOrderStatus (+28 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (33): require_customer(), health_check(), atomic(), create_engine_and_session(), get_db(), _json_deserializer(), _json_serializer(), error_response() (+25 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (58): assert_owns_resource(), assert_owns_seller_resource(), _extract_token(), get_current_user_payload(), get_optional_user_payload(), require_admin(), require_seller(), require_seller_account() (+50 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (86): useAccountWrite(), WriteFeedback(), AvatarProfile, MAX_AVATAR_BYTES, safeAvatarUrl(), validateAvatarDimensions(), validateAvatarFile(), validateAvatarProfile() (+78 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (68): review(), state(), test_decision_is_once_and_keeps_money_and_physical_stock(), test_expired_is_visible_cancel_only(), test_expiry_worker_releases_once(), test_inconsistent_release_rolls_back(), test_outbox_failure_rolls_back_all_changes(), test_permissions() (+60 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (45): AsyncSessionLocal(), close_db(), init_db(), close_redis(), init_redis(), NotifType, cleanup_abandoned_carts(), cleanup_expired_reset_tokens() (+37 more)

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (62): AccountGate(), useOrderAccess(), integer(), isOrderId(), labels, OrderDetail, OrderItem, OrderList (+54 more)

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (64): AddressesPage(), AddressForm(), AddressManager(), refresh(), save(), ProfileForm(), ProfileManager(), ProfilePage() (+56 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (26): _format_amount(), PayFastProtocolError, InitiatePaymentRequest, RetryPaymentRequest, callback(), evidence(), fail(), rig() (+18 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (19): add_to_cart(), clear_cart(), get_cart(), _get_redis(), remove_cart_item(), sync_cart(), update_cart_item(), AddToCartRequest (+11 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (64): AdminReturnsPage(), CaseFeedback(), DisputeForm(), DisputeManager(), save(), Queue(), ReturnForm(), ReturnManager() (+56 more)

### Community 15 - "Community 15"
Cohesion: 0.07
Nodes (51): Order, OrderAddress, OrderItem, SellerOrder, snapshot(), address(), at(), fractional() (+43 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (32): MoneyDisplayValue, api_url(), _build_url(), frontend_url(), normalize_origin(), _base_template(), _configure_resend(), send_cod_timeout_email() (+24 more)

### Community 18 - "Community 18"
Cohesion: 0.08
Nodes (61): DeletionForm(), Accounting(), accountingLabels, AdminRefundsPage(), ConfirmForm(), Money(), PaymentRefunds(), save() (+53 more)

### Community 19 - "Community 19"
Cohesion: 0.09
Nodes (61): ActionForm(), Inspection(), save(), PayoutList(), Results(), AdminPayout, allowed(), confirmPayout() (+53 more)

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (6): UserSession, BaseRepository, AddressRepository, SessionRepository, UserRepository, test_late_authentication_writes_cannot_restore_deleted_credentials()

### Community 21 - "Community 21"
Cohesion: 0.08
Nodes (16): SellerBankAccount, Payout, PayoutStatus, PayoutRepository, PayoutReview, WalletService, test_independent_sessions_cannot_double_release_or_complete(), decide() (+8 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (18): test_reviewed_return_lifecycle(), admin_requests(), error(), payload(), request_return(), requested(), snapshot(), test_admin_endpoints_reject_non_admin_roles() (+10 more)

### Community 23 - "Community 23"
Cohesion: 0.05
Nodes (5): row, initial, product, @axe-core/playwright, @playwright/test

### Community 24 - "Community 24"
Cohesion: 0.06
Nodes (19): redact(), safe_exception(), scrub_sentry_event(), lifespan(), main(), dependencies(), main(), selected_files() (+11 more)

### Community 25 - "Community 25"
Cohesion: 0.08
Nodes (25): delete_review_photo(), get_review_photos(), upload_review_photo(), NotFoundError, ReviewImage, ReviewStatus, ReviewResponse, queue_photo_cleanup() (+17 more)

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (48): AdminCODPage(), CODCard(), CODForm(), CODList(), CODReview(), refresh(), save(), page() (+40 more)

### Community 27 - "Community 27"
Cohesion: 0.09
Nodes (21): add_to_wishlist(), change_password(), create_address(), create_review(), delete_account(), delete_address(), delete_review(), get_notification_preferences() (+13 more)

### Community 28 - "Community 28"
Cohesion: 0.10
Nodes (47): BannerCard(), BannerForm(), choose(), BannerManager(), refresh(), save(), ProductList(), ProductResults() (+39 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (6): Dispute, DisputeStatus, DisputeRepository, DisputeDetailResponse, DisputeMessageResponse, test_seller_win_keeps_return_rejected_and_creates_no_refund()

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (10): AdminReturnActionRequest, ReturnService, _received_return(), test_return_refund_failure_before_outer_commit_leaves_no_orphan(), test_return_refund_is_created_with_its_return_link(), test_customer_win_reopens_return_and_completes_manual_refund_journey(), _request_single_item_return(), test_admin_return_detail_tracks_actions_and_linked_refund() (+2 more)

### Community 31 - "Community 31"
Cohesion: 0.06
Nodes (7): AdminUser, BrowseUser, CustomerUser, on_test_start(), on_test_stop(), _rnd(), SellerUser

### Community 32 - "Community 32"
Cohesion: 0.07
Nodes (21): StorageError, SupabaseStorage, Category, AssetCleanupReviewRequiredError, cleanup_deleted_customer(), cleanup_review_photo(), review_photo_path(), cleanup_orphaned_images() (+13 more)

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (25): change_password(), _clear_refresh_cookie(), forgot_password(), _get_ip(), get_me(), google_login(), login(), logout() (+17 more)

### Community 34 - "Community 34"
Cohesion: 0.09
Nodes (38): Cart, CheckoutQuote, CouponPreview, previewTotal(), quote, validateQuote(), checkoutRequest(), OrderPayload (+30 more)

### Community 35 - "Community 35"
Cohesion: 0.06
Nodes (14): configure_logging(), get_logger(), _scrub_sensitive(), SecurityHeadersMiddleware, cache_delete(), cache_delete_pattern(), cache_get(), cache_set() (+6 more)

### Community 36 - "Community 36"
Cohesion: 0.08
Nodes (26): ResendClient, EmailLog, authorized_order(), create_guest_token(), guest_token_matches(), cod(), collected_order(), _session_context() (+18 more)

### Community 37 - "Community 37"
Cohesion: 0.05
Nodes (44): name, postgres, PGADMIN_DEFAULT_EMAIL, PGADMIN_DEFAULT_PASSWORD, PGADMIN_LISTEN_PORT, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER (+36 more)

### Community 38 - "Community 38"
Cohesion: 0.09
Nodes (15): refresh(), setup_2fa(), DuplicateEmailError, InvalidCredentialsError, hash_password(), hash_refresh_token(), TokenResponse, TOTPSetupResponse (+7 more)

### Community 39 - "Community 39"
Cohesion: 0.09
Nodes (15): InsufficientBalanceError, NoSlotsAvailableError, format_pkr(), WalletRepository, WalletTransactionRepository, SlotPricingResponse, SlotPurchaseResponse, SlotService (+7 more)

### Community 40 - "Community 40"
Cohesion: 0.11
Nodes (23): AnalyticsEvent, AdminProductDetailResponse, AdminProductRowResponse, AdminProductsPage, AdminProductsPagination, BrandSuggestion, CataloguePage, CategoryResponse (+15 more)

### Community 41 - "Community 41"
Cohesion: 0.05
Nodes (13): upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade() (+5 more)

### Community 42 - "Community 42"
Cohesion: 0.07
Nodes (4): AddressResponse, UserProfileResponse, WishlistResponse, lock_active_user()

### Community 43 - "Community 43"
Cohesion: 0.15
Nodes (39): AdminSellersPage(), consequences, DecisionForm(), decisionLabels, RegistrationForm(), RegistrationReceipt(), SellerList(), SellerReview() (+31 more)

### Community 44 - "Community 44"
Cohesion: 0.07
Nodes (4): create_email_verify_token(), SellerRepository, WorkerSettings, test_email_job_retries_and_records_final_result()

### Community 45 - "Community 45"
Cohesion: 0.06
Nodes (9): ExternalServiceError, RedisKeys, revoke_token(), require_configuration(), start_google_login(), TestGoogleOAuth, domain_error(), test_google_configuration_and_browser_state() (+1 more)

### Community 46 - "Community 46"
Cohesion: 0.16
Nodes (24): add_variant(), admin_hide_product(), admin_list_products(), admin_product_detail(), create_product(), delete_image(), delete_product(), get_product() (+16 more)

### Community 47 - "Community 47"
Cohesion: 0.12
Nodes (23): ReviewVote, DRIPBaseModel, AddToWishlistRequest, AvatarUploadResponse, ChangePasswordRequest, CreateAddressRequest, CreateReviewRequest, DeleteAccountRequest (+15 more)

### Community 48 - "Community 48"
Cohesion: 0.12
Nodes (37): analyticsMoney(), balanced(), CommissionEntry, CommissionPage, CommissionSummary, count(), date(), day() (+29 more)

### Community 49 - "Community 49"
Cohesion: 0.10
Nodes (4): BankAccountRepository, SellerProfileResponse, SellerService, test_admin_seller_bank_and_cod_management()

### Community 50 - "Community 50"
Cohesion: 0.16
Nodes (31): review(), test_detail_saved_destination_and_admin_boundary(), test_existing_evidence_blocks_mutation(), test_missing_wallet_does_not_falsely_record_reversal(), test_rejection_requires_meaningful_note(), test_reviewed_completion_preserves_receipt_on_replay(), test_stale_snapshot_cannot_approve(), accounts() (+23 more)

### Community 51 - "Community 51"
Cohesion: 0.17
Nodes (22): admin_approve_payout(), admin_complete_payout(), admin_get_payout(), admin_list_payouts(), admin_reject_payout(), admin_wallet_overview(), get_commission_breakdown(), get_payout_history() (+14 more)

### Community 52 - "Community 52"
Cohesion: 0.07
Nodes (6): get_settings(), Settings, _provider_money_matches(), test_enabled_gateway_requires_authoritative_status_api(), test_explicit_consistent_money_is_accepted(), test_missing_invalid_or_conflicting_money_is_rejected()

### Community 53 - "Community 53"
Cohesion: 0.07
Nodes (34): dependencies, react@19.3.1, react-dom@19.3.1, react-router@8.5.0, devDependencies, @axe-core/playwright@4.14.0, jsdom@^26.1.0, @playwright/test@1.64.1 (+26 more)

### Community 54 - "Community 54"
Cohesion: 0.10
Nodes (15): create_banner(), delete_banner(), list_banners(), update_banner(), Banner, BannerResponse, UpdateBannerRequest, test_concurrent_updates_have_one_winner() (+7 more)

### Community 55 - "Community 55"
Cohesion: 0.12
Nodes (15): AddDisputeMessageRequest, CreateReturnRequest, OpenDisputeRequest, test_preloaded_dispute_is_refreshed_after_other_session_resolves(), _reject_and_open_dispute(), test_admin_dispute_detail_reply_and_terminal_state(), test_deletion_and_new_case_serialize(), case() (+7 more)

### Community 56 - "Community 56"
Cohesion: 0.09
Nodes (19): ErrorBoundaryMiddleware, assert_error(), ProbeInput, test_bodyless_status_is_preserved(), test_development_docs_allow_assets_and_bootstrap(), test_development_health_schema_preserves_degraded_response(), test_error_boundary_does_not_swallow_cancellation(), test_error_boundary_never_sends_second_response() (+11 more)

### Community 57 - "Community 57"
Cohesion: 0.12
Nodes (6): NotificationService, test_canonical_preferences_enforce_optional_order_updates(), test_import_then_explicit_edit_is_not_overwritten(), test_payout_money_notice_respects_opt_out(), test_payout_notification_keeps_paisa_without_repeating_or_charging(), test_notifications_delivery_preferences_and_jobs()

### Community 58 - "Community 58"
Cohesion: 0.11
Nodes (20): RegisterRequest, test_google_only_deletion_requires_reauthentication(), test_privileged_accounts_require_managed_offboarding(), test_bootstrap_account_never_overwrites_existing_credentials_or_role(), test_exact_amount_remaining_and_normalized_reason(), test_existing_multiline_return_notes_remain_supported(), test_explicit_null_return_link_is_distinct_from_legacy_omission(), test_invalid_reason() (+12 more)

### Community 59 - "Community 59"
Cohesion: 0.22
Nodes (23): add_dispute_message(), admin_add_dispute_message(), admin_approve_return(), admin_get_dispute(), admin_get_return(), admin_list_disputes(), admin_list_returns(), admin_mark_received() (+15 more)

### Community 60 - "Community 60"
Cohesion: 0.16
Nodes (24): db(), assert_error(), capability(), checkout(), completed(), guest_order(), offline_boundaries(), payment_request() (+16 more)

### Community 61 - "Community 61"
Cohesion: 0.18
Nodes (27): assert_error(), assert_valid_identity(), callback_payload(), callback_request(), headers(), snapshot(), test_absent_token_is_rejected(), test_account_order_requires_identity() (+19 more)

### Community 62 - "Community 62"
Cohesion: 0.14
Nodes (13): AdminReturnCustomerResponse, AdminReturnDetailResponse, AdminReturnDisputeResponse, AdminReturnItemResponse, AdminReturnOrderResponse, AdminReturnRefundResponse, AdminReturnSellerResponse, PaginatedReturns (+5 more)

### Community 63 - "Community 63"
Cohesion: 0.10
Nodes (8): CreateBankAccountRequest, SellerProfileUpdateRequest, UpdateOrderStatusRequest, _slugify(), TestBankAccountSchema, TestOrderStatusSchema, TestProfileUpdateSchema, TestSlugify

### Community 64 - "Community 64"
Cohesion: 0.13
Nodes (12): google_callback(), finish_google_login(), google_callback_response(), flow(), test_bound_cancellation_consumes_state_without_provider_request(), test_expired_cancellation_is_not_accepted(), test_failures_roll_back_without_leaking_details(), test_provider_error_or_missing_code_never_reflected() (+4 more)

### Community 65 - "Community 65"
Cohesion: 0.21
Nodes (26): CollectionForm(), PaymentCard(), PaymentFilters(), PaymentInspection(), save(), PaymentResults(), AdminPayment, AdminPayments (+18 more)

### Community 66 - "Community 66"
Cohesion: 0.20
Nodes (17): cohort_retention(), conversion_funnel(), orders_by_city(), payment_methods(), platform_analytics(), platform_revenue(), search_queries(), top_sellers() (+9 more)

### Community 67 - "Community 67"
Cohesion: 0.09
Nodes (10): CursorPagination, DateRangeParams, DRIPResponseModel, ErrorDetail, ErrorResponse, HealthResponse, MessageResponse, PagePagination (+2 more)

### Community 68 - "Community 68"
Cohesion: 0.11
Nodes (12): _serialize_amount(), CreateVariantRequest, ReorderImagesRequest, UpdateVariantRequest, test_openapi_documents_price_strings_and_nullable_sale(), test_pkr_amount_is_decimal_in_python_and_fixed_string_in_json(), test_price_entry_policy_still_whole_rupees(), test_response_rejects_invalid_amount_instead_of_truncating() (+4 more)

### Community 69 - "Community 69"
Cohesion: 0.16
Nodes (21): BankAccountResponse, LogoUploadResponse, OrderItemSchema, OrderStatusBreakdown, PagePagination, PaginatedSellerOrders, RevenueAnalyticsResponse, RevenueDayRow (+13 more)

### Community 70 - "Community 70"
Cohesion: 0.13
Nodes (9): _client_ip(), client_ip(), matches_ip(), LoggingMiddleware, request(), test_invalid_allowlists_do_not_grant_trust(), test_middleware_and_payment_share_safe_resolution(), test_payment_proxy_override_stays_separate() (+1 more)

### Community 71 - "Community 71"
Cohesion: 0.21
Nodes (14): confirm_refund(), gateway_status(), get_admin_payment(), get_payment_refunds(), get_payment_status(), get_refund(), initiate_payment(), list_payments() (+6 more)

### Community 72 - "Community 72"
Cohesion: 0.14
Nodes (3): TestResendEmailClient, fake_send(), TestSupabaseStorage

### Community 73 - "Community 73"
Cohesion: 0.22
Nodes (24): completeShippingAddress(), confirmFulfilment(), fail(), FulfilmentChange, fulfilmentChange(), FulfilmentDetail, fulfilmentLabel(), fulfilmentMarker() (+16 more)

### Community 74 - "Community 74"
Cohesion: 0.16
Nodes (12): broadcast_notification(), failed_notifications(), get_email_log(), get_preferences(), list_notifications(), mark_all_read(), mark_notification_read(), replay_notification() (+4 more)

### Community 75 - "Community 75"
Cohesion: 0.17
Nodes (24): label(), ReviewDetail(), refresh(), save(), ReviewForm(), ReviewList(), ReviewResults(), AdminReviews (+16 more)

### Community 76 - "Community 76"
Cohesion: 0.21
Nodes (23): ReturnList, confirmSellerReturn(), fail(), money(), nullableText(), SellerReturnAction, sellerReturnActions(), sellerReturnBody() (+15 more)

### Community 77 - "Community 77"
Cohesion: 0.18
Nodes (9): seller_inventory_health(), seller_overview(), seller_revenue_series(), seller_top_products(), InventoryHealthResponse, RevenueSeriesResponse, TopProductsResponse, SellerAnalyticsService (+1 more)

### Community 79 - "Community 79"
Cohesion: 0.13
Nodes (6): RateLimitMiddleware, RequestIDMiddleware, test_native_rate_counter_is_atomic_and_expires(), test_counter_expires_and_does_not_extend_window(), test_counter_missing_expiry_is_repaired(), test_rate_limit_scope_cannot_be_reset_by_changing_resource_id()

### Community 80 - "Community 80"
Cohesion: 0.15
Nodes (8): approve_payout(), complete_payout(), list_all_payouts(), PayoutActionRequest, PayoutCompletionRequest, reject_payout(), AdminPayoutActionRequest, TestAdminPayoutSchema

### Community 81 - "Community 81"
Cohesion: 0.16
Nodes (14): AdminOrderRowResponse, AdminSellerDetailResponse, AdminSellerRowResponse, OrderTotals, PaginatedAdminOrders, SellerRegistrationPaymentRequest, run_action(), test_http_runtime_pricing_and_payment_due_snapshot() (+6 more)

### Community 82 - "Community 82"
Cohesion: 0.14
Nodes (11): cancel_cod_order(), list_cod_queue(), verify_cod_order(), CODDecisionResponse, CODQueueItem, CODVerifyRequest, test_exact_and_past_deadlines_reject_approval(), test_invalid_decision_fields() (+3 more)

### Community 85 - "Community 85"
Cohesion: 0.13
Nodes (11): admin_headers(), client(), customer_headers(), db(), isolated_redis(), _make_auth_headers(), seller_headers(), test_engine() (+3 more)

### Community 86 - "Community 86"
Cohesion: 0.19
Nodes (10): add_bank_account(), delete_bank_account(), get_dashboard(), get_seller_profile(), get_slot_pricing(), list_bank_accounts(), purchase_slots(), register_seller() (+2 more)

### Community 87 - "Community 87"
Cohesion: 0.17
Nodes (9): admin_response(), AdminReviewResponse, AdminReviewsPage, list_reviews(), moderate_review(), ModerateReviewRequest, review_detail(), decide() (+1 more)

### Community 88 - "Community 88"
Cohesion: 0.16
Nodes (4): Notification, NotificationRepository, archive_old_notifications(), test_notification_read_archive_and_ownership()

### Community 89 - "Community 89"
Cohesion: 0.16
Nodes (8): CityRow, PaymentMethodStat, PlatformAnalytics, RevenueDayRow, SellerAnalyticsOverview, _trunc(), TestAnalyticsSchemas, TestGranularity

### Community 90 - "Community 90"
Cohesion: 0.14
Nodes (8): WithdrawalRequest, test_wallet_history_and_bank_details_are_seller_scoped(), TestCommissionMath, TestWithdrawalSchema, test_fresh_process_schema_and_openapi_follow_startup_limits(), test_invalid_withdrawal_amounts_remain_rejected(), test_invalid_withdrawal_configuration_fails_startup(), test_service_rechecks_configured_limits_before_mutation()

### Community 91 - "Community 91"
Cohesion: 0.25
Nodes (19): auth(), error(), snapshot(), test_authenticated_empty_updates_rejected(), test_bank_account_defaults_and_ownership(), test_dashboard_and_revenue_empty_state(), test_empty_registration_rejected(), test_insufficient_wallet_does_not_add_slots_or_transactions() (+11 more)

### Community 92 - "Community 92"
Cohesion: 0.19
Nodes (5): SlotPurchaseRequest, TestSlotPurchaseSchema, _mock_service(), TestSlotPurchaseFlow, TestSlotPurchaseRequestSchema

### Community 93 - "Community 93"
Cohesion: 0.24
Nodes (19): CartProvider(), add(), clear(), loadStorage(), merge(), perform(), save(), storageChanged() (+11 more)

### Community 94 - "Community 94"
Cohesion: 0.20
Nodes (7): adjust_variant_stock(), admin_list_inventory(), get_low_stock_alerts(), get_variant_stock(), list_seller_inventory(), PaginatedVariantStock, set_variant_stock()

### Community 95 - "Community 95"
Cohesion: 0.21
Nodes (3): VariantStockResponse, InventoryService, test_reorder_threshold_round_trip_and_filters()

### Community 96 - "Community 96"
Cohesion: 0.17
Nodes (7): RejectSellerRequest, SuspendSellerRequest, UpdateSettingsRequest, test_seller_decision_loader_locks_and_refreshes_current_state(), test_seller_decision_loader_rejects_missing_or_deleted_seller(), TestSellerActionSchemas, TestUpdateSettingsSchema

### Community 97 - "Community 97"
Cohesion: 0.12
Nodes (19): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+11 more)

### Community 98 - "Community 98"
Cohesion: 0.14
Nodes (12): create_application(), test_openapi_private_read_contracts(), row(), test_invalid_money_is_not_silently_rounded(), test_openapi_documents_admin_product_contract(), test_openapi_has_separate_private_admin_detail_contract(), test_row_preserves_live_fields_and_money(), test_notes_are_normalized() (+4 more)

### Community 99 - "Community 99"
Cohesion: 0.17
Nodes (15): BulkStockUpdateItem, items(), stored(), test_bulk_correction_and_reservation_serialize(), bulk(), competitor(), reserve(), test_database_row_failure_preserves_other_successes() (+7 more)

### Community 100 - "Community 100"
Cohesion: 0.16
Nodes (10): files(), snapshot(), storage(), test_banner_oversize_keeps_413(), test_catalogue_filter_policy_preserved(), test_native_price_constraints_still_match_policy(), test_service_cap_rejects_direct_call_without_rows(), test_upload_rejects_limits_without_storage_or_rows() (+2 more)

### Community 102 - "Community 102"
Cohesion: 0.16
Nodes (4): UpdateProductRequest, _slugify(), TestSlugify, TestUpdateProductSchema

### Community 103 - "Community 103"
Cohesion: 0.20
Nodes (7): TopProductRow, TopSellerRow, TopSellersResponse, _money(), test_all_money_fields_preserve_large_decimal_and_publish_string_schema(), test_money_rounding_is_explicit_half_up(), test_money_schema_rejects_nonfinite_or_unrounded_output()

### Community 104 - "Community 104"
Cohesion: 0.15
Nodes (3): _date_from(), _period_to_days(), TestPeriodHelpers

### Community 105 - "Community 105"
Cohesion: 0.18
Nodes (4): _make_seller_order(), _make_service(), create_ledger(), TestCommissionSettle

### Community 106 - "Community 106"
Cohesion: 0.14
Nodes (3): AdjustStockRequest, SetStockRequest, test_threshold_bounds()

### Community 107 - "Community 107"
Cohesion: 0.12
Nodes (9): BusinessRuleError, CODLimitExceededError, CouponInvalidError, CouponLimitReachedError, OrderCancellationError, PaymentRequiredError, PaymentVerificationError, test_duplicate_decision_does_not_publish_twice() (+1 more)

### Community 108 - "Community 108"
Cohesion: 0.18
Nodes (4): ImageService, test_image_byte_boundary_before_conversion(), test_corrupt_image_validation(), test_image_conversion_and_delete_boundaries()

### Community 109 - "Community 109"
Cohesion: 0.18
Nodes (12): actors(), banner(), client(), image_bytes(), test_bad_image_never_reaches_storage(), test_create_metadata_rejected_before_upload(), test_create_update_schedule_clear_delete(), test_invalid_patch_does_not_mutate() (+4 more)

### Community 110 - "Community 110"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+8 more)

### Community 111 - "Community 111"
Cohesion: 0.12
Nodes (3): InsufficientStockError, InvalidStatusTransitionError, ValidationError

### Community 113 - "Community 113"
Cohesion: 0.28
Nodes (13): SettingsForm(), SettingsManager(), save(), confirmSettings(), PlatformSettings, sameSettings(), settingFields, SettingKey (+5 more)

### Community 114 - "Community 114"
Cohesion: 0.24
Nodes (13): extraSlots(), money(), registrationMarker, registrationMoney(), RegistrationPricing, RegistrationResult, samePricing(), pricing (+5 more)

### Community 115 - "Community 115"
Cohesion: 0.36
Nodes (8): approve_seller(), get_seller(), list_sellers(), record_registration_payment(), reinstate_seller(), reject_seller(), suspend_seller(), PaginatedAdminSellers

### Community 118 - "Community 118"
Cohesion: 0.24
Nodes (12): count(), Inbox, InboxItem, notificationLink(), inbox, row, uuid, validateInbox() (+4 more)

### Community 119 - "Community 119"
Cohesion: 0.25
Nodes (8): validate_phone(), dependencies(), policy(), routes(), test_all_protected_operations_reject_invalid_identity_or_role(), test_checkout_policy_is_explicit_and_method_scoped(), test_every_operation_has_the_reviewed_guard(), test_review_photo_policy_is_authenticated_and_method_scoped()

### Community 121 - "Community 121"
Cohesion: 0.34
Nodes (7): test_forgot_password_does_not_enumerate_accounts(), test_login_rejects_invalid_password(), test_login_sets_refresh_cookie(), test_me_requires_authentication(), test_rate_limit_middleware_returns_429(), test_register_returns_created(), test_register_validation_rejects_weak_password()

### Community 122 - "Community 122"
Cohesion: 0.37
Nodes (10): DisputeMessage, auth_headers(), message_count(), test_admin_review_and_resolution_remain_available(), test_missing_return_is_not_found(), test_non_owner_cannot_reply_or_probe_state(), test_owned_return_without_dispute_is_not_found(), test_owner_can_reply_and_cannot_spoof_sender() (+2 more)

### Community 124 - "Community 124"
Cohesion: 0.27
Nodes (8): eligible(), test_bad_reference(), test_bad_review_version(), test_eligible_full_payment(), test_equal_aggregate_does_not_hide_wrong_brand_allocation(), test_inconsistent_collection_is_blocked(), test_partially_cancelled_fulfilment_cannot_collect_full_amount(), test_trimmed_reference_and_legacy_payload()

### Community 125 - "Community 125"
Cohesion: 0.41
Nodes (8): headers(), seed_seller(), test_ineligible_state_does_not_record_payment(), test_registration_payment_races(), test_registration_payment_requires_verified_admin(), test_registration_receipt_readback_and_identical_replay(), test_wrong_registration_amount_does_not_record_payment(), test_zero_fee_and_partial_legacy_record_are_not_fake_receipts()

### Community 126 - "Community 126"
Cohesion: 0.35
Nodes (10): SavedProvider(), changed(), reload(), set(), changeSaved(), MAX_SAVED, parseSaved(), readSaved() (+2 more)

### Community 127 - "Community 127"
Cohesion: 0.40
Nodes (10): brandChanges(), BrandDraft, brandDraft(), BrandProfile, confirmBrandUpdate(), profileLimits, profile, validateBrandProfile() (+2 more)

### Community 128 - "Community 128"
Cohesion: 0.33
Nodes (7): brand_detail(), brand_products(), brand_response(), brands(), categories(), is_visible(), public_banners()

### Community 131 - "Community 131"
Cohesion: 0.27
Nodes (5): ResolveDisputeRequest, open_case(), test_blank_admin_dispute_text_is_rejected(), test_dispute_review_rejects_unread_messages(), TestResolveDisputeSchema

### Community 132 - "Community 132"
Cohesion: 0.36
Nodes (6): BroadcastResponse, EmailLogResponse, MarkReadResponse, NotificationListResponse, NotificationPreferencesResponse, NotificationResponse

### Community 134 - "Community 134"
Cohesion: 0.33
Nodes (7): funded(), snapshot(), test_configured_boundary_debits_once_and_records_exact_amount(), test_direct_service_rejects_out_of_policy_without_writes(), test_other_withdrawal_guards_preserved(), test_out_of_policy_http_request_has_no_financial_effect(), test_withdrawal_roles_still_rejected()

### Community 135 - "Community 135"
Cohesion: 0.22
Nodes (6): do_run_migrations(), get_sync_url(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online()

### Community 136 - "Community 136"
Cohesion: 0.20
Nodes (3): LowStockResponse, StockAdjustmentResponse, test_seller_inventory_has_stable_order_and_scope()

### Community 137 - "Community 137"
Cohesion: 0.24
Nodes (3): verify_password(), clear_customer_cache(), test_customer_password_revokes_tokens_and_account_deletion()

### Community 139 - "Community 139"
Cohesion: 0.25
Nodes (4): admin_bulk_update_inventory(), BulkStockUpdateRequest, BulkStockUpdateResponse, test_contract_accepts_exactly_500_unique_updates()

### Community 145 - "Community 145"
Cohesion: 0.22
Nodes (3): cache, require, temporaryRoot

### Community 149 - "Community 149"
Cohesion: 0.54
Nodes (7): checkout(), preview(), setup_coupon(), test_checkout_rechecks_price_after_successful_preview(), test_fractional_minimum_is_identical_for_preview_and_checkout(), test_fractional_preview_matches_persisted_checkout(), test_preview_rejects_invalid_money_without_usage()

### Community 151 - "Community 151"
Cohesion: 0.29
Nodes (5): fillDetails(), order, quote, review(), selection

### Community 157 - "Community 157"
Cohesion: 0.29
Nodes (7): scripts, build, dev, preview, test, test:browser, typecheck

### Community 158 - "Community 158"
Cohesion: 0.47
Nodes (3): NotificationPreference, test_conflicting_preexisting_records_preserve_opt_out(), test_import_failure_never_assumes_consent()

### Community 166 - "Community 166"
Cohesion: 0.60
Nodes (4): cart(), product, setup(), setupAccount()

### Community 169 - "Community 169"
Cohesion: 0.60
Nodes (3): imageId(), img(), setup()

## Knowledge Gaps
- **80 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BusinessRuleError` connect `Community 107` to `Community 0`, `Community 1`, `Community 130`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 131`, `Community 136`, `Community 137`, `Community 8`, `Community 134`, `Community 12`, `Community 13`, `Community 15`, `Community 17`, `Community 21`, `Community 22`, `Community 150`, `Community 24`, `Community 25`, `Community 29`, `Community 30`, `Community 33`, `Community 35`, `Community 36`, `Community 38`, `Community 39`, `Community 40`, `Community 42`, `Community 45`, `Community 47`, `Community 50`, `Community 51`, `Community 54`, `Community 55`, `Community 56`, `Community 58`, `Community 60`, `Community 62`, `Community 64`, `Community 68`, `Community 74`, `Community 82`, `Community 84`, `Community 90`, `Community 95`, `Community 100`, `Community 108`, `Community 111`, `Community 115`, `Community 125`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 82 inferred relationships involving `BusinessRuleError` (e.g. with `record_registration_payment()` and `update_banner()`) actually correct?**
  _`BusinessRuleError` has 82 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.02603734439834025 - nodes in this community are weakly interconnected._
- **Why does `NotFoundError` connect `Community 25` to `Community 128`, `Community 1`, `Community 0`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 130`, `Community 136`, `Community 137`, `Community 13`, `Community 17`, `Community 20`, `Community 21`, `Community 22`, `Community 29`, `Community 30`, `Community 35`, `Community 36`, `Community 39`, `Community 40`, `Community 42`, `Community 47`, `Community 49`, `Community 51`, `Community 54`, `Community 55`, `Community 62`, `Community 69`, `Community 74`, `Community 84`, `Community 86`, `Community 87`, `Community 92`, `Community 95`, `Community 96`, `Community 105`, `Community 106`, `Community 107`, `Community 108`, `Community 109`, `Community 111`, `Community 115`, `Community 122`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 73 inferred relationships involving `OrderService` (e.g. with `cancel_order()` and `get_order()`) actually correct?**
  _`OrderService` has 73 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.03550609432962374 - nodes in this community are weakly interconnected._
- **Why does `TestAdminAnalyticsEndpoints` connect `Community 133` to `Community 5`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
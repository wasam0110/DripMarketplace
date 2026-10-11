# Backend source index: routes

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## app/api/v1/admin/__init__.py

1 lines; SHA-256 `e849c1237bc3edd7f9853b577bea0826c30fe0b54e93f1d6ed1303ce6f477e63`. [Open source](../../app/api/v1/admin/__init__.py).


## app/api/v1/admin/brands.py

107 lines; SHA-256 `8fda0e6c766b2484cbae188da9256329f250860e536ac1e996f16352a32581c1`. [Open source](../../app/api/v1/admin/brands.py).

Backend imports: `app.api.deps`, `app.core.exceptions`, `app.models.seller`, `app.schemas.admin`, `app.services.admin_service`.

- `list_sellers` (async), lines 21?32: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).list_sellers`, `Query`, `router.get`.
- `get_seller` (async), lines 36?41: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).get_seller`, `router.get`.
- `approve_seller` (async), lines 45?50: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).approve_seller`, `UUID`, `router.post`.
- `reject_seller` (async), lines 54?62: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).reject_seller`, `UUID`, `router.post`.
- `suspend_seller` (async), lines 66?74: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).suspend_seller`, `UUID`, `router.post`.
- `reinstate_seller` (async), lines 78?83: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).reinstate_seller`, `UUID`, `router.post`.
- `record_registration_payment` (async), lines 88?107: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `Seller.deleted_at.is_`, `UUID`, `datetime.now`, `db.commit`, `db.scalar`, `router.post`, `select`, `select(Seller).where`, `select(Seller).where(Seller.id == seller_id, Seller.deleted_at.is_(None)).with_for_update`.
  Mutation/I-O-related call names: `Seller.deleted_at.is_`, `db.commit`, `select(Seller).where(Seller.id == seller_id, Seller.deleted_at.is_(None)).with_for_update`.

## app/api/v1/admin/cod_queue.py

49 lines; SHA-256 `3269b9df9ea12eedcb094e6f1c6ecfe0cad20c3fe687a58e1f07ba1f96c0b6cd`. [Open source](../../app/api/v1/admin/cod_queue.py).

Backend imports: `app.api.deps`, `app.schemas.admin`, `app.services.admin_service`.

- `list_cod_queue` (async), lines 18?21: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).list_cod_queue`, `router.get`.
- `verify_cod_order` (async), lines 25?35: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).verify_cod`, `UUID`, `router.post`.
- `cancel_cod_order` (async), lines 39?49: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).cancel_cod`, `UUID`, `router.post`.

## app/api/v1/admin/content.py

104 lines; SHA-256 `81cd5229afa020dbcd0c951d5f26e87d405524f69b965a0fa2fd414accb124a9`. [Open source](../../app/api/v1/admin/content.py).

Backend imports: `app.api.deps`, `app.core.exceptions`, `app.models.admin`, `app.schemas.admin`, `app.services.admin_service`, `app.services.image_service`.

- `list_banners` (async), lines 21?22: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).list_banners`, `router.get`.
- `create_banner` (async), lines 26?57: No function docstring; consult the source body and layer walkthrough.
  Calls: `', '.join`, `AdminService`, `AdminService(db).create_banner`, `File`, `Form`, `HTTPException`, `ImageService`, `ImageService().process_and_upload`, `image.read`, `len`, `router.post`.
  Mutation/I-O-related call names: `ImageService().process_and_upload`.
- `delete_banner` (async), lines 61?67: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).delete_banner`, `Response`, `router.delete`.
  Mutation/I-O-related call names: `AdminService(db).delete_banner`, `router.delete`.
- `update_banner` (async), lines 74?104: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `changes.items`, `db.commit`, `db.get`, `payload.model_dump`, `router.patch`, `setattr`, `value.startswith`.
  Mutation/I-O-related call names: `db.commit`.

## app/api/v1/admin/dashboard.py

22 lines; SHA-256 `022d0fce05d37464ddd12cb3efa37a1de44d07dce9d1770741e1504c83c1ecd9`. [Open source](../../app/api/v1/admin/dashboard.py).

Backend imports: `app.api.deps`, `app.schemas.admin`, `app.services.admin_service`.

- `admin_dashboard` (async), lines 17?22: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).get_dashboard`, `Query`, `router.get`.

## app/api/v1/admin/orders.py

34 lines; SHA-256 `3d6264c5a3c1819e13ae96ddda3b16c9d3b669614c6dcd83d39ca1080b3c713f`. [Open source](../../app/api/v1/admin/orders.py).

Backend imports: `app.api.deps`, `app.models.order`, `app.schemas.admin`, `app.services.admin_service`.

- `list_all_orders` (async), lines 19?34: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).list_orders`, `Query`, `router.get`.

## app/api/v1/admin/payouts.py

103 lines; SHA-256 `c47b401d06e5db0e11106e8ac3389c07dda112be497dcb576ead597ab759c555`. [Open source](../../app/api/v1/admin/payouts.py).

Backend imports: `app.api.deps`, `app.core.exceptions`, `app.models.wallet`, `app.schemas.wallet`, `app.services.wallet_service`.

- Class `PayoutActionRequest`, lines 19?21; bases: BaseModel.
  Annotated fields: `admin_note`, `payment_reference`.
- `list_all_payouts` (async), lines 25?47: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaginatedPayouts`, `PayoutResponse`, `Query`, `WalletService`, `int`, `max`, `router.get`, `svc.payout_repo.list_admin`.
- `approve_payout` (async), lines 51?61: No function docstring; consult the source body and layer walkthrough.
  Calls: `UUID`, `WalletService`, `WalletService(db).admin_approve_payout`, `router.post`.
- `complete_payout` (async), lines 65?87: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `PayoutResponse`, `UUID`, `WalletService`, `db.commit`, `int`, `router.post`, `svc.payout_repo.get_by_id`, `svc.payout_repo.update_status`.
  Mutation/I-O-related call names: `db.commit`.
- `reject_payout` (async), lines 91?103: No function docstring; consult the source body and layer walkthrough.
  Calls: `HTTPException`, `UUID`, `WalletService`, `WalletService(db).admin_reject_payout`, `router.post`.

## app/api/v1/admin/reviews.py

60 lines; SHA-256 `46ff4b598ba3ba7c44af18fce6eb7f0f15c1cee2047c4ae43cb4b1d8b48d0132`. [Open source](../../app/api/v1/admin/reviews.py).

Backend imports: `app.api.deps`, `app.core.exceptions`, `app.models.review`, `app.services.customer_service`.

- Class `ModerateReviewRequest`, lines 18?20; bases: BaseModel.
  Annotated fields: `status`, `admin_note`.
- `list_reviews` (async), lines 24?44: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await db.scalars(query.order_by(Review.created_at.desc(), Review.id).offset((page - 1) * 25).limit(25))).all`, `CustomerService._review_to_schema`, `Query`, `Review.created_at.desc`, `db.scalar`, `db.scalars`, `func.count`, `query.order_by`, `query.order_by(Review.created_at.desc(), Review.id).offset`, `query.order_by(Review.created_at.desc(), Review.id).offset((page - 1) * 25).limit`, `query.subquery`, `query.where` ? (15 distinct call expressions).
- `moderate_review` (async), lines 48?60: No function docstring; consult the source body and layer walkthrough.
  Calls: `CustomerService`, `CustomerService(db).refresh_product_rating`, `CustomerService._review_to_schema`, `NotFoundError`, `ReviewStatus`, `db.commit`, `db.flush`, `db.refresh`, `db.scalar`, `router.patch`, `select`, `select(Review).where` ? (13 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`, `db.flush`.

## app/api/v1/admin/settings.py

29 lines; SHA-256 `a86915c3a005c9068b8a5d8ae57c9f84e668dbb2f4199b30cf29f17ba9c8520d`. [Open source](../../app/api/v1/admin/settings.py).

Backend imports: `app.api.deps`, `app.schemas.admin`, `app.services.admin_service`.

- `get_settings` (async), lines 18?19: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).get_settings`, `router.get`.
- `update_settings` (async), lines 23?29: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminService`, `AdminService(db).update_settings`, `UUID`, `payload.model_dump`, `payload.model_dump().items`, `router.patch`.

## app/api/v1/analytics/__init__.py

1 lines; SHA-256 `e0e69c02d96ca4439e9a581e5d03ef62fd6fe64ea2ccc6100d6720a0be152ec3`. [Open source](../../app/api/v1/analytics/__init__.py).


## app/api/v1/analytics/admin.py

94 lines; SHA-256 `faf24067a5f4db84d10618d00234d24df18aaae761b4bf82c69bba723f9e7bf1`. [Open source](../../app/api/v1/analytics/admin.py).

Backend imports: `app.api.deps`, `app.schemas.analytics`, `app.services.analytics_service`.

- `platform_analytics` (async), lines 22?27: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminAnalyticsService`, `AdminAnalyticsService(db).get_platform_analytics`, `Query`, `router.get`.
- `platform_revenue` (async), lines 31?37: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminAnalyticsService`, `AdminAnalyticsService(db).get_platform_revenue`, `Query`, `router.get`.
- `top_sellers` (async), lines 41?47: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminAnalyticsService`, `AdminAnalyticsService(db).get_top_sellers`, `Query`, `router.get`.
- `cohort_retention` (async), lines 51?56: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminAnalyticsService`, `AdminAnalyticsService(db).get_cohort`, `Query`, `router.get`.
- `payment_methods` (async), lines 60?65: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminAnalyticsService`, `AdminAnalyticsService(db).get_payment_methods`, `Query`, `router.get`.
- `orders_by_city` (async), lines 69?75: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminAnalyticsService`, `AdminAnalyticsService(db).get_cities`, `Query`, `router.get`.
- `conversion_funnel` (async), lines 79?84: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminAnalyticsService`, `AdminAnalyticsService(db).get_conversion`, `Query`, `router.get`.
- `search_queries` (async), lines 88?94: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminAnalyticsService`, `AdminAnalyticsService(db).get_search_queries`, `Query`, `router.get`.

## app/api/v1/analytics/seller.py

65 lines; SHA-256 `1f875d8c7878c3588380a0ff4498c20f26d795a33fb8c5298a8578488de946ef`. [Open source](../../app/api/v1/analytics/seller.py).

Backend imports: `app.api.deps`, `app.schemas.analytics`, `app.services.analytics_service`.

- `seller_overview` (async), lines 21?28: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `SellerAnalyticsService`, `SellerAnalyticsService(db).get_overview`, `UUID`, `router.get`.
- `seller_revenue_series` (async), lines 32?41: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `SellerAnalyticsService`, `SellerAnalyticsService(db).get_revenue_series`, `UUID`, `router.get`.
- `seller_top_products` (async), lines 45?55: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `SellerAnalyticsService`, `SellerAnalyticsService(db).get_top_products`, `UUID`, `router.get`.
- `seller_inventory_health` (async), lines 59?65: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerAnalyticsService`, `SellerAnalyticsService(db).get_inventory_health`, `UUID`, `router.get`.

## app/api/v1/auth.py

417 lines; SHA-256 `b8d3955562471ee23971dd86a8a96e38ef7c7f86428295027eb81b83bc8292eb`. [Open source](../../app/api/v1/auth.py).

Backend imports: `app.api.deps`, `app.core.config`, `app.core.exceptions`, `app.core.redis`, `app.core.security`, `app.repositories.user_repo`, `app.schemas.auth`, `app.services.auth_service`, `app.services.google_oauth`.

- `register` (async), lines 42?75: Create a new customer account.
  Calls: `AuthService.register`, `MessageResponse`, `RedisSettings.from_dsn`, `create_pool`, `pool.aclose`, `pool.enqueue_job`, `router.post`.
  Mutation/I-O-related call names: `pool.enqueue_job`.
- `verify_email` (async), lines 86?97: Called when the user clicks the verification link in their email.
  Calls: `AuthService.verify_email`, `_set_refresh_cookie`, `router.get`.
- `login` (async), lines 108?132: Authenticate and receive tokens.
  Calls: `AuthService.login`, `_get_ip`, `_set_refresh_cookie`, `request.headers.get`, `router.post`.
- `refresh` (async), lines 143?159: Exchange a valid refresh token (from httpOnly cookie) for a new access token.
  Calls: `AuthService.refresh_token`, `AuthenticationError`, `Cookie`, `_set_refresh_cookie`, `router.post`.
- `logout` (async), lines 170?190: Revoke the refresh token + blocklist the current access token.
  Calls: `AuthService.logout`, `Cookie`, `Depends`, `_clear_refresh_cookie`, `datetime.fromtimestamp`, `payload.get`, `router.post`.
- `forgot_password` (async), lines 201?231: Always returns 200 regardless of whether the email exists (prevents enumeration).
  Calls: `AuthService.forgot_password`, `MessageResponse`, `RedisSettings.from_dsn`, `UserRepository.get_by_email`, `create_pool`, `pool.aclose`, `pool.enqueue_job`, `router.post`.
  Mutation/I-O-related call names: `pool.enqueue_job`.
- `reset_password` (async), lines 242?249: No function docstring; consult the source body and layer walkthrough.
  Calls: `AuthService.reset_password`, `MessageResponse`, `router.post`.
- `get_me` (async), lines 260?271: Return the profile of the currently authenticated user.
  Calls: `UserRepository.get_by_id_or_raise`, `_user_to_response`, `router.get`, `token_payload.get`.
- `change_password` (async), lines 282?297: No function docstring; consult the source body and layer walkthrough.
  Calls: `AuthService.change_password`, `MessageResponse`, `_clear_refresh_cookie`, `router.post`, `uuid.UUID`.
- `setup_2fa` (async), lines 308?323: Generate a TOTP secret and QR code URI for the authenticator app.
  Calls: `AuthService.setup_totp`, `PermissionDeniedError`, `router.post`, `token_payload.get`, `uuid.UUID`.
- `verify_2fa_setup` (async), lines 334?342: No function docstring; consult the source body and layer walkthrough.
  Calls: `AuthService.verify_and_enable_totp`, `MessageResponse`, `router.post`, `uuid.UUID`.
- `google_login` (async), lines 353?356: No function docstring; consult the source body and layer walkthrough.
  Calls: `router.get`, `start_google_login`.
- `google_callback` (async), lines 360?363: No function docstring; consult the source body and layer walkthrough.
  Calls: `finish_google_login`, `router.get`.
- `resend_verification` (async), lines 367?391: No function docstring; consult the source body and layer walkthrough.
  Calls: `MessageResponse`, `RedisSettings.from_dsn`, `UserRepository.get_by_email`, `create_email_verify_token`, `create_pool`, `get_redis`, `get_redis().set`, `hashlib.sha256`, `hashlib.sha256(payload.email.lower().encode()).hexdigest`, `payload.email.lower`, `payload.email.lower().encode`, `pool.aclose` ? (15 distinct call expressions).
  Mutation/I-O-related call names: `pool.enqueue_job`.
- `_set_refresh_cookie` (sync), lines 397?400: No function docstring; consult the source body and layer walkthrough.
  Calls: `get_cookie_params`, `params.items`, `params.pop`, `response.set_cookie`.
- `_clear_refresh_cookie` (sync), lines 403?410: No function docstring; consult the source body and layer walkthrough.
  Calls: `response.delete_cookie`.
  Mutation/I-O-related call names: `response.delete_cookie`.
- `_get_ip` (sync), lines 413?417: No function docstring; consult the source body and layer walkthrough.
  Calls: `forwarded.split`, `forwarded.split(',')[0].strip`, `request.headers.get`.

## app/api/v1/cart.py

79 lines; SHA-256 `a06ed197e534a71b17ae20fac1725a4fa354e86cabbba1b051f5ce1a95de19a5`. [Open source](../../app/api/v1/cart.py).

Backend imports: `app.api.deps`, `app.core.redis`, `app.schemas.order`, `app.services.cart_service`.

- `_get_redis` (async), lines 18?20: No function docstring; consult the source body and layer walkthrough.
  Calls: `get_redis`.
- `get_cart` (async), lines 24?26: No function docstring; consult the source body and layer walkthrough.
  Calls: `CartService`, `CartService(db, redis).get_cart`, `UUID`, `_get_redis`, `router.get`.
- `add_to_cart` (async), lines 30?36: No function docstring; consult the source body and layer walkthrough.
  Calls: `CartService`, `CartService(db, redis).add_item`, `UUID`, `_get_redis`, `router.post`.
- `update_cart_item` (async), lines 40?49: No function docstring; consult the source body and layer walkthrough.
  Calls: `CartService`, `CartService(db, redis).update_item`, `UUID`, `_get_redis`, `router.patch`.
- `remove_cart_item` (async), lines 53?60: No function docstring; consult the source body and layer walkthrough.
  Calls: `CartService`, `CartService(db, redis).remove_item`, `Response`, `UUID`, `_get_redis`, `router.delete`.
  Mutation/I-O-related call names: `router.delete`.
- `clear_cart` (async), lines 64?67: No function docstring; consult the source body and layer walkthrough.
  Calls: `CartService`, `CartService(db, redis).clear`, `Response`, `UUID`, `_get_redis`, `router.post`.
- `sync_cart` (async), lines 71?79: Merge guest (localStorage) cart into server cart after login.
  Calls: `CartService`, `CartService(db, redis).sync`, `UUID`, `_get_redis`, `router.post`.

## app/api/v1/customers.py

328 lines; SHA-256 `b3fbc16bf1301b7c27f36849b353f347802fc6bb47e63416342d78a216a627ec`. [Open source](../../app/api/v1/customers.py).

Backend imports: `app.api.deps`, `app.schemas.user`, `app.services.customer_service`.

- `get_profile` (async), lines 54?56: Return the authenticated customer's profile.
  Calls: `CustomerService`, `CustomerService(db).get_profile`, `UUID`, `router.get`.
- `update_profile` (async), lines 60?68: Update first_name, last_name, and/or phone.
  Calls: `CustomerService`, `CustomerService(db).update_profile`, `UUID`, `router.patch`.
- `upload_avatar` (async), lines 72?88: Upload a new profile avatar (JPEG/PNG/WebP, max 2 MB).
  Calls: `CustomerService`, `CustomerService(db).upload_avatar`, `File`, `HTTPException`, `UUID`, `avatar.read`, `len`, `router.post`.
  Mutation/I-O-related call names: `CustomerService(db).upload_avatar`.
- `change_password` (async), lines 92?101: Change account password. Invalidates all existing sessions.
  Calls: `CustomerService`, `CustomerService(db).change_password`, `Response`, `UUID`, `router.post`.
- `list_addresses` (async), lines 109?111: List all saved delivery addresses for the current user.
  Calls: `CustomerService`, `CustomerService(db).list_addresses`, `UUID`, `router.get`.
- `create_address` (async), lines 115?123: Add a new delivery address. Maximum 10 per account.
  Calls: `CustomerService`, `CustomerService(db).create_address`, `UUID`, `router.post`.
- `update_address` (async), lines 127?136: Update an existing address.
  Calls: `CustomerService`, `CustomerService(db).update_address`, `UUID`, `router.patch`.
- `delete_address` (async), lines 140?149: Remove a saved address.
  Calls: `CustomerService`, `CustomerService(db).delete_address`, `Response`, `UUID`, `router.delete`.
  Mutation/I-O-related call names: `CustomerService(db).delete_address`, `router.delete`.
- `set_default_address` (async), lines 153?161: Mark an address as the default shipping address.
  Calls: `CustomerService`, `CustomerService(db).set_default_address`, `UUID`, `router.post`.
- `list_my_reviews` (async), lines 169?178: List reviews written by the current user.
  Calls: `CustomerService`, `CustomerService(db).list_user_reviews`, `Query`, `UUID`, `router.get`.
- `create_review` (async), lines 182?190: Submit a product review. One review per product per customer.
  Calls: `CustomerService`, `CustomerService(db).create_review`, `UUID`, `router.post`.
- `update_review` (async), lines 194?203: Update an existing review (only pending or approved reviews).
  Calls: `CustomerService`, `CustomerService(db).update_review`, `UUID`, `router.patch`.
- `delete_review` (async), lines 207?216: Delete a review authored by the current user.
  Calls: `CustomerService`, `CustomerService(db).delete_review`, `Response`, `UUID`, `router.delete`.
  Mutation/I-O-related call names: `CustomerService(db).delete_review`, `router.delete`.
- `list_product_reviews` (async), lines 222?233: Fetch approved reviews for a product (public).
  Calls: `CustomerService`, `CustomerService(db).list_product_reviews`, `Query`, `router.get`.
- `mark_review_helpful` (async), lines 237?249: Vote a review as helpful or unhelpful. One vote per user per review.
  Calls: `CustomerService`, `CustomerService(db).vote_review`, `Response`, `UUID`, `router.post`.
- `get_wishlist` (async), lines 257?259: Retrieve the current user's wishlist.
  Calls: `CustomerService`, `CustomerService(db).get_wishlist`, `UUID`, `router.get`.
- `add_to_wishlist` (async), lines 263?271: Add a product to the wishlist. Idempotent — duplicate adds are ignored.
  Calls: `CustomerService`, `CustomerService(db).add_to_wishlist`, `UUID`, `router.post`.
- `remove_from_wishlist` (async), lines 275?284: Remove a product from the wishlist.
  Calls: `CustomerService`, `CustomerService(db).remove_from_wishlist`, `Response`, `UUID`, `router.delete`.
  Mutation/I-O-related call names: `router.delete`.
- `get_notification_preferences` (async), lines 292?296: Return current notification preference settings.
  Calls: `CustomerService`, `CustomerService(db).get_notification_prefs`, `UUID`, `router.get`.
- `update_notification_preferences` (async), lines 300?308: Update notification preferences (partial update).
  Calls: `CustomerService`, `CustomerService(db).update_notification_prefs`, `UUID`, `router.patch`.
- `delete_account` (async), lines 316?328: Permanently delete the account. Requires password confirmation and the
  Calls: `CustomerService`, `CustomerService(db).delete_account`, `Response`, `UUID`, `router.delete`.
  Mutation/I-O-related call names: `CustomerService(db).delete_account`, `router.delete`.

## app/api/v1/health.py

56 lines; SHA-256 `82cb37ed913d8756aaedf1d14bc3b2510467bbb710bd657899b52d0141cfee78`. [Open source](../../app/api/v1/health.py).

Backend imports: `app.core.config`, `app.core.database`, `app.core.redis`, `app.schemas.common`.

- `health_check` (async), lines 26?56: Returns OK if both the database and Redis are reachable.
  Calls: `HealthResponse`, `get_db`, `get_redis`, `get_redis().ping`, `router.get`, `session.execute`, `text`.

## app/api/v1/inventory.py

285 lines; SHA-256 `796b3542f3494f40e8dca170d54752f75ccc6fa3481251c68082cec4385f5731`. [Open source](../../app/api/v1/inventory.py).

Backend imports: `app.api.deps`, `app.repositories.inventory_repo`, `app.schemas.common`, `app.services.inventory_service`.

- Class `VariantStockResponse`, lines 38?50; bases: DRIPResponseModel.
  Annotated fields: `variant_id`, `product_id`, `product_name`, `sku`, `size`, `colour`, `stock`, `reserved`, `available`, `reorder_point`, `is_low_stock`, `last_restocked_at`.
- Class `PaginatedVariantStock`, lines 53?58; bases: DRIPResponseModel.
  Annotated fields: `data`, `total`, `page`, `per_page`, `pages`.
- Class `SetStockRequest`, lines 61?79; bases: DRIPBaseModel.
  Annotated fields: `stock`, `reorder_point`.
- `SetStockRequest.stock_non_negative` (sync), lines 67?72: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`.
- `SetStockRequest.reorder_non_negative` (sync), lines 76?79: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`.
- Class `AdjustStockRequest`, lines 82?103; bases: DRIPBaseModel.
  Annotated fields: `delta`, `reason`.
- `AdjustStockRequest.delta_in_range` (sync), lines 88?93: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `abs`, `field_validator`.
- `AdjustStockRequest.reason_not_empty` (sync), lines 97?103: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `len`, `v.strip`.
- Class `StockAdjustmentResponse`, lines 106?111; bases: DRIPResponseModel.
  Annotated fields: `variant_id`, `previous_stock`, `new_stock`, `delta`, `reason`.
- Class `BulkStockUpdateItem`, lines 114?124; bases: DRIPBaseModel.
  Annotated fields: `variant_id`, `stock`, `reason`.
- `BulkStockUpdateItem.stock_non_negative` (sync), lines 121?124: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`.
- Class `BulkStockUpdateRequest`, lines 127?137; bases: DRIPBaseModel.
  Annotated fields: `updates`.
- `BulkStockUpdateRequest.validate_updates` (sync), lines 132?137: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `len`.
- Class `BulkStockUpdateResponse`, lines 140?143; bases: DRIPResponseModel.
  Annotated fields: `updated`, `failed`, `errors`.
- Class `LowStockResponse`, lines 146?148; bases: DRIPResponseModel.
  Annotated fields: `data`, `total`.
- `list_seller_inventory` (async), lines 156?177: List all product variants and their current stock levels for the
  Calls: `InventoryService`, `InventoryService(db).list_seller_inventory`, `Query`, `router.get`.
- `get_low_stock_alerts` (async), lines 181?190: Return all variants whose current stock is at or below the reorder point.
  Calls: `InventoryService`, `InventoryService(db).get_low_stock`, `router.get`.
- `get_variant_stock` (async), lines 194?203: Get stock details for a single variant owned by this seller.
  Calls: `InventoryService`, `InventoryService(db).get_variant_stock`, `router.get`.
- `set_variant_stock` (async), lines 207?223: Set the absolute stock quantity for a variant. Use this for manual stock
  Calls: `InventoryService`, `InventoryService(db).set_stock`, `router.put`.
- `adjust_variant_stock` (async), lines 227?243: Apply a relative stock adjustment (e.g. +50 for a restock, -3 for
  Calls: `InventoryService`, `InventoryService(db).adjust_stock`, `router.post`.
- `admin_list_inventory` (async), lines 251?270: Admin: View inventory across all sellers with optional filters.
  Calls: `InventoryService`, `InventoryService(db).admin_list_inventory`, `Query`, `router.get`.
- `admin_bulk_update_inventory` (async), lines 274?285: Admin: Bulk-correct stock levels across any variants. Used after CSV
  Calls: `InventoryService`, `InventoryService(db).bulk_update_stock`, `router.post`.

## app/api/v1/notifications.py

104 lines; SHA-256 `047179abe93eed55220a1152d3e5e5d4ad449b07b1c3360141a117357d0e3bbe`. [Open source](../../app/api/v1/notifications.py).

Backend imports: `app.api.deps`, `app.schemas.notification`, `app.services.notification_service`.

- `list_notifications` (async), lines 24?36: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationService`, `NotificationService(db).list_notifications`, `Query`, `UUID`, `router.get`.
- `mark_notification_read` (async), lines 40?49: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationService`, `NotificationService(db).mark_read`, `UUID`, `router.post`.
- `mark_all_read` (async), lines 53?58: No function docstring; consult the source body and layer walkthrough.
  Calls: `MarkReadResponse`, `NotificationService`, `NotificationService(db).mark_all_read`, `UUID`, `router.post`.
- `get_preferences` (async), lines 62?66: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationService`, `NotificationService(db).get_preferences`, `UUID`, `router.get`.
- `update_preferences` (async), lines 70?77: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationService`, `NotificationService(db).update_preferences`, `UUID`, `router.patch`.
- `broadcast_notification` (async), lines 84?91: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationService`, `NotificationService(db).broadcast`, `UUID`, `router.post`.
- `get_email_log` (async), lines 95?104: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationService`, `NotificationService(db).get_email_log`, `Query`, `router.get`.

## app/api/v1/orders.py

175 lines; SHA-256 `8a6471ecc4dbb17664a333e484e5b82b221e62e6f7359847c1fd8b986f44d857`. [Open source](../../app/api/v1/orders.py).

Backend imports: `app.api.deps`, `app.core.redis`, `app.schemas.order`, `app.services.coupon_service`, `app.services.order_access`, `app.services.order_service`.

- `_get_redis` (async), lines 31?34: No function docstring; consult the source body and layer walkthrough.
  Calls: `get_redis`.
- `place_order` (async), lines 41?49: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db, redis).create_order`, `UUID`, `_get_redis`, `router.post`.
- `place_guest_order` (async), lines 53?57: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).create_guest_order`, `router.post`.
- `quote_guest_checkout` (async), lines 61?65: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).quote_guest_checkout`, `router.post`.
- `list_orders` (async), lines 69?74: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).get_customer_orders`, `Query`, `UUID`, `router.get`.
- `get_order_by_number` (async), lines 78?87: No function docstring; consult the source body and layer walkthrough.
  Calls: `Header`, `OrderService`, `OrderService(db).get_order_by_number`, `Query`, `UUID`, `router.get`.
- `get_order` (async), lines 91?102: No function docstring; consult the source body and layer walkthrough.
  Calls: `Header`, `OrderService._to_detail`, `UUID`, `authorized_order`, `router.get`.
- `cancel_order` (async), lines 106?118: No function docstring; consult the source body and layer walkthrough.
  Calls: `Header`, `OrderService`, `OrderService(db).cancel_order`, `UUID`, `router.post`.
- `validate_coupon` (async), lines 125?130: No function docstring; consult the source body and layer walkthrough.
  Calls: `CouponService`, `CouponService(db).validate`, `UUID`, `router.post`.
- `list_seller_orders` (async), lines 137?149: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).get_seller_orders`, `Query`, `UUID`, `router.get`.
- `get_seller_order` (async), lines 153?161: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).get_seller_order_detail`, `UUID`, `router.get`.
- `update_seller_order_status` (async), lines 165?175: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderService`, `OrderService(db).update_seller_order_status`, `UUID`, `router.put`.

## app/api/v1/payments.py

231 lines; SHA-256 `e7df34d40faf9f602f16b0dcd7742f7f79217c1d51a119de4b00f117e7775a0f`. [Open source](../../app/api/v1/payments.py).

Backend imports: `app.api.deps`, `app.core.config`, `app.schemas.payment`, `app.services.payment_service`.

- `initiate_payment` (async), lines 41?54: Initiate a PayFast or COD payment for an order.
  Calls: `Header`, `PaymentService`, `PaymentService(db).initiate`, `UUID`, `_client_ip`, `router.post`.
- `get_payment_status` (async), lines 58?68: No function docstring; consult the source body and layer walkthrough.
  Calls: `Header`, `PaymentService`, `PaymentService(db).get_status`, `UUID`, `router.get`.
- `retry_payment` (async), lines 72?86: No function docstring; consult the source body and layer walkthrough.
  Calls: `Header`, `PaymentService`, `PaymentService(db).retry`, `UUID`, `_client_ip`, `router.post`.
- `_matches_ip` (sync), lines 92?97: No function docstring; consult the source body and layer walkthrough.
  Calls: `any`, `ipaddress.ip_address`, `ipaddress.ip_network`.
- `_client_ip` (sync), lines 100?113: Trust forwarding headers only from explicitly configured reverse proxies.
  Calls: `_matches_ip`, `forwarded.split`, `forwarded.split(',', 1)[0].strip`, `ipaddress.ip_address`, `request.headers.get`, `str`.
- `payfast_callback` (async), lines 117?139: No function docstring; consult the source body and layer walkthrough.
  Calls: `HTTPException`, `PaymentService`, `PaymentService(db).handle_payfast_callback`, `_client_ip`, `_matches_ip`, `callback_data.update`, `dict`, `int`, `len`, `request.body`, `request.form`, `request.headers.get` ? (13 distinct call expressions).
- `gateway_status` (async), lines 146?147: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentService`, `PaymentService(db).gateway_status`, `router.get`.
- `reconcile_payfast_payment` (async), lines 151?155: Query PayFast for a missed callback and safely reconcile the order.
  Calls: `PaymentService`, `PaymentService(db).reconcile_payfast`, `router.post`.
- `list_payments` (async), lines 159?168: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentService`, `PaymentService(db).list_admin`, `Query`, `router.get`.
- `list_refunds` (async), lines 172?181: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentService`, `PaymentService(db).list_admin_refunds`, `Query`, `router.get`.
- `get_refund` (async), lines 185?190: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentService`, `PaymentService(db).get_admin_refund`, `router.get`.
- `get_payment_refunds` (async), lines 194?199: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentService`, `PaymentService(db).get_payment_refund_history`, `router.get`.
- `refund_payment` (async), lines 203?213: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentService`, `PaymentService(db).refund`, `UUID`, `router.post`.
- `confirm_refund` (async), lines 217?222: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentService`, `PaymentService(db).confirm_refund`, `UUID`, `router.post`.
- `record_cod_collection` (async), lines 226?231: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentService`, `PaymentService(db).record_cod_collection`, `UUID`, `router.post`.

## app/api/v1/products.py

300 lines; SHA-256 `d8d9c4e4e890d9bf1d1f6ceb04bba022f8219f5c94c0a11b03efe5faf44657a0`. [Open source](../../app/api/v1/products.py).

Backend imports: `app.api.deps`, `app.schemas.product`, `app.schemas.user`, `app.services.customer_service`, `app.services.image_service`, `app.services.product_service`.

- `list_products` (async), lines 36?66: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).get_catalogue`, `Query`, `router.get`.
- `search_suggestions` (async), lines 70?74: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).search_suggestions`, `Query`, `router.get`.
- `get_product_by_slug` (async), lines 78?79: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).get_product_by_slug`, `router.get`.
- `get_product` (async), lines 83?84: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).get_product_detail`, `router.get`.
- `get_product_variants` (async), lines 88?89: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).get_variants`, `router.get`.
- `get_product_reviews` (async), lines 93?102: No function docstring; consult the source body and layer walkthrough.
  Calls: `CustomerService`, `CustomerService(db).list_product_reviews`, `ProductService`, `ProductService(db).get_variants`, `Query`, `router.get`.
- `submit_review` (async), lines 106?114: No function docstring; consult the source body and layer walkthrough.
  Calls: `CustomerService`, `CustomerService(db).create_review`, `HTTPException`, `UUID`, `router.post`.
- `list_seller_products` (async), lines 123?132: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).get_seller_products`, `Query`, `UUID`, `router.get`.
- `create_product` (async), lines 136?142: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).create_product`, `UUID`, `router.post`.
- `update_product` (async), lines 146?153: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).update_product`, `UUID`, `router.put`.
- `delete_product` (async), lines 157?164: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).delete_product`, `Response`, `UUID`, `router.delete`.
  Mutation/I-O-related call names: `ProductService(db).delete_product`, `router.delete`.
- `publish_product` (async), lines 168?174: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).publish_product`, `UUID`, `router.post`.
- `unpublish_product` (async), lines 178?184: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).unpublish_product`, `UUID`, `router.post`.
- `upload_product_images` (async), lines 190?214: No function docstring; consult the source body and layer walkthrough.
  Calls: `File`, `HTTPException`, `ImageService`, `ProductService`, `ProductService(db).add_images`, `UUID`, `UploadImagesResponse`, `image_svc.process_and_upload`, `len`, `router.post`, `service._require_owned`, `str` ? (14 distinct call expressions).
  Mutation/I-O-related call names: `image_svc.process_and_upload`, `upload.read`.
- `admin_list_products` (async), lines 223?230: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).admin_list`, `Query`, `router.get`.
- `admin_hide_product` (async), lines 234?239: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).set_hidden`, `router.post`.
- `seller_product_detail` (async), lines 246?247: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).get_seller_detail`, `UUID`, `router.get`.
- `add_variant` (async), lines 253?258: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).add_variant`, `UUID`, `router.post`.
- `update_variant` (async), lines 264?273: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).update_variant`, `UUID`, `router.patch`.
- `reorder_images` (async), lines 277?282: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).reorder_images`, `UUID`, `router.put`.
- `primary_image` (async), lines 286?289: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).primary_image`, `UUID`, `router.put`.
- `delete_image` (async), lines 293?295: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).delete_image`, `Response`, `UUID`, `router.delete`.
  Mutation/I-O-related call names: `ProductService(db).delete_image`, `router.delete`.
- `unhide_product` (async), lines 299?300: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).set_hidden`, `router.post`.

## app/api/v1/returns.py

276 lines; SHA-256 `2fab708d5e3c0ee01eb1fa1a43e7153afcdb5af7d1b9d3aa3b250728281acf07`. [Open source](../../app/api/v1/returns.py).

Backend imports: `app.api.deps`, `app.schemas.return_`, `app.services.return_service`.

- `request_guest_return` (async), lines 32?37: No function docstring; consult the source body and layer walkthrough.
  Calls: `Header`, `ReturnService`, `ReturnService(db).request_guest_return`, `router.post`.
- `get_guest_return` (async), lines 41?46: No function docstring; consult the source body and layer walkthrough.
  Calls: `Header`, `ReturnService`, `ReturnService(db).get_guest_return`, `router.get`.
- `request_return` (async), lines 50?55: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).request_return`, `UUID`, `router.post`.
- `list_returns` (async), lines 59?64: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `ReturnService`, `ReturnService(db).list_returns`, `UUID`, `router.get`.
- `get_return` (async), lines 68?73: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).get_return`, `UUID`, `router.get`.
- `open_dispute` (async), lines 77?83: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).open_dispute`, `UUID`, `router.post`.
- `get_dispute` (async), lines 87?92: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).get_dispute`, `UUID`, `router.get`.
- `add_dispute_message` (async), lines 96?102: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).add_message`, `UUID`, `router.post`.
- `seller_list_returns` (async), lines 108?119: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `ReturnService`, `ReturnService(db).seller_list_returns`, `UUID`, `router.get`.
- `seller_get_return` (async), lines 123?130: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).get_seller_return`, `UUID`, `router.get`.
- `seller_approve_return` (async), lines 134?142: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).seller_approve_return`, `UUID`, `router.post`.
- `seller_reject_return` (async), lines 146?154: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).seller_reject_return`, `UUID`, `router.post`.
- `seller_mark_received` (async), lines 158?166: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).seller_mark_received`, `UUID`, `router.post`.
- `admin_list_returns` (async), lines 170?179: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `ReturnService`, `ReturnService(db).admin_list_returns`, `router.get`.
- `admin_get_return` (async), lines 183?188: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).get_admin_return`, `router.get`.
- `admin_approve_return` (async), lines 192?198: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).approve_return`, `UUID`, `router.post`.
- `admin_reject_return` (async), lines 202?208: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).reject_return`, `UUID`, `router.post`.
- `admin_mark_received` (async), lines 212?218: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).mark_received`, `UUID`, `router.post`.
- `admin_process_refund` (async), lines 222?228: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).process_refund`, `UUID`, `router.post`.
- `admin_list_disputes` (async), lines 232?241: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `ReturnService`, `ReturnService(db).admin_list_disputes`, `router.get`.
- `admin_get_dispute` (async), lines 245?250: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).get_admin_dispute`, `router.get`.
- `admin_add_dispute_message` (async), lines 258?266: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).add_admin_message`, `UUID`, `router.post`.
- `admin_resolve_dispute` (async), lines 270?276: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnService`, `ReturnService(db).resolve_dispute`, `UUID`, `router.post`.

## app/api/v1/router.py

59 lines; SHA-256 `3832373275669e80a91256c56d69297d93608aacab5b38981db147d80cdee526`. [Open source](../../app/api/v1/router.py).

Backend imports: `app.api.v1`, `app.api.v1.admin`, `app.api.v1.admin.reviews`, `app.api.v1.analytics`, `app.api.v1.auth`, `app.api.v1.health`.


## app/api/v1/sellers.py

138 lines; SHA-256 `e9153e1f25c9130b95cbf10b7e532ec8c65d9866dbebe4b6074b2f2d4bc74963`. [Open source](../../app/api/v1/sellers.py).

Backend imports: `app.api.deps`, `app.core.config`, `app.core.exceptions`, `app.repositories.seller_repo`, `app.schemas.seller`, `app.services.image_service`, `app.services.seller_service`, `app.services.slot_service`.

- `register_seller` (async), lines 37?39: Creates a new User (role=seller) and Seller profile in one step. No auth required.
  Calls: `SellerService`, `SellerService(db).register`, `router.post`.
- `get_slot_pricing` (async), lines 43?47: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `SlotService`, `SlotService(db).get_pricing`, `router.get`.
- `get_seller_profile` (async), lines 54?55: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerService`, `SellerService(db).get_profile`, `UUID`, `router.get`.
- `update_seller_profile` (async), lines 59?64: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerService`, `SellerService(db).update_profile`, `UUID`, `router.patch`.
- `upload_logo` (async), lines 68?88: No function docstring; consult the source body and layer walkthrough.
  Calls: `File`, `HTTPException`, `ImageService`, `ImageService().process_and_upload`, `NotFoundError`, `SellerRepository`, `SellerRepository(db).get_by_user_id`, `SellerService`, `SellerService(db).update_logo`, `UUID`, `len`, `logo.read` ? (14 distinct call expressions).
  Mutation/I-O-related call names: `ImageService().process_and_upload`.
- `purchase_slots` (async), lines 95?98: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotService`, `SlotService(db).purchase_slots`, `UUID`, `router.post`.
- `get_dashboard` (async), lines 105?110: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `SellerService`, `SellerService(db).get_dashboard`, `UUID`, `router.get`.
- `list_bank_accounts` (async), lines 120?121: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerService`, `SellerService(db).list_bank_accounts`, `UUID`, `router.get`.
- `add_bank_account` (async), lines 125?130: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerService`, `SellerService(db).add_bank_account`, `UUID`, `router.post`.
- `delete_bank_account` (async), lines 134?138: No function docstring; consult the source body and layer walkthrough.
  Calls: `Response`, `SellerService`, `SellerService(db).delete_bank_account`, `UUID`, `router.delete`.
  Mutation/I-O-related call names: `SellerService(db).delete_bank_account`, `router.delete`.

## app/api/v1/storefront.py

142 lines; SHA-256 `d7737f6071840b167add1ec29234186e5b830872304fdf5af8db30ae20160f74`. [Open source](../../app/api/v1/storefront.py).

Backend imports: `app.api.deps`, `app.core.exceptions`, `app.models.admin`, `app.models.product`, `app.models.seller`, `app.schemas.admin`, `app.schemas.product`, `app.services.product_service`.

- `brand_response` (sync), lines 24?38: No function docstring; consult the source body and layer walkthrough.
  Calls: `getattr`.
- `categories` (async), lines 42?76: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.name, Category.id))).all`, `Category.is_active.is_`, `db.scalars`, `is_visible`, `next`, `router.get`, `seen.add`, `select`, `select(Category).where`, `select(Category).where(Category.is_active.is_(True)).order_by`, `set`.
- `categories.is_visible` (sync), lines 53?61: No function docstring; consult the source body and layer walkthrough.
  Calls: `is_visible`, `next`, `seen.add`, `set`.
- `brands` (async), lines 80?100: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await db.scalars(query.order_by(Seller.brand_name, Seller.id).offset((page - 1) * per_page).limit(per_page))).all`, `Query`, `Seller.brand_name.ilike`, `Seller.deleted_at.is_`, `brand_response`, `db.scalar`, `db.scalars`, `func.count`, `query.order_by`, `query.order_by(Seller.brand_name, Seller.id).offset`, `query.order_by(Seller.brand_name, Seller.id).offset((page - 1) * per_page).limit`, `query.subquery` ? (17 distinct call expressions).
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `brand_detail` (async), lines 104?112: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `Seller.deleted_at.is_`, `brand_response`, `db.scalar`, `router.get`, `select`, `select(Seller).where`.
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `brand_products` (async), lines 116?126: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductService`, `ProductService(db).get_catalogue`, `Query`, `brand_detail`, `router.get`.
- `public_banners` (async), lines 130?142: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await db.scalars(query.order_by(Banner.sort_order, Banner.id))).all`, `Banner.is_active.is_`, `Banner.valid_from.is_`, `Banner.valid_until.is_`, `Query`, `datetime.now`, `db.scalars`, `list`, `or_`, `query.order_by`, `query.where`, `router.get` ? (14 distinct call expressions).

## app/api/v1/wallet.py

164 lines; SHA-256 `ebc7af73effe3b2eddda1f752e393c0f6e99e4d7e1f8bb7b883acb37bf2ab1b9`. [Open source](../../app/api/v1/wallet.py).

Backend imports: `app.api.deps`, `app.schemas.wallet`, `app.services.wallet_service`.

- `get_wallet_summary` (async), lines 26?29: No function docstring; consult the source body and layer walkthrough.
  Calls: `UUID`, `WalletService`, `WalletService(db).get_summary`, `router.get`.
- `get_wallet_transactions` (async), lines 33?48: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `UUID`, `WalletService`, `WalletService(db).get_transactions`, `router.get`.
- `request_withdrawal` (async), lines 52?59: No function docstring; consult the source body and layer walkthrough.
  Calls: `UUID`, `WalletService`, `WalletService(db).request_withdrawal`, `router.post`.
- `get_payout_history` (async), lines 63?76: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `UUID`, `WalletService`, `WalletService(db).get_payouts`, `router.get`.
- `get_commission_breakdown` (async), lines 80?92: No function docstring; consult the source body and layer walkthrough.
  Calls: `Query`, `UUID`, `WalletService`, `WalletService(db).get_commission_breakdown`, `router.get`.
- `admin_wallet_overview` (async), lines 98?101: No function docstring; consult the source body and layer walkthrough.
  Calls: `WalletService`, `WalletService(db).admin_overview`, `router.get`.
- `admin_list_payouts` (async), lines 105?128: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaginatedPayouts`, `PayoutResponse`, `Query`, `WalletService`, `WalletService(db).payout_repo.list_admin`, `max`, `router.get`.
- `admin_approve_payout` (async), lines 132?142: No function docstring; consult the source body and layer walkthrough.
  Calls: `UUID`, `WalletService`, `WalletService(db).admin_approve_payout`, `router.post`.
- `admin_reject_payout` (async), lines 146?159: No function docstring; consult the source body and layer walkthrough.
  Calls: `HTTPException`, `UUID`, `WalletService`, `WalletService(db).admin_reject_payout`, `router.post`.
- `admin_complete_payout` (async), lines 163?164: No function docstring; consult the source body and layer walkthrough.
  Calls: `UUID`, `WalletService`, `WalletService(db).admin_complete_payout`, `router.post`.



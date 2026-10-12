# Backend source index: services-a

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## app/services/admin_service.py

472 lines; SHA-256 `9ebff6468a75e712e90152965e2065b338fb5836086b21cd41ecf76b161fe0ad`. [Open source](../../app/services/admin_service.py).

Backend imports: `app.core.exceptions`, `app.models.admin`, `app.models.order`, `app.models.product`, `app.models.seller`, `app.models.user`, `app.models.wallet`, `app.repositories.inventory_repo`, `app.repositories.order_repo`, `app.repositories.seller_repo`, `app.schemas.admin`, `app.services.platform_settings`, `app.services.revenue`.

- Class `AdminService`, lines 39-472; bases: .
- `AdminService.__init__` (sync), lines 40-41: No function docstring; consult the source body and layer walkthrough.
- `AdminService.get_dashboard` (async), lines 45-86: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminDashboardResponse`, `Decimal`, `Order.status.in_`, `Seller.deleted_at.is_`, `count`, `datetime.now`, `func.coalesce`, `func.count`, `func.sum`, `now.replace`, `pending_payouts_r.scalar_one`, `r.scalar_one` ... (21 distinct call expressions).
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `AdminService.get_dashboard.count` (async), lines 50-52: No function docstring; consult the source body and layer walkthrough.
  Calls: `func.count`, `r.scalar_one`, `select`, `select(func.count(model.id)).where`, `self.db.execute`.
- `AdminService.get_dashboard.sum_col` (async), lines 54-56: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `func.coalesce`, `func.sum`, `r.scalar_one`, `select`, `select(func.coalesce(func.sum(col), 0)).where`, `self.db.execute`.
- `AdminService.list_sellers` (async), lines 90-131: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `AdminSellerRowResponse`, `PaginatedAdminSellers`, `Seller.brand_name.ilike`, `Seller.deleted_at.is_`, `SellerStatus`, `desc`, `func.count`, `max`, `query.order_by`, `query.order_by(desc(Seller.created_at)).offset`, `query.order_by(desc(Seller.created_at)).offset((page - 1) * per_page).limit` ... (26 distinct call expressions).
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `AdminService.get_seller` (async), lines 133-166: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminSellerDetailResponse`, `NotFoundError`, `Seller.deleted_at.is_`, `result.scalar_one_or_none`, `select`, `select(Seller).options`, `select(Seller).options(selectinload(Seller.wallet)).where`, `selectinload`, `self._count_products`, `self._seller_commission`, `self._seller_gmv`, `self.db.execute`.
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `AdminService.approve_seller` (async), lines 168-183: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `datetime.utcnow`, `self._get_seller`, `self.db.commit`, `self.db.execute`, `update`, `update(Seller).where`, `update(Seller).where(Seller.id == seller_id).values`.
  Mutation/I-O-related call names: `self.db.commit`.
- `AdminService.reject_seller` (async), lines 185-198: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `datetime.utcnow`, `self._get_seller`, `self.db.commit`, `self.db.execute`, `update`, `update(Seller).where`, `update(Seller).where(Seller.id == seller_id).values`.
  Mutation/I-O-related call names: `self.db.commit`.
- `AdminService.suspend_seller` (async), lines 200-218: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Product.deleted_at.is_`, `datetime.utcnow`, `self._get_seller`, `self.db.commit`, `self.db.execute`, `update`, `update(Product).where`, `update(Product).where(Product.seller_id == seller_id, Product.deleted_at.is_(None)).values`, `update(Seller).where`, `update(Seller).where(Seller.id == seller_id).values`.
  Mutation/I-O-related call names: `Product.deleted_at.is_`, `self.db.commit`, `update(Product).where(Product.seller_id == seller_id, Product.deleted_at.is_(None)).values`.
- `AdminService.reinstate_seller` (async), lines 220-239: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Product.deleted_at.is_`, `datetime.utcnow`, `self._get_seller`, `self.db.commit`, `self.db.execute`, `update`, `update(Product).where`, `update(Product).where(Product.seller_id == seller_id, Product.deleted_at.is_(None)).values`, `update(Seller).where`, `update(Seller).where(Seller.id == seller_id).values`.
  Mutation/I-O-related call names: `Product.deleted_at.is_`, `self.db.commit`, `update(Product).where(Product.seller_id == seller_id, Product.deleted_at.is_(None)).values`.
- `AdminService.list_orders` (async), lines 243-309: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `AdminOrderRowResponse`, `Order.id.in_`, `OrderStatus`, `OrderTotals`, `PaginatedAdminOrders`, `SellerOrder.order_id.in_`, `commission_total_r.scalar_one`, `desc`, `func.coalesce`, `func.count`, `func.sum` ... (35 distinct call expressions).
- `AdminService.list_cod_queue` (async), lines 313-350: No function docstring; consult the source body and layer walkthrough.
  Calls: `(expires_at - now).total_seconds`, `CODQueueItem`, `datetime.now`, `get_platform_settings`, `int`, `items.append`, `list`, `max`, `o.created_at.replace`, `result.scalars`, `result.scalars().all`, `select` ... (19 distinct call expressions).
- `AdminService.verify_cod` (async), lines 352-362: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `OrderRepository`, `repo.get_by_id`, `repo.update_status`, `self.db.commit`.
  Mutation/I-O-related call names: `self.db.commit`.
- `AdminService.cancel_cod` (async), lines 364-391: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `InventoryRepository`, `NotFoundError`, `OrderRepository`, `SellerOrderRepository`, `inv_repo.release`, `order_repo.get_by_id`, `order_repo.update_status`, `self.db.commit`, `so_repo.update_status`.
  Mutation/I-O-related call names: `self.db.commit`.
- `AdminService.list_banners` (async), lines 395-399: No function docstring; consult the source body and layer walkthrough.
  Calls: `BannerResponse.model_validate`, `result.scalars`, `result.scalars().all`, `select`, `select(Banner).order_by`, `self.db.execute`.
- `AdminService.create_banner` (async), lines 401-407: No function docstring; consult the source body and layer walkthrough.
  Calls: `Banner`, `BannerResponse.model_validate`, `self.db.add`, `self.db.commit`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.commit`, `self.db.flush`.
- `AdminService.delete_banner` (async), lines 409-415: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `result.scalar_one_or_none`, `select`, `select(Banner).where`, `self.db.commit`, `self.db.delete`, `self.db.execute`.
  Mutation/I-O-related call names: `self.db.commit`, `self.db.delete`.
- `AdminService.get_settings` (async), lines 419-421: No function docstring; consult the source body and layer walkthrough.
  Calls: `get_platform_settings`.
- `AdminService.update_settings` (async), lines 423-439: No function docstring; consult the source body and layer walkthrough.
  Calls: `UpdateSettingsRequest.model_validate`, `UpdateSettingsRequest.model_validate(updates).model_dump`, `datetime.now`, `insert`, `insert(SystemSetting).values`, `self.db.commit`, `self.db.execute`, `self.get_settings`, `statement.on_conflict_do_update`, `str`, `updates.items`.
  Mutation/I-O-related call names: `self.db.commit`.
- `AdminService._get_seller` (async), lines 443-450: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `Seller.deleted_at.is_`, `result.scalar_one_or_none`, `select`, `select(Seller).where`, `self.db.execute`.
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `AdminService._count_products` (async), lines 452-460: No function docstring; consult the source body and layer walkthrough.
  Calls: `Product.deleted_at.is_`, `Product.is_published.is_`, `func.count`, `result.scalar_one`, `select`, `select(func.count(Product.id)).where`, `self.db.execute`.
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `AdminService._seller_commission` (async), lines 462-467: No function docstring; consult the source body and layer walkthrough.
  Calls: `func.coalesce`, `func.sum`, `result.scalar_one`, `select`, `select(func.coalesce(func.sum(CommissionLedger.commission_amount), 0)).where`, `self.db.execute`.
- `AdminService._seller_gmv` (async), lines 469-472: No function docstring; consult the source body and layer walkthrough.
  Calls: `func.coalesce`, `func.sum`, `select`, `select(func.coalesce(func.sum(SellerOrder.subtotal), 0)).where`, `self.db.scalar`.

## app/services/analytics_service.py

601 lines; SHA-256 `79853701f0c1d67c465636f9a6cfd9a13b0c5a3447834cc2ffb799792868ce8c`. [Open source](../../app/services/analytics_service.py).

Backend imports: `app.models.analytics`, `app.models.order`, `app.models.product`, `app.models.seller`, `app.models.user`, `app.models.wallet`, `app.schemas.analytics`, `app.services.revenue`.

- `_period_to_days` (sync), lines 41-42: No function docstring; consult the source body and layer walkthrough.
  Calls: `{'7d': 7, '30d': 30, '90d': 90, '1y': 365}.get`.
- `_date_from` (sync), lines 45-46: No function docstring; consult the source body and layer walkthrough.
  Calls: `_period_to_days`, `datetime.now`, `timedelta`.
- `_trunc` (sync), lines 49-50: No function docstring; consult the source body and layer walkthrough.
  Calls: `{'day': 'day', 'week': 'week', 'month': 'month'}.get`.
- Class `SellerAnalyticsService`, lines 56-250; bases: .
- `SellerAnalyticsService.__init__` (sync), lines 57-58: No function docstring; consult the source body and layer walkthrough.
- `SellerAnalyticsService.get_overview` (async), lines 60-118: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(comm_q)).one`, `(await self.db.execute(units_q)).scalar_one`, `(await self.db.execute(views_q)).scalar_one`, `Order.status.in_`, `OrderItem.order_id.in_`, `SellerAnalyticsOverview`, `_date_from`, `func.coalesce`, `func.count`, `func.sum`, `int`, `round` ... (19 distinct call expressions).
- `SellerAnalyticsService.get_revenue_series` (async), lines 120-158: No function docstring; consult the source body and layer walkthrough.
  Calls: `RevenueDayRow`, `RevenueSeriesResponse`, `_date_from`, `_trunc`, `func.count`, `func.count(CommissionLedger.id).label`, `func.date_trunc`, `func.date_trunc(trunc_unit, CommissionLedger.settled_at).label`, `func.sum`, `func.sum(CommissionLedger.commission_amount).label`, `func.sum(CommissionLedger.gross_amount).label`, `func.sum(CommissionLedger.seller_amount).label` ... (20 distinct call expressions).
- `SellerAnalyticsService.get_top_products` (async), lines 160-219: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(q)).all`, `Order.status.in_`, `OrderItem.order_id.in_`, `Product.deleted_at.is_`, `TopProductRow`, `TopProductsResponse`, `_date_from`, `and_`, `desc`, `float`, `func.coalesce`, `func.coalesce(func.sum(OrderItem.quantity), 0).label` ... (25 distinct call expressions).
  Mutation/I-O-related call names: `Product.deleted_at.is_`, `select(Product.id, Product.name, Product.view_count, Product.avg_rating, func.coalesce(func.sum(OrderItem.quantity), 0).label('units_sold'), func.coalesce(func.sum(OrderItem.subtotal), 0).label('revenue')).outerjoin(OrderItem, and_(OrderItem.product_id == Product.id, OrderItem.order_id.in_(valid_orders))).where(Product.seller_id == seller_id, Product.deleted_at.is_(None)).group_by`.
- `SellerAnalyticsService.get_inventory_health` (async), lines 221-250: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(q)).one`, `InventoryHealthResponse`, `Product.deleted_at.is_`, `ProductVariant.is_active.is_`, `and_`, `case`, `func.coalesce`, `func.coalesce(func.sum(avail), 0).label`, `func.count`, `func.count(ProductVariant.id).label`, `func.sum`, `func.sum(case((and_(avail > 0, avail <= LOW_STOCK_THRESHOLD), 1), else_=0)).label` ... (20 distinct call expressions).
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- Class `AdminAnalyticsService`, lines 256-601; bases: .
- `AdminAnalyticsService.__init__` (sync), lines 257-258: No function docstring; consult the source body and layer walkthrough.
- `AdminAnalyticsService.get_platform_analytics` (async), lines 260-323: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(q)).scalar_one`, `Order.status.in_`, `PlatformAnalytics`, `_date_from`, `func.coalesce`, `func.count`, `func.sum`, `int`, `round`, `scalar`, `select`, `select(func.coalesce(func.sum(CommissionLedger.commission_amount), 0)).where` ... (18 distinct call expressions).
- `AdminAnalyticsService.get_platform_analytics.scalar` (async), lines 263-264: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(q)).scalar_one`, `self.db.execute`.
- `AdminAnalyticsService.get_platform_revenue` (async), lines 325-356: No function docstring; consult the source body and layer walkthrough.
  Calls: `RevenueDayRow`, `RevenueSeriesResponse`, `_date_from`, `_trunc`, `func.count`, `func.count(CommissionLedger.id).label`, `func.date_trunc`, `func.date_trunc(trunc_unit, CommissionLedger.settled_at).label`, `func.sum`, `func.sum(CommissionLedger.commission_amount).label`, `func.sum(CommissionLedger.gross_amount).label`, `func.sum(CommissionLedger.seller_amount).label` ... (20 distinct call expressions).
- `AdminAnalyticsService.get_top_sellers` (async), lines 358-397: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(q)).all`, `Seller.deleted_at.is_`, `TopSellerRow`, `TopSellersResponse`, `_date_from`, `and_`, `desc`, `func.coalesce`, `func.coalesce(func.sum(CommissionLedger.commission_amount), 0).label`, `func.coalesce(func.sum(CommissionLedger.gross_amount), 0).label`, `func.count`, `func.count(CommissionLedger.id).label` ... (22 distinct call expressions).
  Mutation/I-O-related call names: `Seller.deleted_at.is_`, `select(Seller.id, Seller.brand_name, Seller.logo_url, func.coalesce(func.sum(CommissionLedger.gross_amount), 0).label('gmv'), func.coalesce(func.sum(CommissionLedger.commission_amount), 0).label('commission'), func.count(CommissionLedger.id).label('order_count')).outerjoin(CommissionLedger, and_(CommissionLedger.seller_id == Seller.id, CommissionLedger.settled_at >= date_from)).where(Seller.deleted_at.is_(None)).group_by`, `select(Seller.id, Seller.brand_name, Seller.logo_url, func.coalesce(func.sum(CommissionLedger.gross_amount), 0).label('gmv'), func.coalesce(func.sum(CommissionLedger.commission_amount), 0).label('commission'), func.count(CommissionLedger.id).label('order_count')).outerjoin(CommissionLedger, and_(CommissionLedger.seller_id == Seller.id, CommissionLedger.settled_at >= date_from)).where(Seller.deleted_at.is_(None)).group_by(Seller.id).order_by`, `select(Seller.id, Seller.brand_name, Seller.logo_url, func.coalesce(func.sum(CommissionLedger.gross_amount), 0).label('gmv'), func.coalesce(func.sum(CommissionLedger.commission_amount), 0).label('commission'), func.count(CommissionLedger.id).label('order_count')).outerjoin(CommissionLedger, and_(CommissionLedger.seller_id == Seller.id, CommissionLedger.settled_at >= date_from)).where(Seller.deleted_at.is_(None)).group_by(Seller.id).order_by(desc('gmv')).limit`.
- `AdminAnalyticsService.get_cohort` (async), lines 399-443: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(text("\n            WITH first_orders AS (\n                SELECT user_id, date_trunc('month', min(created_at)) AS cohort\n                FROM orders WHERE user_id IS NOT NULL AND status IN\n                  ('payment_confirmed','processing','shipped','delivered','completed')\n                GROUP BY user_id\n            ), sizes AS (\n                SELECT cohort, count(*) AS size FROM first_orders WHERE cohort >= :start GROUP BY cohort\n            ), activity AS (\n                SELECT f.cohort, date_trunc('month', o.created_at) AS active_month,\n                       count(DISTINCT o.user_id) AS active\n                FROM first_orders f JOIN orders o ON o.user_id=f.user_id\n                WHERE f.cohort >= :start AND o.status IN\n                  ('payment_confirmed','processing','shipped','delivered','completed')\n                GROUP BY f.cohort, active_month\n            )\n            SELECT s.cohort, s.size, a.active_month, a.active FROM sizes s\n            JOIN activity a ON a.cohort=s.cohort ORDER BY s.cohort, a.active_month\n        "), {'start': start})).all`, `CohortResponse`, `CohortRow`, `cohorts.values`, `datetime`, `datetime.now`, `list`, `range`, `round`, `row.cohort.strftime`, `self.db.execute`, `text`.
- `AdminAnalyticsService.get_payment_methods` (async), lines 445-503: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(q)).all`, `(await self.db.execute(select(func.count(Order.id)).where(Order.created_at >= date_from, Order.payment_method == 'cod', Order.status == OrderStatus.cancelled))).scalar_one`, `(await self.db.execute(select(func.count(Order.id)).where(Order.created_at >= date_from, Order.payment_method == 'cod', Order.status.notin_(['pending_cod_verification', 'cancelled'])))).scalar_one`, `Order.status.notin_`, `PaymentMethodStat`, `PaymentMethodsResponse`, `_date_from`, `data.get`, `data.get('cod', {}).get`, `data.values`, `func.coalesce`, `func.coalesce(func.sum(Order.total), 0).label` ... (24 distinct call expressions).
- `AdminAnalyticsService.get_payment_methods.stat` (sync), lines 465-472: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentMethodStat`, `data.get`, `round`.
- `AdminAnalyticsService.get_cities` (async), lines 505-542: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(q)).all`, `CitiesResponse`, `CityRow`, `Order.status.in_`, `_date_from`, `desc`, `func.coalesce`, `func.coalesce(func.sum(Order.total), 0).label`, `func.count`, `func.count(Order.id).label`, `func.sum`, `int` ... (21 distinct call expressions).
- `AdminAnalyticsService.get_conversion` (async), lines 544-571: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(select(AnalyticsEvent.kind, func.count()).where(AnalyticsEvent.created_at >= date_from).group_by(AnalyticsEvent.kind))).all`, `ConversionResponse`, `Order.status.in_`, `_date_from`, `counts.get`, `dict`, `func.count`, `func.min`, `round`, `select`, `select(AnalyticsEvent.kind, func.count()).where`, `select(AnalyticsEvent.kind, func.count()).where(AnalyticsEvent.created_at >= date_from).group_by` ... (16 distinct call expressions).
- `AdminAnalyticsService.get_search_queries` (async), lines 573-601: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(select(AnalyticsEvent.query, func.count().label('count'), func.sum(case((AnalyticsEvent.result_count == 0, 1), else_=0)).label('empty')).where(AnalyticsEvent.kind == 'search', AnalyticsEvent.created_at >= _date_from(period)).group_by(AnalyticsEvent.query).order_by(desc('count'), AnalyticsEvent.query).limit(limit))).all`, `SearchQueriesResponse`, `SearchQueryRow`, `_date_from`, `case`, `desc`, `func.count`, `func.count().label`, `func.min`, `func.sum`, `func.sum(case((AnalyticsEvent.result_count == 0, 1), else_=0)).label`, `round` ... (21 distinct call expressions).

## app/services/auth_service.py

377 lines; SHA-256 `f5ae0491d30ac757fc6bd4182c32d61e08b45d4b51ea438bd8612fa8ce282af1`. [Open source](../../app/services/auth_service.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.core.logging`, `app.core.redis`, `app.core.security`, `app.models.seller`, `app.models.user`, `app.repositories.user_repo`, `app.schemas.auth`.

- `_user_to_response` (sync), lines 58-71: No function docstring; consult the source body and layer walkthrough.
  Calls: `UserResponse`, `str`.
- Class `AuthService`, lines 74-377; bases: .
- `AuthService.register` (async), lines 79-104: Create a new customer account.
  Calls: `DuplicateEmailError`, `UserRepository.create`, `UserRepository.email_exists`, `create_email_verify_token`, `db.commit`, `hash_password`, `logger.info`, `str`.
  Mutation/I-O-related call names: `db.commit`.
- `AuthService.verify_email` (async), lines 109-141: Verify email address via token link. Returns auth tokens on success.
  Calls: `AuthResponse`, `BusinessRuleError`, `SessionRepository.create`, `UserRepository.get_by_id_or_raise`, `UserRepository.verify_email`, `_user_to_response`, `create_access_token`, `datetime.now`, `db.commit`, `db.refresh`, `decode_email_verify_token`, `generate_refresh_token` ... (16 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `AuthService.login` (async), lines 146-215: Authenticate with email + password (+ TOTP for admins).
  Calls: `AuthResponse`, `EmailNotVerifiedError`, `InvalidCredentialsError`, `SessionRepository.create`, `TwoFactorRequiredError`, `UserRepository.get_by_email`, `UserRepository.update_last_login`, `UserRepository.update_password`, `_user_to_response`, `create_access_token`, `datetime.now`, `db.commit` ... (25 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.
- `AuthService.refresh_token` (async), lines 220-266: Validate refresh token → rotate → return new access + refresh tokens.
  Calls: `AuthenticationError`, `SessionRepository.create`, `SessionRepository.delete_by_token_hash`, `SessionRepository.get_by_token_hash`, `TokenResponse`, `UserRepository.get_by_id_or_raise`, `create_access_token`, `datetime.now`, `db.commit`, `db.scalar`, `generate_refresh_token`, `hash_refresh_token` ... (17 distinct call expressions).
  Mutation/I-O-related call names: `SessionRepository.delete_by_token_hash`, `db.commit`.
- `AuthService.logout` (async), lines 271-285: Invalidate refresh token session + blocklist the access token jti.
  Calls: `SessionRepository.delete_by_token_hash`, `db.commit`, `hash_refresh_token`, `logger.info`, `revoke_token`.
  Mutation/I-O-related call names: `SessionRepository.delete_by_token_hash`, `db.commit`.
- `AuthService.forgot_password` (async), lines 290-301: Generate a password reset token.
  Calls: `UserRepository.get_by_email`, `create_password_reset_token`, `logger.info`, `str`.
- `AuthService.reset_password` (async), lines 306-328: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `SessionRepository.delete_all_for_user`, `UserRepository.get_by_id_or_raise`, `UserRepository.update_password`, `db.commit`, `decode_password_reset_token`, `get_redis`, `get_redis().set`, `hash_password`, `hashlib.sha256`, `hashlib.sha256(token.encode()).hexdigest`, `logger.info` ... (14 distinct call expressions).
  Mutation/I-O-related call names: `SessionRepository.delete_all_for_user`, `db.commit`.
- `AuthService.change_password` (async), lines 333-346: No function docstring; consult the source body and layer walkthrough.
  Calls: `InvalidCredentialsError`, `SessionRepository.delete_all_for_user`, `UserRepository.get_by_id_or_raise`, `UserRepository.update_password`, `db.commit`, `hash_password`, `logger.info`, `str`, `verify_password`.
  Mutation/I-O-related call names: `SessionRepository.delete_all_for_user`, `db.commit`.
- `AuthService.setup_totp` (async), lines 351-360: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `TOTPSetupResponse`, `UserRepository.get_by_id_or_raise`, `UserRepository.set_totp`, `db.commit`, `generate_totp_secret`, `get_totp_uri`.
  Mutation/I-O-related call names: `db.commit`.
- `AuthService.verify_and_enable_totp` (async), lines 363-377: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `UserRepository.get_by_id_or_raise`, `UserRepository.set_totp`, `db.commit`, `logger.info`, `str`, `verify_totp`.
  Mutation/I-O-related call names: `db.commit`.

## app/services/cart_service.py

194 lines; SHA-256 `f7dff13a4318d1d8f68003bdc23a003e66e66214126b1cae3f4416a091857ab7`. [Open source](../../app/services/cart_service.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.models.analytics`, `app.models.product`, `app.models.seller`, `app.schemas.order`, `app.services.platform_settings`.

- `_cart_key` (sync), lines 24-25: No function docstring; consult the source body and layer walkthrough.
- Class `CartService`, lines 28-194; bases: .
- `CartService.__init__` (sync), lines 29-31: No function docstring; consult the source body and layer walkthrough.
- `CartService.get_cart` (async), lines 33-85: No function docstring; consult the source body and layer walkthrough.
  Calls: `CartItemResponse`, `ProductVariant.id.in_`, `ProductVariant.is_active.is_`, `UUID`, `_cart_key`, `get_platform_settings`, `int`, `isinstance`, `items.append`, `k.decode`, `next`, `quantities.items` ... (27 distinct call expressions).
- `CartService.add_item` (async), lines 87-107: No function docstring; consult the source body and layer walkthrough.
  Calls: `AnalyticsEvent`, `BusinessRuleError`, `_cart_key`, `int`, `self._get_variant`, `self.db.add`, `self.db.commit`, `self.get_cart`, `self.redis.expire`, `self.redis.hget`, `self.redis.hset`, `str`.
  Mutation/I-O-related call names: `self.db.commit`.
- `CartService.update_item` (async), lines 109-123: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `_cart_key`, `self._get_variant`, `self.get_cart`, `self.redis.expire`, `self.redis.hdel`, `self.redis.hset`, `str`.
- `CartService.remove_item` (async), lines 125-126: No function docstring; consult the source body and layer walkthrough.
  Calls: `_cart_key`, `self.redis.hdel`, `str`.
- `CartService.clear` (async), lines 128-129: No function docstring; consult the source body and layer walkthrough.
  Calls: `_cart_key`, `self.redis.delete`.
  Mutation/I-O-related call names: `self.redis.delete`.
- `CartService.sync` (async), lines 131-139: No function docstring; consult the source body and layer walkthrough.
  Calls: `_cart_key`, `int`, `max`, `self.get_cart`, `self.redis.expire`, `self.redis.hget`, `self.redis.hset`, `str`.
- `CartService.get_raw_items` (async), lines 141-146: No function docstring; consult the source body and layer walkthrough.
  Calls: `UUID`, `_cart_key`, `int`, `isinstance`, `k.decode`, `raw.items`, `self.redis.hgetall`.
- `CartService._get_variant` (async), lines 148-160: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `ProductVariant.is_active.is_`, `result.scalar_one_or_none`, `select`, `select(ProductVariant).options`, `select(ProductVariant).options(selectinload(ProductVariant.inventory), selectinload(ProductVariant.product).selectinload(Product.seller)).where`, `selectinload`, `selectinload(ProductVariant.product).selectinload`, `self.db.execute`.
- `CartService._empty_cart` (sync), lines 163-167: No function docstring; consult the source body and layer walkthrough.
  Calls: `CartResponse`.
- `CartService._build_cart_response` (sync), lines 170-194: No function docstring; consult the source body and layer walkthrough.
  Calls: `CartResponse`, `SellerCartGroup`, `groups.values`, `groups[item.seller_id].items.append`, `list`, `sum`.

## app/services/commission_service.py

396 lines; SHA-256 `8c5407ecc680fd038c59dec3f008314afbc99b562fef700530760b77432420f1`. [Open source](../../app/services/commission_service.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.models.order`, `app.models.payment`, `app.models.seller`, `app.models.wallet`, `app.repositories.seller_repo`, `app.repositories.wallet_repo`, `app.services.platform_settings`.

- Class `CommissionService`, lines 21-396; bases: .
- `CommissionService.__init__` (sync), lines 22-26: No function docstring; consult the source body and layer walkthrough.
  Calls: `CommissionRepository`, `WalletRepository`, `WalletTransactionRepository`.
- `CommissionService.settle` (async), lines 30-144: Credit the seller's pending_balance when a SellerOrder is delivered and paid.
  Calls: `(await self.db.scalars(select(SO.subtotal).where(SO.order_id == seller_order.order_id))).all`, `(gross_amount * rate).quantize`, `(pre_confirmed * seller_share).quantize`, `(seller_order.subtotal / order_subtotal).quantize`, `BusinessRuleError`, `Decimal`, `NotFoundError`, `Refund.processed_at.is_not`, `func.coalesce`, `func.sum`, `get_platform_settings`, `max` ... (34 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`, `self.db.flush`.
- `CommissionService.reverse_for_refund` (async), lines 148-188: Reverse the seller's wallet earnings proportionally when a customer refund
  Calls: `self._reverse_across_order`, `self._reverse_one`, `self.db.commit`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.commit`, `self.db.flush`.
- `CommissionService._reverse_one` (async), lines 190-223: Reverse earnings for one seller_order (return-linked refund).
  Calls: `Decimal`, `select`, `select(CommissionLedger).where`, `select(CommissionLedger).where(CommissionLedger.seller_order_id == seller_order_id).with_for_update`, `self._already_reversed`, `self._apply_debit`, `self._prorate`, `self.db.scalar`.
- `CommissionService._reverse_across_order` (async), lines 225-280: Split a direct (non-return) refund proportionally across all settled
  Calls: `(await self.db.execute(select(SO).where(SO.order_id == order_id))).scalars`, `(await self.db.execute(select(SO).where(SO.order_id == order_id))).scalars().all`, `(refund_amount * seller_share).quantize`, `(so.subtotal / total_subtotal).quantize`, `Decimal`, `select`, `select(CommissionLedger).where`, `select(CommissionLedger).where(CommissionLedger.seller_order_id == so.id).with_for_update`, `select(SO).where`, `self._already_reversed`, `self._apply_debit`, `self._prorate` ... (15 distinct call expressions).
- `CommissionService._already_reversed` (async), lines 284-294: True if a debit_adjustment WalletTransaction for this reference already exists.
  Calls: `select`, `select(WalletTransaction.id).where`, `self.db.scalar`.
- `CommissionService._prorate` (sync), lines 297-312: Return target_amount × (refund_amount / gross_amount), capped at target_amount.
  Calls: `(refund_amount / gross_amount).quantize`, `(target_amount * ratio).quantize`, `Decimal`, `min`.
- `CommissionService._apply_debit` (async), lines 314-378: Debit the seller wallet, best effort.
  Calls: `Decimal`, `min`, `select`, `select(SellerWallet).where`, `select(SellerWallet).where(SellerWallet.seller_id == seller_id).with_for_update`, `self.db.execute`, `self.db.flush`, `self.db.scalar`, `self.tx_repo.create`, `update`, `update(SellerWallet).where`, `update(SellerWallet).where(SellerWallet.seller_id == seller_id).values`.
  Mutation/I-O-related call names: `self.db.flush`.
- `CommissionService._enqueue_release` (async), lines 380-396: No function docstring; consult the source body and layer walkthrough.
  Calls: `RedisSettings.from_dsn`, `create_pool`, `pool.aclose`, `pool.enqueue_job`, `str`.
  Mutation/I-O-related call names: `pool.enqueue_job`.

## app/services/coupon_service.py

106 lines; SHA-256 `408e05c2fdf3bfd36e172a1fb0dac973dcb66e52315c36486967372b7bda5262`. [Open source](../../app/services/coupon_service.py).

Backend imports: `app.core.exceptions`, `app.models.coupon`, `app.schemas.order`.

- Class `CouponService`, lines 16-106; bases: .
- `CouponService.__init__` (sync), lines 17-18: No function docstring; consult the source body and layer walkthrough.
- `CouponService.validate` (async), lines 20-33: No function docstring; consult the source body and layer walkthrough.
  Calls: `CouponValidationResponse`, `Decimal`, `int`, `max`, `self._calc_discount`, `self._get_valid_coupon`.
- `CouponService.apply_to_order` (async), lines 35-58: Validate, calculate discount, record usage, increment uses_count.
  Calls: `CouponUsage`, `int`, `self._calc_discount`, `self._get_valid_coupon`, `self.db.add`, `self.db.execute`, `update`, `update(Coupon).where`, `update(Coupon).where(Coupon.id == coupon.id).values`.
- `CouponService._get_valid_coupon` (async), lines 62-100: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `code.upper`, `coupon.valid_from.replace`, `coupon.valid_until.replace`, `datetime.now`, `int`, `len`, `query.with_for_update`, `result.scalar_one_or_none`, `select`, `select(Coupon).where`, `select(CouponUsage).where` ... (15 distinct call expressions).
- `CouponService._calc_discount` (sync), lines 103-106: No function docstring; consult the source body and layer walkthrough.
  Calls: `(subtotal * coupon.discount_value / 100).quantize`, `Decimal`, `min`.

## app/services/customer_service.py

633 lines; SHA-256 `839660933d471b81fc15d325e2b168bdd59f7cadae0dc8ce4aca8abde14f9976`. [Open source](../../app/services/customer_service.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.core.logging`, `app.core.redis`, `app.core.security`, `app.models.order`, `app.models.product`, `app.models.review`, `app.models.seller`, `app.models.user`, `app.repositories.user_repo`, `app.schemas.user`, `app.services.image_service`.

- Class `CustomerService`, lines 58-633; bases: .
- `CustomerService.__init__` (sync), lines 59-60: No function docstring; consult the source body and layer walkthrough.
- `CustomerService._get_user` (async), lines 64-68: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `UserRepository.get_by_id`.
- `CustomerService._review_to_schema` (sync), lines 71-94: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReviewAuthorResponse`, `ReviewImageResponse`, `ReviewResponse`, `hasattr`.
- `CustomerService.get_profile` (async), lines 100-113: No function docstring; consult the source body and layer walkthrough.
  Calls: `UserProfileResponse`, `self._get_user`.
- `CustomerService.update_profile` (async), lines 115-132: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._get_user`, `self.db.commit`, `self.db.execute`, `self.db.refresh`, `self.get_profile`, `update`, `update(User).where`, `update(User).where(User.id == user_id).values`.
  Mutation/I-O-related call names: `self.db.commit`.
- `CustomerService.upload_avatar` (async), lines 134-150: No function docstring; consult the source body and layer walkthrough.
  Calls: `AvatarUploadResponse`, `ImageService`, `ImageService().process_and_upload`, `self._get_user`, `self.db.commit`, `self.db.execute`, `str`, `update`, `update(User).where`, `update(User).where(User.id == user_id).values`.
  Mutation/I-O-related call names: `ImageService().process_and_upload`, `self.db.commit`.
- `CustomerService.change_password` (async), lines 152-172: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `delete`, `delete(UserSession).where`, `hash_password`, `logger.info`, `self._get_user`, `self.db.commit`, `self.db.execute`, `str`, `update`, `update(User).where`, `update(User).where(User.id == user_id).values` ... (13 distinct call expressions).
  Mutation/I-O-related call names: `delete`, `delete(UserSession).where`, `self.db.commit`.
- `CustomerService._addr_to_schema` (sync), lines 179-188: No function docstring; consult the source body and layer walkthrough.
  Calls: `AddressResponse`.
- `CustomerService.list_addresses` (async), lines 190-197: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(stmt)).scalars`, `(await self.db.execute(stmt)).scalars().all`, `UserAddress.is_default.desc`, `select`, `select(UserAddress).where`, `select(UserAddress).where(UserAddress.user_id == user_id).order_by`, `self._addr_to_schema`, `self.db.execute`.
- `CustomerService.create_address` (async), lines 199-225: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_stmt)).scalar_one`, `BusinessRuleError`, `UserAddress`, `func.count`, `select`, `select(func.count()).where`, `self._addr_to_schema`, `self.db.add`, `self.db.commit`, `self.db.execute`, `self.db.refresh`, `update` ... (14 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `CustomerService.update_address` (async), lines 227-260: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(stmt)).scalar_one_or_none`, `NotFoundError`, `select`, `select(UserAddress).where`, `self._addr_to_schema`, `self.db.commit`, `self.db.execute`, `self.db.refresh`, `update`, `update(UserAddress).where`, `update(UserAddress).where(UserAddress.id == address_id).values`, `update(UserAddress).where(UserAddress.user_id == user_id).values`.
  Mutation/I-O-related call names: `self.db.commit`.
- `CustomerService.delete_address` (async), lines 262-270: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `delete`, `delete(UserAddress).where`, `self.db.commit`, `self.db.execute`.
  Mutation/I-O-related call names: `delete`, `delete(UserAddress).where`, `self.db.commit`.
- `CustomerService.set_default_address` (async), lines 272-290: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `result.scalar_one_or_none`, `self._addr_to_schema`, `self.db.commit`, `self.db.execute`, `update`, `update(UserAddress).where`, `update(UserAddress).where(UserAddress.id == address_id, UserAddress.user_id == user_id).values`, `update(UserAddress).where(UserAddress.id == address_id, UserAddress.user_id == user_id).values(is_default=True).returning`, `update(UserAddress).where(UserAddress.user_id == user_id).values`.
  Mutation/I-O-related call names: `self.db.commit`.
- `CustomerService.list_user_reviews` (async), lines 296-308: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(stmt)).scalars`, `(await self.db.execute(stmt)).scalars().all`, `Review.created_at.desc`, `select`, `select(Review).where`, `select(Review).where(Review.user_id == user_id).order_by`, `select(Review).where(Review.user_id == user_id).order_by(Review.created_at.desc()).offset`, `select(Review).where(Review.user_id == user_id).order_by(Review.created_at.desc()).offset(offset).limit`, `self._review_to_schema`, `self.db.execute`.
- `CustomerService.create_review` (async), lines 310-354: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `Review`, `existing.scalar_one_or_none`, `logger.info`, `select`, `select(OrderItem.id).where`, `select(Review).where`, `self._review_to_schema`, `self.db.add`, `self.db.commit`, `self.db.execute` ... (16 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `CustomerService.update_review` (async), lines 356-381: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(stmt)).scalar_one_or_none`, `BusinessRuleError`, `NotFoundError`, `select`, `select(Review).where`, `self._review_to_schema`, `self.db.commit`, `self.db.execute`, `self.db.refresh`, `self.refresh_product_rating`, `update`, `update(Review).where` ... (13 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `CustomerService.delete_review` (async), lines 383-391: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `select`, `select(Review).where`, `self.db.commit`, `self.db.delete`, `self.db.flush`, `self.db.scalar`, `self.refresh_product_rating`.
  Mutation/I-O-related call names: `self.db.commit`, `self.db.delete`, `self.db.flush`.
- `CustomerService.refresh_product_rating` (async), lines 393-397: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(select(func.coalesce(func.avg(Review.rating), 0), func.count(Review.id)).where(Review.product_id == product_id, Review.status == ReviewStatus.approved))).one`, `func.avg`, `func.coalesce`, `func.count`, `select`, `select(Product.id).where`, `select(Product.id).where(Product.id == product_id).with_for_update`, `select(func.coalesce(func.avg(Review.rating), 0), func.count(Review.id)).where`, `self.db.execute`, `update`, `update(Product).where`, `update(Product).where(Product.id == product_id).values`.
- `CustomerService.list_product_reviews` (async), lines 399-451: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(avg_stmt)).scalar_one`, `(await self.db.execute(breakdown_stmt)).all`, `(await self.db.execute(count_stmt)).scalar_one`, `(await self.db.execute(stmt)).scalars`, `(await self.db.execute(stmt)).scalars().all`, `PaginatedReviews`, `Review.created_at.asc`, `Review.created_at.desc`, `Review.helpful_count.desc`, `Review.rating.asc`, `Review.rating.desc`, `base.order_by` ... (29 distinct call expressions).
- `CustomerService.vote_review` (async), lines 453-474: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `insert`, `insert(ReviewVote).values`, `insert(ReviewVote).values(review_id=review_id, user_id=user_id, helpful=helpful).on_conflict_do_nothing`, `insert(ReviewVote).values(review_id=review_id, user_id=user_id, helpful=helpful).on_conflict_do_nothing().returning`, `inserted.scalar_one_or_none`, `self.db.commit`, `self.db.execute`, `self.db.get`, `str`, `update` ... (14 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `CustomerService.get_wishlist` (async), lines 480-528: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(image_stmt)).scalar_one_or_none`, `(await self.db.execute(stmt)).scalars`, `(await self.db.execute(stmt)).scalars().all`, `Product.admin_hidden.is_`, `Product.deleted_at.is_`, `Product.id.in_`, `Product.is_published.is_`, `Product.seller.has`, `WishlistItemResponse`, `WishlistResponse`, `get_redis`, `int` ... (25 distinct call expressions).
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `CustomerService.add_to_wishlist` (async), lines 530-541: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `get_redis`, `redis.expire`, `redis.sadd`, `self.db.get`, `self.get_wishlist`, `str`.
- `CustomerService.remove_from_wishlist` (async), lines 543-548: No function docstring; consult the source body and layer walkthrough.
  Calls: `get_redis`, `redis.srem`, `str`.
- `CustomerService.get_notification_prefs` (async), lines 554-573: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationPreferencesResponse`, `_bool`, `get_redis`, `isinstance`, `k.decode`, `raw.get`, `raw.items`, `redis.hgetall`.
- `CustomerService.get_notification_prefs._bool` (sync), lines 563-566: No function docstring; consult the source body and layer walkthrough.
- `CustomerService.update_notification_prefs` (async), lines 575-589: No function docstring; consult the source body and layer walkthrough.
  Calls: `get_redis`, `payload.model_dump`, `payload.model_dump(exclude_none=True).items`, `redis.expire`, `redis.hset`, `self.get_notification_prefs`.
- `CustomerService.delete_account` (async), lines 595-633: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(active_stmt)).scalar_one`, `BusinessRuleError`, `Order.status.in_`, `datetime.now`, `delete`, `delete(UserSession).where`, `func.count`, `logger.info`, `select`, `select(func.count()).where`, `self._get_user`, `self.db.commit` ... (18 distinct call expressions).
  Mutation/I-O-related call names: `delete`, `delete(UserSession).where`, `self.db.commit`.

## app/services/google_oauth.py

154 lines; SHA-256 `466c5e45caeff9624f9d71779eb4b84cf7a52dcb53284275ca92b53ce95450d7`. [Open source](../../app/services/google_oauth.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.core.redis`, `app.core.security`, `app.models.user`, `app.repositories.user_repo`.

- `require_configuration` (sync), lines 28-30: No function docstring; consult the source body and layer walkthrough.
  Calls: `ExternalServiceError`.
- `start_google_login` (async), lines 33-66: No function docstring; consult the source body and layer walkthrough.
  Calls: `base64.urlsafe_b64encode`, `base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip`, `base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode`, `get_redis`, `get_redis().setex`, `hashlib.sha256`, `hashlib.sha256(verifier.encode()).digest`, `json.dumps`, `range`, `require_configuration`, `response.set_cookie`, `secrets.token_urlsafe` ... (14 distinct call expressions).
- `finish_google_login` (async), lines 69-154: No function docstring; consult the source body and layer walkthrough.
  Calls: `AuthenticationError`, `BusinessRuleError`, `RedirectResponse`, `SessionRepository.create`, `UserRepository.create`, `UserRepository.get_by_email`, `UserRepository.get_by_google_id`, `ValueError`, `claims.get`, `claims['email'].lower`, `client.get`, `client.post` ... (37 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`, `response.delete_cookie`.

## app/services/image_service.py

80 lines; SHA-256 `046a330c74c1bb49fdf031641511c5bed074adae71750a15ab5077c608802b3a`. [Open source](../../app/services/image_service.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.integrations.supabase_storage`.

- Class `ImageService`, lines 21-80; bases: .
- `ImageService.__init__` (sync), lines 22-23: No function docstring; consult the source body and layer walkthrough.
  Calls: `SupabaseStorage`.
- `ImageService.validate` (sync), lines 27-39: Returns detected MIME type or raises BusinessRuleError.
  Calls: `BusinessRuleError`, `len`.
- `ImageService.to_webp` (sync), lines 43-57: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Image.open`, `ImageOps.exif_transpose`, `buf.getvalue`, `img.convert`, `img.save`, `img.thumbnail`, `io.BytesIO`, `source.load`.
- `ImageService.process_and_upload` (async), lines 61-74: Validate → convert to WebP → upload to Supabase → return public URL.
  Calls: `self.storage.upload`, `self.to_webp`, `self.validate`, `uuid.uuid4`.
  Mutation/I-O-related call names: `self.storage.upload`.
- `ImageService.delete` (async), lines 76-80: Delete an image from Supabase Storage given its public URL.
  Calls: `len`, `self.storage.delete`, `self.storage.get_public_url`, `url.startswith`.
  Mutation/I-O-related call names: `self.storage.delete`.

## app/services/inventory_service.py

289 lines; SHA-256 `86aaeac1668026850fd888939edda3d9aa0d0847bbb597b3a536f2d40e12b990`. [Open source](../../app/services/inventory_service.py).

Backend imports: `app.api.v1.inventory`, `app.core.exceptions`, `app.core.logging`, `app.models.product`, `app.repositories.inventory_repo`.

- Class `InventoryService`, lines 32-289; bases: .
- `InventoryService.__init__` (sync), lines 33-35: No function docstring; consult the source body and layer walkthrough.
  Calls: `InventoryRepository`.
- `InventoryService._get_inventory_for_seller` (async), lines 39-56: Load inventory + variant + product, assert seller ownership.
  Calls: `(await self.db.execute(stmt.with_for_update(of=ProductInventory))).first`, `NotFoundError`, `Product.deleted_at.is_`, `select`, `select(ProductInventory, ProductVariant, Product).join`, `select(ProductInventory, ProductVariant, Product).join(ProductVariant, ProductVariant.id == ProductInventory.variant_id).join`, `select(ProductInventory, ProductVariant, Product).join(ProductVariant, ProductVariant.id == ProductInventory.variant_id).join(Product, Product.id == ProductVariant.product_id).where`, `self.db.execute`, `stmt.with_for_update`.
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `InventoryService._to_schema` (sync), lines 59-79: No function docstring; consult the source body and layer walkthrough.
  Calls: `dict`, `inv.updated_at.isoformat`.
- `InventoryService.list_seller_inventory` (async), lines 85-126: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_stmt)).scalar_one`, `(await self.db.execute(stmt.offset(offset).limit(per_page))).all`, `PaginatedVariantStock`, `Product.deleted_at.is_`, `Product.name.ilike`, `ProductVariant.sku.ilike`, `VariantStockResponse`, `func.count`, `math.ceil`, `select`, `select(ProductInventory, ProductVariant, Product).join`, `select(ProductInventory, ProductVariant, Product).join(ProductVariant, ProductVariant.id == ProductInventory.variant_id).join` ... (20 distinct call expressions).
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `InventoryService.get_low_stock` (async), lines 128-147: No function docstring; consult the source body and layer walkthrough.
  Calls: `(ProductInventory.stock - ProductInventory.reserved).asc`, `(await self.db.execute(stmt)).all`, `LowStockResponse`, `Product.deleted_at.is_`, `VariantStockResponse`, `len`, `select`, `select(ProductInventory, ProductVariant, Product).join`, `select(ProductInventory, ProductVariant, Product).join(ProductVariant, ProductVariant.id == ProductInventory.variant_id).join`, `select(ProductInventory, ProductVariant, Product).join(ProductVariant, ProductVariant.id == ProductInventory.variant_id).join(Product, Product.id == ProductVariant.product_id).where`, `select(ProductInventory, ProductVariant, Product).join(ProductVariant, ProductVariant.id == ProductInventory.variant_id).join(Product, Product.id == ProductVariant.product_id).where(Product.seller_id == seller_id, Product.deleted_at.is_(None), ProductInventory.stock - ProductInventory.reserved <= DEFAULT_REORDER_THRESHOLD).order_by`, `self._to_schema` ... (13 distinct call expressions).
  Mutation/I-O-related call names: `Product.deleted_at.is_`, `select(ProductInventory, ProductVariant, Product).join(ProductVariant, ProductVariant.id == ProductInventory.variant_id).join(Product, Product.id == ProductVariant.product_id).where(Product.seller_id == seller_id, Product.deleted_at.is_(None), ProductInventory.stock - ProductInventory.reserved <= DEFAULT_REORDER_THRESHOLD).order_by`.
- `InventoryService.get_variant_stock` (async), lines 149-153: No function docstring; consult the source body and layer walkthrough.
  Calls: `VariantStockResponse`, `self._get_inventory_for_seller`, `self._to_schema`.
- `InventoryService.set_stock` (async), lines 155-175: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `VariantStockResponse`, `datetime.now`, `logger.info`, `self._get_inventory_for_seller`, `self._to_schema`, `self.db.commit`, `self.db.execute`, `self.db.refresh`, `str`, `update`, `update(ProductInventory).where` ... (13 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `InventoryService.adjust_stock` (async), lines 177-213: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `StockAdjustmentResponse`, `datetime.now`, `logger.info`, `self._get_inventory_for_seller`, `self.db.commit`, `self.db.execute`, `str`, `update`, `update(ProductInventory).where`, `update(ProductInventory).where(ProductInventory.variant_id == variant_id).values`.
  Mutation/I-O-related call names: `self.db.commit`.
- `InventoryService.admin_list_inventory` (async), lines 219-262: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_stmt)).scalar_one`, `(await self.db.execute(stmt.offset(offset).limit(per_page))).all`, `PaginatedVariantStock`, `Product.deleted_at.is_`, `Product.name.ilike`, `ProductVariant.sku.ilike`, `VariantStockResponse`, `func.count`, `math.ceil`, `select`, `select(ProductInventory, ProductVariant, Product).join`, `select(ProductInventory, ProductVariant, Product).join(ProductVariant, ProductVariant.id == ProductInventory.variant_id).join` ... (20 distinct call expressions).
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `InventoryService.bulk_update_stock` (async), lines 264-289: No function docstring; consult the source body and layer walkthrough.
  Calls: `BulkStockUpdateResponse`, `datetime.now`, `errors.append`, `logger.info`, `self.db.commit`, `self.db.execute`, `str`, `update`, `update(ProductInventory).where`, `update(ProductInventory).where(ProductInventory.variant_id == item.variant_id, ProductInventory.reserved <= item.stock).values`.
  Mutation/I-O-related call names: `self.db.commit`.



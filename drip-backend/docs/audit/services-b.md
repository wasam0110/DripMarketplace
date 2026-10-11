# Backend source index: services-b

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## app/services/notification_service.py

365 lines; SHA-256 `b9ebea8dadf2dad165cdedd8a7fe3ae9180fbcc57dda6be9151501e33643c0c0`. [Open source](../../app/services/notification_service.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.integrations.resend_client`, `app.models.notification`, `app.models.order`, `app.models.seller`, `app.models.user`, `app.models.wallet`, `app.repositories.notification_repo`, `app.schemas.notification`.

- Class `NotifType`, lines 28?39; bases: .
- Class `NotificationService`, lines 42?365; bases: .
- `NotificationService.__init__` (sync), lines 43?46: No function docstring; consult the source body and layer walkthrough.
  Calls: `EmailLogRepository`, `NotificationRepository`.
- `NotificationService.create` (async), lines 50?64: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.repo.create`.
- `NotificationService.list_notifications` (async), lines 66?80: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationListResponse`, `NotificationResponse.model_validate`, `self.repo.list_by_user`, `self.repo.unread_count`.
- `NotificationService.mark_read` (async), lines 82?85: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.db.commit`, `self.repo.mark_read`.
  Mutation/I-O-related call names: `self.db.commit`.
- `NotificationService.mark_all_read` (async), lines 87?90: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.db.commit`, `self.repo.mark_all_read`.
  Mutation/I-O-related call names: `self.db.commit`.
- `NotificationService.get_preferences` (async), lines 94?106: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationPreferencesResponse`, `NotificationPreferencesResponse.model_validate`, `self.repo.get_preferences`.
- `NotificationService.update_preferences` (async), lines 108?114: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationPreferencesResponse.model_validate`, `payload.model_dump`, `payload.model_dump().items`, `self.db.commit`, `self.repo.upsert_preferences`.
  Mutation/I-O-related call names: `self.db.commit`.
- `NotificationService.send_email` (async), lines 118?148: Send email via Resend and log the result.
  Calls: `ResendClient`, `client.send`, `self.db.commit`, `self.log_repo.create`, `str`.
  Mutation/I-O-related call names: `ResendClient`, `client.send`, `self.db.commit`.
- `NotificationService.notify_order_placed` (async), lines 152?211: No function docstring; consult the source body and layer walkthrough.
  Calls: `''.join`, `int`, `order.payment_method.value.upper`, `result.scalar_one_or_none`, `select`, `select(Order).options`, `select(Order).options(selectinload(Order.items), selectinload(Order.address), selectinload(Order.seller_orders)).where`, `select(User).where`, `selectinload`, `self.create`, `self.db.commit`, `self.db.execute` ? (14 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`, `self.send_email`.
- `NotificationService.notify_order_status` (async), lines 213?243: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(Order).where`, `self.create`, `self.db.commit`, `self.db.execute`, `status_messages.get`.
  Mutation/I-O-related call names: `self.db.commit`.
- `NotificationService.notify_payout` (async), lines 245?282: No function docstring; consult the source body and layer walkthrough.
  Calls: `int`, `messages.get`, `result.scalar_one_or_none`, `select`, `select(Payout).where`, `select(Seller).where`, `self.create`, `self.db.commit`, `self.db.execute`, `seller_result.scalar_one_or_none`.
  Mutation/I-O-related call names: `self.db.commit`.
- `NotificationService.notify_seller_decision` (async), lines 284?310: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(Seller).where`, `self.create`, `self.db.commit`, `self.db.execute`.
  Mutation/I-O-related call names: `self.db.commit`.
- `NotificationService.broadcast` (async), lines 314?350: No function docstring; consult the source body and layer walkthrough.
  Calls: `BroadcastResponse`, `ExternalServiceError`, `RedisSettings.from_dsn`, `create_pool`, `len`, `pool.aclose`, `pool.enqueue_job`, `result.scalars`, `result.scalars().all`, `select`, `select(User.id).where`, `self.db.execute` ? (14 distinct call expressions).
  Mutation/I-O-related call names: `pool.enqueue_job`.
- `NotificationService.get_email_log` (async), lines 354?365: No function docstring; consult the source body and layer walkthrough.
  Calls: `EmailLogResponse.model_validate`, `self.log_repo.list_admin`.

## app/services/order_access.py

56 lines; SHA-256 `7dc15ba82c19936e49947df99e1976b3342a9c6ab879891366da99baf432b1a6`. [Open source](../../app/services/order_access.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.core.security`, `app.repositories.order_repo`.

- `create_guest_token` (sync), lines 14?26: No function docstring; consult the source body and layer walkthrough.
  Calls: `_load_private_key`, `datetime.now`, `jwt.encode`, `str`, `timedelta`.
- `guest_token_matches` (sync), lines 29?43: No function docstring; consult the source body and layer walkthrough.
  Calls: `_load_public_key`, `jwt.decode`, `str`.
- `authorized_order` (async), lines 46?56: No function docstring; consult the source body and layer walkthrough.
  Calls: `AuthenticationError`, `NotFoundError`, `OrderRepository`, `OrderRepository(db).get_by_id`, `guest_token_matches`.

## app/services/order_service.py

751 lines; SHA-256 `dc58c4ea09e5ff4f8bad4b23bb8d3b8409418e1e6227d839873be85f9b388e56`. [Open source](../../app/services/order_service.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.core.logging`, `app.models.coupon`, `app.models.order`, `app.models.payment`, `app.models.product`, `app.models.seller`, `app.repositories.inventory_repo`, `app.repositories.order_repo`, `app.schemas.order`, `app.services.cart_service`, `app.services.commission_service`, `app.services.coupon_service`, `app.services.order_access`, `app.services.platform_settings`.

- `_generate_order_number` (sync), lines 47?50: No function docstring; consult the source body and layer walkthrough.
  Calls: `''.join`, `datetime.utcnow`, `now.strftime`, `range`, `secrets.choice`.
- `_whatsapp_url` (sync), lines 53?55: No function docstring; consult the source body and layer walkthrough.
- Class `_CheckoutLine`, lines 66?71; bases: .
  Annotated fields: `variant`, `quantity`, `unit_price`, `subtotal`, `primary_image`.
- Class `_CheckoutCalculation`, lines 75?85; bases: .
  Annotated fields: `lines`, `seller_subtotals`, `subtotal`, `shipping_fee`, `free_shipping_threshold`, `cod_timeout_minutes`.
- `_CheckoutCalculation.total` (sync), lines 84?85: No function docstring; consult the source body and layer walkthrough.
- Class `OrderService`, lines 88?751; bases: .
- `OrderService.__init__` (sync), lines 89?94: No function docstring; consult the source body and layer walkthrough.
  Calls: `InventoryRepository`, `OrderRepository`, `SellerOrderRepository`.
- `OrderService.create_order` (async), lines 98?114: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `CartService`, `cart_svc.get_raw_items`, `self._build_order`.
- `OrderService.create_guest_order` (async), lines 118?129: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._build_order`, `self._merge_items`.
- `OrderService.quote_guest_checkout` (async), lines 131?186: Return current guest pricing and payment capabilities without reserving stock.
  Calls: `BusinessRuleError`, `CartItemResponse`, `Decimal`, `GuestCheckoutQuoteResponse`, `PaymentMethodAvailability`, `max`, `self._calculate_checkout`, `self._merge_items`, `sum`.
- `OrderService._build_order` (async), lines 190?343: No function docstring; consult the source body and layer walkthrough.
  Calls: `(discount * sub / subtotal).quantize`, `BusinessRuleError`, `CouponService`, `CouponUsage`, `CreateOrderResponse`, `Decimal`, `PaymentMethod`, `_generate_order_number`, `_whatsapp_url`, `calculation.seller_subtotals.items`, `cart_svc.clear`, `coupon_svc._calc_discount` ? (30 distinct call expressions).
  Mutation/I-O-related call names: `self._enqueue_cod_timeout`, `self.db.commit`.
- `OrderService.get_order` (async), lines 347?351: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self._to_detail`, `self.order_repo.get_by_id`.
- `OrderService.get_order_by_number` (async), lines 353?368: No function docstring; consult the source body and layer walkthrough.
  Calls: `AuthenticationError`, `NotFoundError`, `authorized_order`, `self._to_detail`, `self.order_repo.get_by_number`.
- `OrderService.get_customer_orders` (async), lines 370?386: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderRowResponse`, `PageInfo`, `PaginatedOrders`, `max`, `self.order_repo.get_customer_orders`, `sum`.
- `OrderService.cancel_order` (async), lines 390?433: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Payment.status.in_`, `any`, `authorized_order`, `select`, `select(Payment.id).where`, `self.db.commit`, `self.db.scalar`, `self.inv_repo.release`, `self.order_repo.update_status`, `self.so_repo.update_status`.
  Mutation/I-O-related call names: `self.db.commit`.
- `OrderService.get_seller_orders` (async), lines 437?453: No function docstring; consult the source body and layer walkthrough.
  Calls: `max`, `self._to_seller_order_response`, `self.so_repo.get_by_seller`.
- `OrderService.get_seller_order_detail` (async), lines 455?459: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self._to_seller_order_response`, `self.so_repo.get_by_id`.
- `OrderService.update_seller_order_status` (async), lines 461?535: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.scalars(select(SellerOrder.status).where(SellerOrder.order_id == order.id))).all`, `BusinessRuleError`, `CommissionService`, `CommissionService(self.db).settle`, `NotFoundError`, `SellerOrderStatus`, `all`, `list`, `select`, `select(Payment.id).where`, `select(SellerOrder.status).where`, `self.db.commit` ? (23 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`, `self.db.flush`.
- `OrderService._merge_items` (sync), lines 540?544: No function docstring; consult the source body and layer walkthrough.
  Calls: `quantities.get`.
- `OrderService._calculate_checkout` (async), lines 546?594: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `_CheckoutCalculation`, `_CheckoutLine`, `get_platform_settings`, `lines.append`, `next`, `self._fetch_and_validate_variants`, `seller_subtotals.get`.
- `OrderService._fetch_and_validate_variants` (async), lines 596?643: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Product.admin_hidden.is_`, `Product.deleted_at.is_`, `Product.is_published.is_`, `ProductVariant.id.in_`, `ProductVariant.is_active.is_`, `__import__`, `any`, `len`, `list`, `result.scalars`, `result.scalars().all` ? (23 distinct call expressions).
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `OrderService._enqueue_cod_timeout` (async), lines 645?662: Enqueue a 30-min COD verification timeout task.
  Calls: `RedisSettings.from_dsn`, `create_pool`, `pool.aclose`, `pool.enqueue_job`, `str`.
  Mutation/I-O-related call names: `pool.enqueue_job`.
- `OrderService._to_detail` (sync), lines 665?715: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderDetailResponse`, `OrderItemResponse`, `SellerOrderResponse`, `ShippingAddressResponse`.
- `OrderService._to_seller_order_response` (sync), lines 718?751: No function docstring; consult the source body and layer walkthrough.
  Calls: `so.created_at.isoformat`, `so.delivered_at.isoformat`, `so.shipped_at.isoformat`, `str`.

## app/services/payment_service.py

661 lines; SHA-256 `050135db77c136962e56575a4a3e58d2483a1606417c9515711b2b253ebcabb9`. [Open source](../../app/services/payment_service.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.integrations.payfast`, `app.models.order`, `app.models.payment`, `app.models.product`, `app.models.return_`, `app.models.user`, `app.repositories.order_repo`, `app.repositories.payment_repo`, `app.repositories.return_repo`, `app.schemas.payment`, `app.services.commission_service`, `app.services.order_access`, `app.services.order_service`.

- `_build_payfast` (sync), lines 39?53: No function docstring; consult the source body and layer walkthrough.
  Calls: `ExternalServiceError`, `PayFastClient`.
- Class `PaymentService`, lines 56?661; bases: .
- `PaymentService.__init__` (sync), lines 57?59: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentRepository`.
- `PaymentService.initiate` (async), lines 61?126: No function docstring; consult the source body and layer walkthrough.
  Calls: `(order.created_at or datetime.now(UTC)).date`, `(order.created_at or datetime.now(UTC)).date().isoformat`, `BusinessRuleError`, `ExternalServiceError`, `PaymentInitResponse`, `_build_payfast`, `authorized_order`, `datetime.now`, `pf.build_checkout_payload`, `pf.get_checkout_token`, `self.db.commit`, `self.db.get` ? (15 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `PaymentService.get_status` (async), lines 128?143: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `PaymentStatusResponse`, `authorized_order`, `self.payment_repo.get_by_order_id`.
- `PaymentService.retry` (async), lines 145?189: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `OrderService`, `OrderService(self.db)._enqueue_cod_timeout`, `_build_payfast`, `authorized_order`, `self.db.flush`, `self.initiate`, `self.payment_repo.get_by_order_id`, `str`.
  Mutation/I-O-related call names: `OrderService(self.db)._enqueue_cod_timeout`, `self.db.flush`.
- `PaymentService.handle_payfast_callback` (async), lines 191?249: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `OrderRepository`, `PaymentCallback`, `UUID`, `_build_payfast`, `datetime.now`, `parsed.get`, `pf.parse_callback`, `repo.get_by_id`, `repo.update_status`, `self.db.add`, `self.db.commit` ? (14 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `PaymentService.reconcile_payfast` (async), lines 251?363: Reconcile a pending PayFast payment using the provider status API.
  Calls: `(payment.gateway_payload or {}).get`, `BusinessRuleError`, `ExternalServiceError`, `NotFoundError`, `OrderRepository`, `PayFastReconcileResponse`, `PaymentCallback`, `_build_payfast`, `_build_payfast().check_status`, `bool`, `date.fromisoformat`, `datetime.now` ? (32 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `PaymentService.refund` (async), lines 365?402: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `Refund`, `select`, `select(Payment).where`, `select(Payment).where(Payment.id == payment_id).with_for_update`, `select(Refund).where`, `self._refund_response`, `self.db.add`, `self.db.commit`, `self.db.refresh`, `self.db.scalar` ? (13 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `PaymentService.confirm_refund` (async), lines 404?482: Confirm a refund with a given reference.
  Calls: `BusinessRuleError`, `CommissionService`, `NotFoundError`, `Refund.processed_at.is_not`, `ReturnRepository`, `ReturnRepository(self.db).get_by_id`, `comm.reverse_for_refund`, `datetime.now`, `func.coalesce`, `func.sum`, `select`, `select(Payment).where` ? (24 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`, `self.db.flush`.
- `PaymentService._refund_response` (sync), lines 485?495: No function docstring; consult the source body and layer walkthrough.
  Calls: `RefundResponse`.
- `PaymentService.list_admin_refunds` (async), lines 497?507: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaginatedRefunds`, `self._refund_admin_row`, `self.payment_repo.list_refunds_admin`.
- `PaymentService.get_admin_refund` (async), lines 509?533: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminRefundDetailResponse`, `NotFoundError`, `RefundHistoryEvent`, `history.append`, `self._refund_admin_row`, `self._refund_admin_row(refund).model_dump`, `self._refund_payment_balance`, `self.payment_repo.get_refund_admin`.
- `PaymentService.get_payment_refund_history` (async), lines 535?549: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `PaymentRefundHistoryResponse`, `self._refund_admin_row`, `self._refund_payment_balance`, `self._refund_payment_balance(payment).model_dump`, `self.payment_repo.get_payment_refunds`, `sorted`.
- `PaymentService._refund_admin_row` (sync), lines 552?570: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminRefundRowResponse`.
- `PaymentService._refund_payment_balance` (sync), lines 573?598: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `RefundPaymentBalanceResponse`, `max`, `sum`.
- `PaymentService.record_cod_collection` (async), lines 600?630: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `CommissionService`, `CommissionService(self.db).settle`, `NotFoundError`, `OrderRepository`, `OrderRepository(self.db).get_by_id`, `datetime.now`, `self.db.commit`, `self.db.get`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.commit`.
- `PaymentService.list_admin` (async), lines 632?651: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaginatedPayments`, `PaymentRowResponse`, `filters.get`, `self.payment_repo.list_admin`.
- `PaymentService.gateway_status` (async), lines 653?661: No function docstring; consult the source body and layer walkthrough.
  Calls: `GatewayStatusResponse`.

## app/services/platform_settings.py

15 lines; SHA-256 `a6108e6133c60a7817294609a7211bd08f9ad1ddbeb30d56fff7fa024f9f7ba5`. [Open source](../../app/services/platform_settings.py).

Backend imports: `app.core.config`, `app.models.admin`, `app.schemas.admin`.

- `get_platform_settings` (async), lines 11?15: No function docstring; consult the source body and layer walkthrough.
  Calls: `PlatformSettingsResponse.model_validate`, `db.execute`, `getattr`, `key.upper`, `result.scalars`, `result.scalars().all`, `select`, `select(SystemSetting).execution_options`, `values.update`.

## app/services/product_service.py

537 lines; SHA-256 `e8fead74fda576f13405a994b3e6ab7b4aa5815cc1e790630ab1cd8223108e26`. [Open source](../../app/services/product_service.py).

Backend imports: `app.core.exceptions`, `app.core.logging`, `app.models.analytics`, `app.models.product`, `app.models.seller`, `app.repositories.inventory_repo`, `app.repositories.product_repo`, `app.repositories.seller_repo`, `app.schemas.product`, `app.services.image_service`.

- `_slugify` (sync), lines 49?53: No function docstring; consult the source body and layer walkthrough.
  Calls: `re.sub`, `text.lower`, `text.lower().strip`, `text.lower().strip().encode`, `text.lower().strip().encode('ascii', errors='ignore').decode`, `text.strip`.
- Class `ProductService`, lines 56?537; bases: .
- `ProductService.__init__` (sync), lines 57?62: No function docstring; consult the source body and layer walkthrough.
  Calls: `InventoryRepository`, `ProductRepository`, `SellerRepository`, `VariantRepository`.
- `ProductService.create_product` (async), lines 66?117: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Decimal`, `PermissionDeniedError`, `SizeType`, `select`, `select(Seller.id).where`, `select(Seller.id).where(Seller.id == seller_id).with_for_update`, `self._to_detail`, `self._unique_slug`, `self._validate_category`, `self.db.commit`, `self.db.execute` ? (22 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.update_product` (async), lines 121?142: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Decimal`, `data.get`, `payload.model_dump`, `self._require_owned`, `self._to_detail`, `self._validate_category`, `self.db.commit`, `self.product_repo.get_by_id`, `self.product_repo.update`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.publish_product` (async), lines 146?165: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `self._require_owned`, `self.db.commit`, `self.product_repo.set_published`, `self.seller_repo.get_by_id`, `self.seller_repo.increment_slots_used`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.unpublish_product` (async), lines 167?174: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `self._require_owned`, `self.db.commit`, `self.product_repo.set_published`, `self.seller_repo.decrement_slots_used`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.delete_product` (async), lines 178?183: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._require_owned`, `self.db.commit`, `self.product_repo.soft_delete`, `self.seller_repo.decrement_slots_used`.
  Mutation/I-O-related call names: `self.db.commit`, `self.product_repo.soft_delete`.
- `ProductService.add_images` (async), lines 187?212: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `ProductImageResponse.model_validate`, `enumerate`, `images.append`, `len`, `self._require_owned`, `self.db.commit`, `self.product_repo.add_image`, `self.product_repo.get_image_count`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.get_catalogue` (async), lines 216?234: No function docstring; consult the source body and layer walkthrough.
  Calls: `' '.join`, `AnalyticsEvent`, `CataloguePage`, `CursorPagination`, `filters.get`, `filters['q'].lower`, `filters['q'].lower().split`, `len`, `self._to_card`, `self.db.add`, `self.db.commit`, `self.product_repo.list_catalogue`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.get_product_detail` (async), lines 236?243: No function docstring; consult the source body and layer walkthrough.
  Calls: `AnalyticsEvent`, `NotFoundError`, `self._is_public`, `self._to_detail`, `self.db.add`, `self.db.commit`, `self.product_repo.get_by_id`, `self.product_repo.increment_view_count`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.get_product_by_slug` (async), lines 245?252: No function docstring; consult the source body and layer walkthrough.
  Calls: `AnalyticsEvent`, `NotFoundError`, `self._is_public`, `self._to_detail`, `self.db.add`, `self.db.commit`, `self.product_repo.get_by_slug`, `self.product_repo.increment_view_count`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.get_variants` (async), lines 254?258: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self._is_public`, `self._to_variant`, `self.product_repo.get_by_id`.
- `ProductService.search_suggestions` (async), lines 260?277: No function docstring; consult the source body and layer walkthrough.
  Calls: `BrandSuggestion`, `SearchSuggestion`, `SearchSuggestionsResponse`, `int`, `next`, `self.product_repo.search_suggestions`.
- `ProductService.get_seller_products` (async), lines 281?311: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `SellerProductRowResponse`, `SellerProductsPage`, `SlotInfoResponse`, `float`, `int`, `len`, `self.product_repo.get_seller_products`, `self.seller_repo.get_by_id`, `sum`.
- `ProductService._require_owned` (async), lines 315?322: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `PermissionDeniedError`, `select`, `select(Seller.id).where`, `select(Seller.id).where(Seller.id == seller_id).with_for_update`, `self.db.execute`, `self.product_repo.get_by_id`.
- `ProductService._unique_slug` (async), lines 324?331: No function docstring; consult the source body and layer walkthrough.
  Calls: `_slugify`, `self.product_repo.slug_exists`.
- `ProductService._to_card` (sync), lines 334?368: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductCardResponse`, `datetime.now`, `float`, `int`, `list`, `next`, `p.created_at.replace`.
- `ProductService._to_variant` (sync), lines 371?385: No function docstring; consult the source body and layer walkthrough.
  Calls: `VariantWithStockResponse`, `int`.
- `ProductService._to_detail` (sync), lines 387?407: No function docstring; consult the source body and layer walkthrough.
  Calls: `CategoryResponse.model_validate`, `ProductDetailResponse`, `ProductImageResponse.model_validate`, `SellerSummaryResponse`, `card.model_dump`, `self._to_card`, `self._to_variant`.
- `ProductService._is_public` (sync), lines 410?419: No function docstring; consult the source body and layer walkthrough.
  Calls: `bool`.
- `ProductService._validate_category` (async), lines 421?425: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `self.db.get`.
- `ProductService.get_seller_detail` (async), lines 427?428: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._require_owned`, `self._to_detail`.
- `ProductService.add_variant` (async), lines 430?446: No function docstring; consult the source body and layer walkthrough.
  Calls: `ConflictError`, `SizeType`, `select`, `select(ProductVariant.id).where`, `self._require_owned`, `self.db.commit`, `self.db.scalar`, `self.get_seller_detail`, `self.inv_repo.create`, `self.variant_repo.create`, `uuid.uuid4`, `uuid.uuid4().hex[:16].upper`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.update_variant` (async), lines 448?458: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `SizeType`, `next`, `payload.model_dump`, `payload.model_dump(exclude_unset=True).items`, `self._require_owned`, `self._to_variant`, `self.db.commit`, `setattr`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.reorder_images` (async), lines 460?470: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `enumerate`, `len`, `self._require_owned`, `self.db.commit`, `set`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.primary_image` (async), lines 472?478: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self._require_owned`, `self.db.commit`, `self.product_repo.set_primary_image`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ProductService.delete_image` (async), lines 480?499: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `ImageService`, `ImageService().delete`, `NotFoundError`, `get_logger`, `get_logger(__name__).warning`, `len`, `next`, `self._require_owned`, `self.db.commit`, `self.db.delete`, `str`.
  Mutation/I-O-related call names: `ImageService().delete`, `self.db.commit`, `self.db.delete`.
- `ProductService.admin_list` (async), lines 501?529: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.scalars(query.order_by(Product.created_at.desc(), Product.id.desc()).offset((page - 1) * 25).limit(25))).all`, `Product.created_at.desc`, `Product.deleted_at.is_`, `Product.id.desc`, `func.count`, `query.order_by`, `query.order_by(Product.created_at.desc(), Product.id.desc()).offset`, `query.order_by(Product.created_at.desc(), Product.id.desc()).offset((page - 1) * 25).limit`, `query.subquery`, `query.where`, `select`, `select(Product).where` ? (15 distinct call expressions).
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `ProductService.set_hidden` (async), lines 531?537: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self.db.commit`, `self.product_repo.get_by_id`.
  Mutation/I-O-related call names: `self.db.commit`.

## app/services/return_service.py

678 lines; SHA-256 `747477cd1aa28becb717a3ea6a5885a211391436d94b088f2e707320d6da3b56`. [Open source](../../app/services/return_service.py).

Backend imports: `app.core.exceptions`, `app.models.order`, `app.models.payment`, `app.models.return_`, `app.models.user`, `app.repositories.inventory_repo`, `app.repositories.return_repo`, `app.schemas.payment`, `app.schemas.return_`, `app.services.order_access`, `app.services.payment_service`.

- Class `ReturnService`, lines 49?678; bases: .
- `ReturnService.__init__` (sync), lines 50?54: No function docstring; consult the source body and layer walkthrough.
  Calls: `DisputeRepository`, `InventoryRepository`, `ReturnRepository`.
- `ReturnService.request_return` (async), lines 58?75: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `PermissionDeniedError`, `order_result.scalar_one_or_none`, `select`, `select(Order).where`, `select(SellerOrder).where`, `select(SellerOrder).where(SellerOrder.id == payload.seller_order_id).with_for_update`, `self._create_return`, `self.db.execute`, `so_result.scalar_one_or_none`.
- `ReturnService.request_guest_return` (async), lines 77?98: No function docstring; consult the source body and layer walkthrough.
  Calls: `AuthenticationError`, `NotFoundError`, `authorized_order`, `select`, `select(SellerOrder).where`, `select(SellerOrder).where(SellerOrder.id == payload.seller_order_id).with_for_update`, `self._create_return`, `self.db.scalar`.
- `ReturnService._create_return` (async), lines 100?152: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `func.coalesce`, `func.sum`, `item_result.scalar_one_or_none`, `len`, `select`, `select(OrderItem).where`, `select(func.coalesce(func.sum(ReturnItem.quantity), 0)).join`, `select(func.coalesce(func.sum(ReturnItem.quantity), 0)).join(Return).where`, `self._to_detail`, `self.db.commit`, `self.db.execute` ? (16 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.get_return` (async), lines 154?158: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self._to_detail`, `self.return_repo.get_by_id`.
- `ReturnService.get_guest_return` (async), lines 160?172: No function docstring; consult the source body and layer walkthrough.
  Calls: `AuthenticationError`, `NotFoundError`, `guest_token_matches`, `self._to_detail`, `self.return_repo.get_by_id`.
- `ReturnService.list_returns` (async), lines 174?180: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaginatedReturns`, `max`, `self._to_row`, `self.return_repo.list_by_user`.
- `ReturnService.open_dispute` (async), lines 184?212: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `select`, `select(SellerOrder).where`, `self._to_dispute`, `self.db.commit`, `self.db.execute`, `self.dispute_repo.add_message`, `self.dispute_repo.create`, `self.dispute_repo.get_by_id`, `self.return_repo.get_by_id`, `so_result.scalar_one_or_none`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.get_dispute` (async), lines 214?220: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self._to_dispute`, `self.return_repo.get_by_id`.
- `ReturnService.add_message` (async), lines 222?243: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `DisputeMessageResponse`, `NotFoundError`, `self.db.commit`, `self.dispute_repo.add_message`, `self.dispute_repo.get_by_return_id`, `self.return_repo.get_by_id`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.seller_list_returns` (async), lines 247?256: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaginatedReturns`, `max`, `self._to_row`, `self.return_repo.list_seller`.
- `ReturnService.get_seller_return` (async), lines 258?288: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Refund.created_at.desc`, `SellerReturnDetailResponse`, `select`, `select(Payment).where`, `select(Refund).where`, `select(Refund).where(Refund.return_id == return_.id).order_by`, `select(Refund).where(Refund.return_id == return_.id).order_by(Refund.created_at.desc()).limit`, `self._available_seller_actions`, `self._calculate_refund_amount`, `self._get_return_seller`, `self._load_order_items` ? (17 distinct call expressions).
- `ReturnService.seller_approve_return` (async), lines 290?300: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `self._get_return_seller`, `self.db.commit`, `self.return_repo.update_status`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.seller_reject_return` (async), lines 302?312: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `self._get_return_seller`, `self.db.commit`, `self.return_repo.update_status`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.seller_mark_received` (async), lines 314?324: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `self._get_return_seller`, `self.db.commit`, `self.return_repo.update_status`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.admin_list_returns` (async), lines 328?336: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaginatedReturns`, `max`, `self._to_row`, `self.return_repo.list_admin`.
- `ReturnService.get_admin_return` (async), lines 338?412: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminReturnCustomerResponse`, `AdminReturnDetailResponse`, `AdminReturnDisputeResponse`, `AdminReturnOrderResponse`, `AdminReturnRefundResponse`, `AdminReturnSellerResponse`, `BusinessRuleError`, `Refund.created_at.desc`, `select`, `select(Payment).where`, `select(Refund).where`, `select(Refund).where(Refund.return_id == return_.id).order_by` ? (25 distinct call expressions).
- `ReturnService.approve_return` (async), lines 414?422: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `self._get_return_admin`, `self.db.commit`, `self.return_repo.update_status`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.reject_return` (async), lines 424?432: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `self._get_return_admin`, `self.db.commit`, `self.return_repo.update_status`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.mark_received` (async), lines 434?442: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `self._get_return_admin`, `self.db.commit`, `self.return_repo.update_status`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.process_refund` (async), lines 444?468: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `PaymentService`, `PaymentService(self.db).refund`, `RefundRequest`, `select`, `select(Payment).where`, `self._calculate_refund_amount`, `self._get_return_admin`, `self._load_order_items`, `self.db.commit`, `self.db.get`, `self.db.scalar` ? (13 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.admin_list_disputes` (async), lines 472?480: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._to_dispute`, `self.dispute_repo.list_admin`.
- `ReturnService.get_admin_dispute` (async), lines 482?486: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self._to_dispute`, `self.dispute_repo.get_by_id`.
- `ReturnService.add_admin_message` (async), lines 488?513: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `DisputeMessageResponse`, `NotFoundError`, `self.db.commit`, `self.dispute_repo.add_message`, `self.dispute_repo.get_by_id`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService.resolve_dispute` (async), lines 515?537: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `self._to_dispute`, `self.db.commit`, `self.dispute_repo.get_by_id`, `self.dispute_repo.resolve`.
  Mutation/I-O-related call names: `self.db.commit`.
- `ReturnService._get_return_admin` (async), lines 541?545: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self.return_repo.get_by_id`.
- `ReturnService._get_return_seller` (async), lines 547?555: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self.return_repo.get_by_seller`.
- `ReturnService._load_order_items` (async), lines 557?567: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(select(OrderItem).where(OrderItem.id.in_(ids)))).scalars`, `(await self.db.execute(select(OrderItem).where(OrderItem.id.in_(ids)))).scalars().all`, `BusinessRuleError`, `OrderItem.id.in_`, `len`, `select`, `select(OrderItem).where`, `self.db.execute`.
- `ReturnService._calculate_refund_amount` (sync), lines 570?581: No function docstring; consult the source body and layer walkthrough.
  Calls: `(item_total * (order.subtotal - order.discount_amount) / order.subtotal).quantize`, `BusinessRuleError`, `Decimal`, `sum`.
- `ReturnService._available_admin_actions` (sync), lines 584?598: No function docstring; consult the source body and layer walkthrough.
- `ReturnService._available_seller_actions` (sync), lines 601?606: No function docstring; consult the source body and layer walkthrough.
- `ReturnService._to_admin_items` (sync), lines 609?627: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminReturnItemResponse`.
- `ReturnService._to_row` (sync), lines 630?640: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnRowResponse`, `len`.
- `ReturnService._to_detail` (sync), lines 643?660: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnDetailResponse`, `ReturnItemResponse`, `len`.
- `ReturnService._to_dispute` (sync), lines 663?678: No function docstring; consult the source body and layer walkthrough.
  Calls: `DisputeDetailResponse`, `DisputeMessageResponse`.

## app/services/revenue.py

22 lines; SHA-256 `3c08edbdaaf28894e66a6724a3819043c92ea8d0a987afecb313c7aa0ecb9de3`. [Open source](../../app/services/revenue.py).

Backend imports: `app.models.seller`, `app.models.wallet`.

- `seller_fee_revenue` (async), lines 13?22: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `WalletTransaction.reference.like`, `db.scalar`, `func.coalesce`, `func.sum`, `select`, `select(func.coalesce(func.sum(Seller.registration_fee), 0)).where`, `select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where`.

## app/services/seller_service.py

244 lines; SHA-256 `815de0a1f2fa617b5b8685f5a4a37718bba3943126de715766fbb9b3770becb1`. [Open source](../../app/services/seller_service.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.core.logging`, `app.core.security`, `app.models.order`, `app.models.seller`, `app.models.user`, `app.models.wallet`, `app.repositories.seller_repo`, `app.repositories.user_repo`, `app.schemas.seller`, `app.services.slot_service`.

- `_slugify` (sync), lines 32?37: No function docstring; consult the source body and layer walkthrough.
  Calls: `re.sub`, `text.encode`, `text.encode('ascii', errors='ignore').decode`, `text.lower`, `text.lower().strip`, `text.strip`.
- Class `SellerService`, lines 40?244; bases: .
- `SellerService.__init__` (sync), lines 41?46: No function docstring; consult the source body and layer walkthrough.
  Calls: `BankAccountRepository`, `SellerRepository`, `WalletRepository`.
- `SellerService.register` (async), lines 50?117: No function docstring; consult the source body and layer walkthrough.
  Calls: `ConflictError`, `Decimal`, `RedisSettings.from_dsn`, `SellerRegistrationResponse`, `SlotService`, `SlotService(self.db).get_pricing`, `create_email_verify_token`, `create_pool`, `get_logger`, `get_logger(__name__).warning`, `hash_password`, `pool.aclose` ? (21 distinct call expressions).
  Mutation/I-O-related call names: `pool.enqueue_job`, `self.db.commit`.
- `SellerService.get_profile` (async), lines 121?123: No function docstring; consult the source body and layer walkthrough.
  Calls: `self._require_seller`, `self._to_profile`.
- `SellerService.update_profile` (async), lines 125?132: No function docstring; consult the source body and layer walkthrough.
  Calls: `payload.model_dump`, `payload.model_dump().items`, `self._require_seller`, `self._to_profile`, `self.db.commit`, `self.seller_repo.update_profile`.
  Mutation/I-O-related call names: `self.db.commit`.
- `SellerService.update_logo` (async), lines 134?138: No function docstring; consult the source body and layer walkthrough.
  Calls: `LogoUploadResponse`, `self._require_seller`, `self.db.commit`, `self.seller_repo.update_logo`.
  Mutation/I-O-related call names: `self.db.commit`.
- `SellerService.get_dashboard` (async), lines 142?174: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(select(SellerOrder.status, func.count()).where(SellerOrder.seller_id == seller.id, SellerOrder.created_at >= start).group_by(SellerOrder.status))).all`, `(await self.db.execute(select(func.coalesce(func.sum(CommissionLedger.gross_amount), 0), func.coalesce(func.sum(CommissionLedger.commission_amount), 0), func.coalesce(func.sum(CommissionLedger.seller_amount), 0)).where(CommissionLedger.seller_id == seller.id, CommissionLedger.settled_at >= start))).one`, `OrderStatusBreakdown`, `SellerDashboardResponse`, `counts.values`, `datetime.now`, `func.coalesce`, `func.count`, `func.sum`, `now.replace`, `select`, `select(SellerOrder.status, func.count()).where` ? (22 distinct call expressions).
- `SellerService.list_bank_accounts` (async), lines 178?181: No function docstring; consult the source body and layer walkthrough.
  Calls: `BankAccountResponse.model_validate`, `self._require_seller`, `self.bank_repo.list_by_seller`.
- `SellerService.add_bank_account` (async), lines 183?192: No function docstring; consult the source body and layer walkthrough.
  Calls: `BankAccountResponse.model_validate`, `payload.model_dump`, `self._require_seller`, `self.bank_repo.clear_default`, `self.bank_repo.create`, `self.db.commit`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.commit`.
- `SellerService.delete_bank_account` (async), lines 194?199: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self._require_seller`, `self.bank_repo.delete`, `self.db.commit`.
  Mutation/I-O-related call names: `self.bank_repo.delete`, `self.db.commit`.
- `SellerService._require_seller` (async), lines 203?207: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `self.seller_repo.get_by_user_id`.
- `SellerService._require_active` (sync), lines 210?214: No function docstring; consult the source body and layer walkthrough.
  Calls: `PermissionDeniedError`.
- `SellerService._unique_slug` (async), lines 216?223: No function docstring; consult the source body and layer walkthrough.
  Calls: `_slugify`, `self.seller_repo.get_by_slug`.
- `SellerService._to_profile` (sync), lines 226?244: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `SellerProfileResponse`.

## app/services/slot_service.py

118 lines; SHA-256 `e9999276f08fb220f7a9b69bbd7a2873c30e8c7ca29f6e571348126179a137fd`. [Open source](../../app/services/slot_service.py).

Backend imports: `app.core.exceptions`, `app.models.seller`, `app.models.wallet`, `app.repositories.seller_repo`, `app.repositories.wallet_repo`, `app.schemas.seller`, `app.services.platform_settings`.

- Class `SlotService`, lines 20?118; bases: .
- `SlotService.__init__` (sync), lines 21?24: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerRepository`, `WalletRepository`.
- `SlotService.get_pricing` (async), lines 26?35: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPricingResponse`, `get_platform_settings`.
- `SlotService.calculate_pricing` (sync), lines 40?50: No function docstring; consult the source body and layer walkthrough.
  Calls: `SlotPricingResponse`.
- `SlotService.purchase_slots` (async), lines 52?86: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Decimal`, `NotFoundError`, `PermissionDeniedError`, `SlotPurchaseResponse`, `get_platform_settings`, `hasattr`, `int`, `select`, `select(Seller.id).where`, `select(Seller.id).where(Seller.id == seller.id).with_for_update`, `select(SellerWallet.id).where` ? (18 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `SlotService.assert_slot_available` (async), lines 89?97: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `PermissionDeniedError`, `self.seller_repo.get_by_id`.
- `SlotService._charge_wallet` (async), lines 101?118: No function docstring; consult the source body and layer walkthrough.
  Calls: `InsufficientBalanceError`, `NotFoundError`, `WalletTransactionRepository`, `WalletTransactionRepository(self.db).create`, `int`, `self.db.refresh`, `self.wallet_repo.debit_available`, `self.wallet_repo.get_by_seller_id`, `uuid4`.

## app/services/wallet_service.py

306 lines; SHA-256 `7299713fc9090bc4c1ce810aa6125acef643e846c24afdb1f994a437f928d1b6`. [Open source](../../app/services/wallet_service.py).

Backend imports: `app.core.exceptions`, `app.models.seller`, `app.models.wallet`, `app.repositories.seller_repo`, `app.repositories.wallet_repo`, `app.schemas.wallet`.

- Class `WalletService`, lines 27?306; bases: .
- `WalletService.__init__` (sync), lines 28?34: No function docstring; consult the source body and layer walkthrough.
  Calls: `CommissionRepository`, `PayoutRepository`, `SellerRepository`, `WalletRepository`, `WalletTransactionRepository`.
- `WalletService.get_summary` (async), lines 38?47: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotFoundError`, `WalletSummaryResponse`, `self.wallet_repo.get_by_seller_id`.
- `WalletService.get_transactions` (async), lines 51?74: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaginatedTransactions`, `WalletTransactionResponse`, `max`, `self.tx_repo.list_by_seller`.
- `WalletService.request_withdrawal` (async), lines 78?146: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Decimal`, `NotFoundError`, `PayoutResponse`, `int`, `result.scalar_one_or_none`, `select`, `select(SellerBankAccount).where`, `self.db.commit`, `self.db.execute`, `self.payout_repo.create`, `self.tx_repo.create` ? (15 distinct call expressions).
  Mutation/I-O-related call names: `self.db.commit`.
- `WalletService.get_payouts` (async), lines 150?174: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaginatedPayouts`, `PayoutResponse`, `max`, `self.payout_repo.list_by_seller`.
- `WalletService.get_commission_breakdown` (async), lines 178?204: No function docstring; consult the source body and layer walkthrough.
  Calls: `CommissionBreakdownResponse`, `CommissionEntryResponse`, `CommissionSummary`, `float`, `self.comm_repo.list_by_seller`.
- `WalletService.admin_overview` (async), lines 208?227: No function docstring; consult the source body and layer walkthrough.
  Calls: `AdminWalletOverviewResponse`, `result.one`, `select`, `self.db.execute`, `self.payout_repo.list_admin`, `sqlfunc.coalesce`, `sqlfunc.sum`.
- `WalletService.admin_approve_payout` (async), lines 229?251: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `PayoutResponse`, `self.db.commit`, `self.payout_repo.get_by_id`, `self.payout_repo.update_status`.
  Mutation/I-O-related call names: `self.db.commit`.
- `WalletService.admin_reject_payout` (async), lines 253?288: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Decimal`, `NotFoundError`, `PayoutResponse`, `self.db.commit`, `self.payout_repo.get_by_id`, `self.payout_repo.update_status`, `self.tx_repo.create`, `self.wallet_repo.credit_available`, `self.wallet_repo.get_by_seller_id`, `str`.
  Mutation/I-O-related call names: `self.db.commit`.
- `WalletService.admin_complete_payout` (async), lines 290?306: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `NotFoundError`, `PayoutResponse.model_validate`, `datetime.now`, `self.db.commit`, `self.payout_repo.get_by_id`.
  Mutation/I-O-related call names: `self.db.commit`.



# Backend source index: workers-integrations

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## app/integrations/payfast.py

259 lines; SHA-256 `1d6687cd7014448e7457bef4daf7d1d63a544df095857b5b97caf92a8605208a`. [Open source](../../app/integrations/payfast.py).

- Class `PayFastProtocolError`, lines 35-36; bases: ValueError.
- Class `PayFastClient`, lines 39-252; bases: .
- `PayFastClient.__init__` (sync), lines 42-64: No function docstring; consult the source body and layer walkthrough.
  Calls: `api_base_url.strip`, `api_base_url.strip().rstrip`, `checkout_url.strip`, `merchant_id.strip`, `merchant_name.strip`, `secured_key.strip`, `token_url.strip`.
- `PayFastClient.base_url` (sync), lines 67-69: Compatibility alias used by the payment response schema.
- `PayFastClient._ensure_configured` (sync), lines 71-73: No function docstring; consult the source body and layer walkthrough.
  Calls: `PayFastProtocolError`.
- `PayFastClient._post_form` (async), lines 75-82: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.post`, `httpx.AsyncClient`, `response.raise_for_status`, `self._http_client.post`.
- `PayFastClient._get` (async), lines 84-93: No function docstring; consult the source body and layer walkthrough.
  Calls: `client.get`, `httpx.AsyncClient`, `response.raise_for_status`, `self._http_client.get`.
- `PayFastClient.get_checkout_token` (async), lines 95-123: Request a one-time token server-side; never expose the secured key.
  Calls: `PayFastProtocolError`, `_format_amount`, `isinstance`, `payload.get`, `response.json`, `self._ensure_configured`, `self._post_form`, `str`, `str(payload.get('ACCESS_TOKEN') or payload.get('access_token') or '').strip`, `str(payload.get('MERCHANT_ID') or payload.get('merchant_id') or self.merchant_id).strip`.
- `PayFastClient.build_checkout_payload` (sync), lines 125-162: Build the documented uppercase form POST for hosted checkout.
  Calls: `PayFastProtocolError`, `_format_amount`, `customer_email.strip`, `customer_email.strip().lower`, `customer_mobile.strip`, `description.strip`, `order_date.isoformat`, `secrets.token_urlsafe`, `self._ensure_configured`, `token.strip`.
- `PayFastClient.callback_hash` (sync), lines 164-167: Compute SHA-256(basket/secured-key/merchant/error-code).
  Calls: `hashlib.sha256`, `hashlib.sha256(source.encode()).hexdigest`, `source.encode`.
- `PayFastClient.parse_callback` (sync), lines 169-203: Verify and normalize a hosted-checkout redirect/IPN notification.
  Calls: `(normalized.get('currency_code') or 'PKR').upper`, `Decimal`, `PayFastProtocolError`, `amount.is_finite`, `dict`, `hmac.compare_digest`, `normalized.get`, `normalized.get('basket_id', '').strip`, `normalized.get('err_code', '').strip`, `normalized.get('err_msg', '').strip`, `normalized.get('paymentname', '').strip`, `normalized.get('transaction_id', '').strip` ... (19 distinct call expressions).
- `PayFastClient.check_status` (async), lines 205-252: Query PayFast's API-based status service when enabled for the merchant.
  Calls: `PayFastProtocolError`, `isinstance`, `order_date.isoformat`, `response.json`, `self._ensure_configured`, `self._get`, `self._post_form`, `str`, `str(token_payload.get('access_token') or '').strip`, `token_payload.get`, `token_response.json`.
- `_format_amount` (sync), lines 255-259: No function docstring; consult the source body and layer walkthrough.
  Calls: `Decimal`, `PayFastProtocolError`, `value.is_finite`, `value.quantize`.

## app/integrations/resend_client.py

230 lines; SHA-256 `b2d7d74e2d17b8251237d44d74ade1f6bd40cbe8f99394968c7b8ff035a9bd49`. [Open source](../../app/integrations/resend_client.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.core.logging`.

- `_configure_resend` (sync), lines 19-22: No function docstring; consult the source body and layer walkthrough.
  Calls: `ExternalServiceError`.
- Class `ResendClient`, lines 25-39; bases: .
- `ResendClient.send` (async), lines 28-39: No function docstring; consult the source body and layer walkthrough.
  Calls: `_configure_resend`, `asyncio.to_thread`.
  Mutation/I-O-related call names: `_configure_resend`.
- `send_email` (async), lines 42-72: Send a transactional email via Resend.
  Calls: `_configure_resend`, `asyncio.to_thread`, `isinstance`, `logger.error`, `logger.info`, `str`.
  Mutation/I-O-related call names: `_configure_resend`.
- `_base_template` (sync), lines 78-117: No function docstring; consult the source body and layer walkthrough.
- `send_verification_email` (async), lines 120-134: No function docstring; consult the source body and layer walkthrough.
  Calls: `_base_template`, `send_email`.
  Mutation/I-O-related call names: `send_email`.
- `send_password_reset_email` (async), lines 137-149: No function docstring; consult the source body and layer walkthrough.
  Calls: `_base_template`, `send_email`.
  Mutation/I-O-related call names: `send_email`.
- `send_order_confirmation_email` (async), lines 152-177: No function docstring; consult the source body and layer walkthrough.
  Calls: `''.join`, `_base_template`, `send_email`.
  Mutation/I-O-related call names: `send_email`.
- `send_shipping_notification_email` (async), lines 180-200: No function docstring; consult the source body and layer walkthrough.
  Calls: `_base_template`, `send_email`.
  Mutation/I-O-related call names: `send_email`.
- `send_cod_timeout_email` (async), lines 203-215: No function docstring; consult the source body and layer walkthrough.
  Calls: `_base_template`, `send_email`.
  Mutation/I-O-related call names: `send_email`.
- `send_seller_approved_email` (async), lines 218-230: No function docstring; consult the source body and layer walkthrough.
  Calls: `_base_template`, `send_email`.
  Mutation/I-O-related call names: `send_email`.

## app/integrations/stripe_client.py

59 lines; SHA-256 `3968e52d6013acd30791355d684839d2b57ebc8d42b1fc0777967b7c5bbcc0fc`. [Open source](../../app/integrations/stripe_client.py).

Backend imports: `app.core.exceptions`.

- Class `StripeClient`, lines 9-59; bases: .
- `StripeClient.__init__` (sync), lines 14-16: No function docstring; consult the source body and layer walkthrough.
- `StripeClient.create_payment_intent` (async), lines 18-40: Create Stripe PaymentIntent.
  Calls: `ExternalServiceError`, `stripe.PaymentIntent.create`.
- `StripeClient.verify_webhook` (sync), lines 42-53: Verify Stripe webhook signature and return the event.
  Calls: `AppValidationError`, `dict`, `stripe.Webhook.construct_event`.
- `StripeClient.get_payment_intent_id` (sync), lines 55-56: No function docstring; consult the source body and layer walkthrough.
  Calls: `event.get`, `event.get('data', {}).get`, `event.get('data', {}).get('object', {}).get`.
- `StripeClient.get_order_id_from_event` (sync), lines 58-59: No function docstring; consult the source body and layer walkthrough.
  Calls: `event.get`, `event.get('data', {}).get`, `event.get('data', {}).get('object', {}).get`, `event.get('data', {}).get('object', {}).get('metadata', {}).get`.

## app/integrations/supabase_storage.py

127 lines; SHA-256 `5c0859ebcff2874c4ba3dde3d6875542e0c151e051dbeeb45d35c36fb23c0652`. [Open source](../../app/integrations/supabase_storage.py).

Backend imports: `app.core.config`, `app.core.exceptions`.

- Class `SupabaseStorage`, lines 9-127; bases: .
- `SupabaseStorage.__init__` (sync), lines 15-17: No function docstring; consult the source body and layer walkthrough.
  Calls: `str`, `str(settings.SUPABASE_URL).rstrip`.
- `SupabaseStorage._headers` (sync), lines 19-26: No function docstring; consult the source body and layer walkthrough.
- `SupabaseStorage.upload` (async), lines 28-49: Upload bytes to Supabase Storage and return the public URL.
  Calls: `StorageError`, `client.post`, `httpx.AsyncClient`, `self._headers`, `self.get_public_url`.
- `SupabaseStorage.get_public_url` (sync), lines 51-52: No function docstring; consult the source body and layer walkthrough.
- `SupabaseStorage.delete` (async), lines 54-67: Delete a file from Supabase Storage.
  Calls: `StorageError`, `client.delete`, `httpx.AsyncClient`, `response.raise_for_status`, `self._headers`.
  Mutation/I-O-related call names: `client.delete`.
- `SupabaseStorage.list_all_files` (async), lines 69-127: List all files under a bucket (or prefix) using the Supabase Storage
  Calls: `StorageError`, `client.post`, `files.append`, `httpx.AsyncClient`, `isinstance`, `item.get`, `len`, `name.startswith`, `pending.append`, `pending.pop`, `prefix.strip`, `response.json` ... (19 distinct call expressions).

## app/tasks/cleanup_tasks.py

255 lines; SHA-256 `cd76a236ba59f95135e7ad64b22b6e973538f0e1d7319e688760c0030489d9fb`. [Open source](../../app/tasks/cleanup_tasks.py).

Backend imports: `app.core.config`, `app.core.database`, `app.core.logging`, `app.core.redis`, `app.integrations.supabase_storage`, `app.models.admin`, `app.models.notification`, `app.models.product`, `app.models.seller`, `app.models.user`.

- `cleanup_abandoned_carts` (async), lines 27-49: Delete Redis cart keys that have had no activity for 30 days.
  Calls: `get_redis`, `logger.info`, `redis.expire`, `redis.scan_iter`, `redis.ttl`.
- `cleanup_expired_sessions` (async), lines 57-71: Hard-delete UserSession rows whose expires_at is in the past.
  Calls: `AsyncSessionLocal`, `datetime.now`, `db.commit`, `db.execute`, `delete`, `delete(UserSession).where`, `logger.info`.
  Mutation/I-O-related call names: `db.commit`, `delete`, `delete(UserSession).where`.
- `cleanup_soft_deleted_users` (async), lines 79-99: Hard-delete User rows that were soft-deleted more than 90 days ago.
  Calls: `AsyncSessionLocal`, `User.deleted_at.isnot`, `datetime.now`, `db.commit`, `db.execute`, `delete`, `delete(User).where`, `logger.info`, `timedelta`.
  Mutation/I-O-related call names: `User.deleted_at.isnot`, `db.commit`, `delete`, `delete(User).where`.
- `cleanup_expired_reset_tokens` (async), lines 107-126: Password-reset tokens are stored in Redis with a 1-hour TTL.
  Calls: `get_redis`, `logger.info`, `redis.exists`, `redis.smembers`, `redis.srem`.
- `archive_old_notifications` (async), lines 134-159: Mark notifications as archived if they are:
  Calls: `AsyncSessionLocal`, `Notification.is_archived.is_`, `Notification.read_at.isnot`, `datetime.now`, `db.commit`, `db.execute`, `logger.info`, `timedelta`, `update`, `update(Notification).where`, `update(Notification).where(Notification.read_at.isnot(None), Notification.created_at < cutoff, Notification.is_archived.is_(False)).values`.
  Mutation/I-O-related call names: `db.commit`.
- `cleanup_orphaned_images` (async), lines 167-243: Scan Supabase storage for product/avatar images that have no matching
  Calls: `AsyncSessionLocal`, `SupabaseStorage`, `_storage_timestamp`, `bucket_columns.items`, `bucket_columns.setdefault`, `bucket_columns.setdefault(bucket, []).extend`, `column.is_not`, `datetime.now`, `db.scalars`, `file_info.get`, `file_name.split`, `logger.error` ... (24 distinct call expressions).
  Mutation/I-O-related call names: `storage.delete`.
- `_storage_timestamp` (sync), lines 246-255: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.fromisoformat`, `isinstance`, `parsed.astimezone`, `value.replace`, `value.strip`.

## app/tasks/email_tasks.py

102 lines; SHA-256 `c331905825e3128980f3541389df20bae80b29682dc885aacd57bae62c03077f`. [Open source](../../app/tasks/email_tasks.py).

Backend imports: `app.core.logging`, `app.integrations.resend_client`.

- `task_send_verification_email` (async), lines 24-34: Send email verification link after registration.
  Calls: `Retry`, `ctx.get`, `logger.error`, `send_verification_email`.
  Mutation/I-O-related call names: `send_verification_email`.
- `task_send_password_reset_email` (async), lines 37-47: Send password reset link.
  Calls: `Retry`, `ctx.get`, `logger.error`, `send_password_reset_email`.
  Mutation/I-O-related call names: `send_password_reset_email`.
- `task_send_order_confirmation` (async), lines 50-61: No function docstring; consult the source body and layer walkthrough.
  Calls: `Retry`, `ctx.get`, `logger.error`, `send_order_confirmation_email`.
  Mutation/I-O-related call names: `send_order_confirmation_email`.
- `task_send_shipping_notification` (async), lines 64-78: No function docstring; consult the source body and layer walkthrough.
  Calls: `Retry`, `ctx.get`, `logger.error`, `send_shipping_notification_email`.
  Mutation/I-O-related call names: `send_shipping_notification_email`.
- `task_send_cod_timeout` (async), lines 81-90: No function docstring; consult the source body and layer walkthrough.
  Calls: `Retry`, `ctx.get`, `logger.error`, `send_cod_timeout_email`.
  Mutation/I-O-related call names: `send_cod_timeout_email`.
- `task_send_seller_approved` (async), lines 93-102: No function docstring; consult the source body and layer walkthrough.
  Calls: `Retry`, `ctx.get`, `logger.error`, `send_seller_approved_email`.
  Mutation/I-O-related call names: `send_seller_approved_email`.

## app/tasks/notification_tasks.py

115 lines; SHA-256 `0d9a458e24f0e696db7c950431f45aa4326ffedd03da1519f7bf5f10f23db180`. [Open source](../../app/tasks/notification_tasks.py).

Backend imports: `app.core.database`, `app.models.notification`, `app.services.notification_service`.

- `send_order_confirmation` (async), lines 17-28: Send order confirmation email + in-app notification.
  Calls: `AsyncSessionLocal`, `NotificationService`, `NotificationService(db).notify_order_placed`, `Retry`, `UUID`, `ctx.get`, `logger.error`, `logger.info`.
- `send_order_status_update` (async), lines 31-42: Notify customer of order status change.
  Calls: `AsyncSessionLocal`, `NotificationService`, `NotificationService(db).notify_order_status`, `Retry`, `UUID`, `ctx.get`, `logger.error`, `logger.info`.
- `send_payout_notification` (async), lines 45-56: Notify seller of payout status change.
  Calls: `AsyncSessionLocal`, `NotificationService`, `NotificationService(db).notify_payout`, `Retry`, `UUID`, `ctx.get`, `logger.error`, `logger.info`.
- `notify_seller_decision` (async), lines 59-71: Notify seller of approval or rejection.
  Calls: `AsyncSessionLocal`, `NotificationService`, `NotificationService(db).notify_seller_decision`, `Retry`, `UUID`, `ctx.get`, `logger.error`.
- `broadcast_notification` (async), lines 74-115: Fan-out broadcast notification to a list of user IDs.
  Calls: `AsyncSessionLocal`, `Retry`, `UUID`, `ctx.get`, `db.commit`, `db.execute`, `db.rollback`, `insert`, `insert(Notification).values`, `insert(Notification).values(id=notification_id, user_id=user_id, type=NotifType.BROADCAST, title=title, body=body, action_url=action_url).on_conflict_do_nothing`, `len`, `logger.error` ... (14 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`, `db.rollback`.

## app/tasks/order_tasks.py

108 lines; SHA-256 `8f99de6e1bc44869a872d8a97c583cde84b546da38c654b2a51676a41e1235d4`. [Open source](../../app/tasks/order_tasks.py).

Backend imports: `app.core.config`, `app.core.database`, `app.models.order`, `app.repositories.inventory_repo`, `app.repositories.order_repo`, `app.services.notification_service`, `app.services.platform_settings`.

- `cod_verification_timeout` (async), lines 15-72: Runs 30 minutes after a COD order is placed.
  Calls: `AsyncSessionLocal`, `InventoryRepository`, `OrderRepository`, `SellerOrderRepository`, `UUID`, `datetime.now`, `db.commit`, `db.rollback`, `get_platform_settings`, `inv_repo.release`, `logger.error`, `logger.info` ... (17 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`, `db.rollback`.
- `send_order_confirmation` (async), lines 75-82: No function docstring; consult the source body and layer walkthrough.
  Calls: `AsyncSessionLocal`, `NotificationService`, `NotificationService(db).notify_order_placed`, `UUID`, `logger.error`.
- `expire_pending_orders` (async), lines 84-108: Sweep expired reservations; no per-order queue job needs to survive an outage.
  Calls: `(await db.scalars(select(Order.id).where(or_(and_(Order.status == OrderStatus.pending_cod_verification, Order.created_at < now - timedelta(minutes=policy.cod_timeout_minutes)), and_(Order.status == OrderStatus.pending_payment, Order.created_at < now - timedelta(minutes=settings.PAYMENT_TIMEOUT_MINUTES)))).order_by(Order.created_at).limit(100).with_for_update(skip_locked=True))).all`, `AsyncSessionLocal`, `InventoryRepository`, `InventoryRepository(db).release`, `OrderRepository`, `OrderRepository(db).get_by_id`, `OrderRepository(db).update_status`, `SellerOrderRepository`, `SellerOrderRepository(db).update_status`, `and_`, `datetime.now`, `db.commit` ... (22 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.

## app/tasks/wallet_tasks.py

67 lines; SHA-256 `cec56c348569e70025c428de7d47c7cdadbf7e8ed3128b321c927edfd43bd675`. [Open source](../../app/tasks/wallet_tasks.py).

Backend imports: `app.core.config`, `app.core.database`, `app.models.order`, `app.models.payment`, `app.models.seller`, `app.models.wallet`, `app.repositories.wallet_repo`, `app.services.commission_service`, `app.services.platform_settings`.

- `settle_commission` (async), lines 14-30: Settle commission for a delivered SellerOrder.
  Calls: `AsyncSessionLocal`, `CommissionService`, `CommissionService(db).settle`, `UUID`, `db.rollback`, `logger.error`, `logger.info`.
  Mutation/I-O-related call names: `db.rollback`.
- `move_pending_to_available` (async), lines 33-67: Release only mature, unreleased ledger entries. Legacy job arguments are hints only.
  Calls: `(await db.scalars(select(CommissionLedger).where(CommissionLedger.released_at.is_(None), CommissionLedger.settled_at <= now - timedelta(days=policy.wallet_hold_days)).with_for_update(skip_locked=True))).all`, `AsyncSessionLocal`, `CommissionLedger.released_at.is_`, `WalletTransactionRepository`, `WalletTransactionRepository(db).create`, `datetime.now`, `db.commit`, `db.get`, `db.scalar`, `db.scalars`, `get_platform_settings`, `select` ... (21 distinct call expressions).
  Mutation/I-O-related call names: `db.commit`.

## app/tasks/worker.py

127 lines; SHA-256 `c2870656211f8a4239dde5b44f78276cc2324fb6382dd405e23fae11df0661b8`. [Open source](../../app/tasks/worker.py).

Backend imports: `app.core.config`, `app.core.database`, `app.core.logging`, `app.core.redis`, `app.tasks.cleanup_tasks`, `app.tasks.email_tasks`, `app.tasks.notification_tasks`, `app.tasks.order_tasks`, `app.tasks.wallet_tasks`.

- `startup` (async), lines 56-62: No function docstring; consult the source body and layer walkthrough.
  Calls: `configure_logging`, `init_db`, `init_redis`, `logger.info`.
- `shutdown` (async), lines 65-70: No function docstring; consult the source body and layer walkthrough.
  Calls: `close_db`, `close_redis`, `logger.info`.
- Class `WorkerSettings`, lines 73-127; bases: .



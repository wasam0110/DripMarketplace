# Backend source index: models

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## app/models/admin.py

37 lines; SHA-256 `1f8f5216da04a531bb7a0b9705c221f685399a56a1bac454af93b480c0cee17c`. [Open source](../../app/models/admin.py).

Backend imports: `app.models.base`.

- Class `SystemSetting`, lines 13-22; bases: Base.
  Annotated fields: `key`, `value`, `updated_by`, `updated_at`.
- Class `Banner`, lines 25-37; bases: Base, TimestampMixin.
  Annotated fields: `id`, `title`, `image_url`, `link_url`, `position`, `sort_order`, `is_active`, `valid_from`, `valid_until`.

## app/models/analytics.py

18 lines; SHA-256 `98c80ba229eeefb033bbe91df9086b6a81f43ec664588a0a25a8ccaf4059e096`. [Open source](../../app/models/analytics.py).

Backend imports: `app.models.base`.

- Class `AnalyticsEvent`, lines 10-18; bases: Base.
  Annotated fields: `id`, `kind`, `product_id`, `query`, `result_count`, `created_at`.

## app/models/base.py

96 lines; SHA-256 `81c91c8ea4eb069802892687b26aeff145c395d2a549900a7a2cf0662cc64f16`. [Open source](../../app/models/base.py).

- Class `Base`, lines 21-39; bases: DeclarativeBase.
- `Base.to_dict` (sync), lines 30-35: Utility for debugging — returns all column values as a dict.
  Calls: `getattr`.
- `Base.__repr__` (sync), lines 37-39: No function docstring; consult the source body and layer walkthrough.
  Calls: `getattr`.
- Class `UUIDPrimaryKeyMixin`, lines 44-50; bases: .
  Annotated fields: `id`.
- Class `TimestampMixin`, lines 53-65; bases: .
  Annotated fields: `created_at`, `updated_at`.
- Class `SoftDeleteMixin`, lines 68-91; bases: .
  Annotated fields: `deleted_at`.
- `SoftDeleteMixin.is_deleted` (sync), lines 82-83: No function docstring; consult the source body and layer walkthrough.
- `SoftDeleteMixin.soft_delete` (sync), lines 85-87: Mark this record as deleted.
  Calls: `datetime.now`.
- `SoftDeleteMixin.restore` (sync), lines 89-91: Undo a soft delete.
- Class `AuditMixin`, lines 94-96; bases: TimestampMixin, SoftDeleteMixin.

## app/models/coupon.py

61 lines; SHA-256 `edb8549e0081f1ee3fffd08ce72e27679d623c07df8e0e8d6e0d953cb0a50476`. [Open source](../../app/models/coupon.py).

Backend imports: `app.models.base`.

- Class `DiscountType`, lines 19-21; bases: str, enum.Enum.
- Class `Coupon`, lines 24-49; bases: Base.
  Annotated fields: `id`, `code`, `discount_type`, `discount_value`, `min_order_amount`, `max_uses`, `max_uses_per_customer`, `uses_count`, `valid_from`, `valid_until`, `is_active`, `created_at`, `usages`.
- Class `CouponUsage`, lines 52-61; bases: Base.
  Annotated fields: `id`, `coupon_id`, `user_id`, `order_id`, `used_at`, `coupon`.

## app/models/notification.py

50 lines; SHA-256 `ca9b9c13f03b1d400100aebc379182ed373629ab5da7aec421314e73abc8fe7e`. [Open source](../../app/models/notification.py).

Backend imports: `app.models.base`.

- Class `Notification`, lines 12-24; bases: Base.
  Annotated fields: `id`, `user_id`, `type`, `title`, `body`, `action_url`, `is_read`, `read_at`, `is_archived`, `created_at`.
- Class `NotificationPreference`, lines 27-37; bases: Base.
  Annotated fields: `user_id`, `order_updates_email`, `order_updates_push`, `promotions_email`, `payout_notifications`, `new_review_notifications`, `low_stock_alerts`, `updated_at`.
- Class `EmailLog`, lines 40-50; bases: Base.
  Annotated fields: `id`, `recipient_email`, `subject`, `template_id`, `status`, `resend_id`, `error_message`, `sent_at`.

## app/models/order.py

164 lines; SHA-256 `b3012d86a9aba3707d4788badcd5a36cd702f1217805973c205f495c651c3f66`. [Open source](../../app/models/order.py).

Backend imports: `app.models.base`, `app.models.coupon`, `app.models.product`, `app.models.seller`, `app.models.user`.

- Class `OrderStatus`, lines 25-34; bases: str, enum.Enum.
- Class `PaymentMethod`, lines 37-39; bases: str, enum.Enum.
- Class `SellerOrderStatus`, lines 42-48; bases: str, enum.Enum.
- Class `Order`, lines 51-89; bases: Base, TimestampMixin.
  Annotated fields: `id`, `user_id`, `order_number`, `status`, `guest_email`, `guest_name`, `guest_phone`, `subtotal`, `discount_amount`, `shipping_fee`, `total`, `payment_method`, `coupon_id`, `notes`, `user`, `address`, `items`, `seller_orders`, `coupon`.
- Class `OrderAddress`, lines 92-104; bases: Base.
  Annotated fields: `id`, `order_id`, `recipient_name`, `phone`, `street`, `city`, `province`, `note`, `order`.
- Class `OrderItem`, lines 107-127; bases: Base.
  Annotated fields: `id`, `order_id`, `seller_id`, `product_id`, `variant_id`, `product_name`, `variant_label`, `unit_price`, `quantity`, `subtotal`, `order`, `seller`, `product`, `variant`.
- Class `SellerOrder`, lines 130-151; bases: Base, TimestampMixin.
  Annotated fields: `id`, `order_id`, `seller_id`, `status`, `subtotal`, `tracking_number`, `courier_name`, `shipped_at`, `delivered_at`, `order`, `seller`.
- Class `OrderStatusHistory`, lines 154-164; bases: Base.
  Annotated fields: `id`, `order_id`, `seller_order_id`, `old_status`, `new_status`, `changed_by`, `note`, `created_at`.

## app/models/payment.py

112 lines; SHA-256 `380ed08a49ab8c9c29285c41e74b20d0ca9d341ff93691677b28a0152641561b`. [Open source](../../app/models/payment.py).

Backend imports: `app.models.base`, `app.models.order`.

- Class `PaymentStatus`, lines 30-35; bases: str, enum.Enum.
- Class `Payment`, lines 38-66; bases: Base.
  Annotated fields: `id`, `order_id`, `method`, `status`, `amount`, `currency`, `gateway_reference`, `gateway_payload`, `failure_reason`, `paid_at`, `created_at`, `order`, `callbacks`, `refunds`.
- Class `PaymentCallback`, lines 69-81; bases: Base.
  Annotated fields: `id`, `payment_id`, `gateway`, `raw_payload`, `is_verified`, `received_at`, `payment`.
- Class `Refund`, lines 84-108; bases: Base.
  Annotated fields: `id`, `payment_id`, `return_id`, `idempotency_key`, `amount`, `reason`, `gateway_ref`, `requested_by`, `processed_by`, `processed_at`, `created_at`, `payment`.

## app/models/product.py

185 lines; SHA-256 `7fd7b3e1a9027b77b6ae1294c5ac4c2b318a5cc933dd45b5dad2bee6c2716f92`. [Open source](../../app/models/product.py).

Backend imports: `app.models.base`, `app.models.seller`.

- Class `SizeType`, lines 31-34; bases: str, enum.Enum.
- Class `Category`, lines 37-55; bases: Base.
  Annotated fields: `id`, `parent_id`, `name`, `slug`, `image_url`, `sort_order`, `is_active`, `parent`, `children`, `products`.
- Class `Product`, lines 58-109; bases: Base, TimestampMixin, SoftDeleteMixin.
  Annotated fields: `id`, `seller_id`, `category_id`, `name`, `slug`, `description`, `price`, `sale_price`, `is_published`, `admin_hidden`, `meta_title`, `meta_description`, `avg_rating`, `review_count`, `view_count`, `seller`, `category`, `images`, `variants`, `tags`.
- `Product.effective_price` (sync), lines 100-101: No function docstring; consult the source body and layer walkthrough.
- `Product.has_stock` (sync), lines 104-109: No function docstring; consult the source body and layer walkthrough.
  Calls: `any`.
- Class `ProductImage`, lines 112-123; bases: Base.
  Annotated fields: `id`, `product_id`, `url`, `alt_text`, `sort_order`, `is_primary`, `created_at`, `product`.
- Class `ProductVariant`, lines 126-151; bases: Base.
  Annotated fields: `id`, `product_id`, `sku`, `size_type`, `size_value`, `colour`, `price_override`, `is_active`, `created_at`, `product`, `inventory`.
- `ProductVariant.effective_price` (sync), lines 150-151: No function docstring; consult the source body and layer walkthrough.
- Class `ProductInventory`, lines 154-174; bases: Base.
  Annotated fields: `id`, `variant_id`, `stock`, `reserved`, `updated_at`, `variant`.
- `ProductInventory.available_stock` (sync), lines 173-174: No function docstring; consult the source body and layer walkthrough.
- Class `Tag`, lines 177-185; bases: Base.
  Annotated fields: `id`, `name`, `products`.

## app/models/return_.py

91 lines; SHA-256 `a3359c936cc50b1acfb6d44d10b89d6829eac1ab8ad5bb8c43900b2a925dc7ea`. [Open source](../../app/models/return_.py).

Backend imports: `app.models.base`.

- Class `ReturnStatus`, lines 14-19; bases: str, enum.Enum.
- Class `DisputeStatus`, lines 22-27; bases: str, enum.Enum.
- Class `Return`, lines 30-47; bases: Base.
  Annotated fields: `id`, `order_id`, `seller_order_id`, `user_id`, `status`, `reason`, `notes`, `requested_at`, `resolved_at`, `items`, `dispute`.
- Class `ReturnItem`, lines 50-59; bases: Base.
  Annotated fields: `id`, `return_id`, `order_item_id`, `quantity`, `reason`, `return_`.
- Class `Dispute`, lines 62-79; bases: Base.
  Annotated fields: `id`, `return_id`, `seller_id`, `user_id`, `status`, `resolution_note`, `resolved_by`, `created_at`, `resolved_at`, `return_`, `messages`.
- Class `DisputeMessage`, lines 82-91; bases: Base.
  Annotated fields: `id`, `dispute_id`, `sender_id`, `body`, `created_at`, `dispute`.

## app/models/review.py

115 lines; SHA-256 `f4ad620ca33f6729fe48024adc237fcef8f201f4b577bbbbc4dcadb878ba90bc`. [Open source](../../app/models/review.py).

Backend imports: `app.models.base`, `app.models.order`, `app.models.product`, `app.models.user`.

- Class `ReviewStatus`, lines 41-45; bases: str, enum.Enum.
- Class `Review`, lines 48-92; bases: TimestampMixin, Base.
  Annotated fields: `id`, `user_id`, `product_id`, `order_id`, `rating`, `title`, `body`, `status`, `is_verified_purchase`, `helpful_count`, `unhelpful_count`, `admin_note`, `moderated_at`, `user`, `product`, `order`, `images`.
- Class `ReviewImage`, lines 95-108; bases: Base.
  Annotated fields: `id`, `review_id`, `url`, `sort_order`, `created_at`, `review`.
- Class `ReviewVote`, lines 111-115; bases: Base.
  Annotated fields: `review_id`, `user_id`, `helpful`.

## app/models/seller.py

129 lines; SHA-256 `02c95bd3cfc37d16e6b04e5729bd9356a887f0a9698ae90fc133567baeddfe60`. [Open source](../../app/models/seller.py).

Backend imports: `app.models.base`, `app.models.order`, `app.models.product`, `app.models.user`, `app.models.wallet`.

- Class `SellerStatus`, lines 20-25; bases: str, enum.Enum.
- Class `Seller`, lines 28-90; bases: Base, TimestampMixin, SoftDeleteMixin.
  Annotated fields: `id`, `user_id`, `brand_name`, `slug`, `description`, `logo_url`, `brand_color`, `return_policy`, `whatsapp_number`, `instagram_handle`, `status`, `total_slots`, `slots_used`, `registration_fee`, `registration_payment_reference`, `registration_paid_at`, `registration_paid_by`, `rejected_reason`, `approved_by`, `approved_at`, `user`, `wallet`, `bank_accounts`, `products`, `seller_orders`, `wallet_transactions`, `payouts`.
- `Seller.slots_available` (sync), lines 85-86: No function docstring; consult the source body and layer walkthrough.
- `Seller.is_active` (sync), lines 89-90: No function docstring; consult the source body and layer walkthrough.
- Class `SellerWallet`, lines 93-106; bases: Base.
  Annotated fields: `id`, `seller_id`, `available_balance`, `pending_balance`, `total_earned`, `total_commission`, `updated_at`, `seller`.
- Class `SellerBankAccount`, lines 109-124; bases: Base.
  Annotated fields: `id`, `seller_id`, `bank_name`, `account_title`, `account_number`, `is_default`, `created_at`, `seller`.

## app/models/user.py

112 lines; SHA-256 `4d4423c869b69c322bfed3856e89d6ca346eb14a3b044e02e02af7de42332ebb`. [Open source](../../app/models/user.py).

Backend imports: `app.models.base`, `app.models.order`, `app.models.seller`.

- Class `UserRole`, lines 27-30; bases: str, enum.Enum.
- Class `User`, lines 33-75; bases: UUIDPrimaryKeyMixin, AuditMixin, Base.
  Annotated fields: `auth_version`, `email`, `password_hash`, `role`, `first_name`, `last_name`, `phone`, `avatar_url`, `has_verified_email`, `google_id`, `totp_secret`, `is_2fa_enabled`, `last_login_at`, `sessions`, `addresses`, `seller`, `orders`.
- Class `UserSession`, lines 77-91; bases: UUIDPrimaryKeyMixin, Base.
  Annotated fields: `user_id`, `token_hash`, `ip_address`, `user_agent`, `expires_at`, `created_at`, `user`.
- Class `UserAddress`, lines 94-109; bases: UUIDPrimaryKeyMixin, Base.
  Annotated fields: `user_id`, `label`, `street`, `city`, `province`, `is_default`, `created_at`, `updated_at`, `user`.

## app/models/wallet.py

114 lines; SHA-256 `bba4e7b263485937003788ec82572c788beb4feb14af9093ec47bce0187ad9a0`. [Open source](../../app/models/wallet.py).

Backend imports: `app.models.base`, `app.models.order`, `app.models.seller`.

- Class `WalletTxType`, lines 21-27; bases: str, enum.Enum.
- Class `PayoutStatus`, lines 30-35; bases: str, enum.Enum.
- Class `CommissionLedger`, lines 38-62; bases: Base.
  Annotated fields: `id`, `seller_order_id`, `seller_id`, `gross_amount`, `commission_rate`, `commission_amount`, `seller_amount`, `released_at`, `settled_at`, `seller`, `seller_order`.
- Class `Payout`, lines 65-88; bases: Base.
  Annotated fields: `id`, `seller_id`, `amount`, `payment_method`, `payment_detail`, `status`, `admin_note`, `transfer_reference`, `approved_by`, `requested_at`, `completed_at`, `seller`.
- Class `WalletTransaction`, lines 91-111; bases: Base.
  Annotated fields: `id`, `seller_id`, `type`, `amount`, `balance_after`, `reference`, `seller_order_id`, `payout_id`, `note`, `created_at`, `seller`, `seller_order`, `payout`.



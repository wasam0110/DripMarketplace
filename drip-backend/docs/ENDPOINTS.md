# WearHowZ endpoint inventory

Generated from the application: 172 HTTP operations.

Dependency names show route-level access checks. Guest capability tokens, resource ownership, payment verification and business-state checks also run inside handlers/services; consult the OpenAPI schema and implementation.

| Method | Path | Access dependencies | Handler |
|---|---|---|---|
| GET | `/api/v1/admin/analytics/cities` | get_current_user_payload, require_admin | `app.api.v1.analytics.admin.orders_by_city` |
| GET | `/api/v1/admin/analytics/cohort` | get_current_user_payload, require_admin | `app.api.v1.analytics.admin.cohort_retention` |
| GET | `/api/v1/admin/analytics/conversion` | get_current_user_payload, require_admin | `app.api.v1.analytics.admin.conversion_funnel` |
| GET | `/api/v1/admin/analytics/payment-methods` | get_current_user_payload, require_admin | `app.api.v1.analytics.admin.payment_methods` |
| GET | `/api/v1/admin/analytics/platform` | get_current_user_payload, require_admin | `app.api.v1.analytics.admin.platform_analytics` |
| GET | `/api/v1/admin/analytics/revenue` | get_current_user_payload, require_admin | `app.api.v1.analytics.admin.platform_revenue` |
| GET | `/api/v1/admin/analytics/search-queries` | get_current_user_payload, require_admin | `app.api.v1.analytics.admin.search_queries` |
| GET | `/api/v1/admin/analytics/top-sellers` | get_current_user_payload, require_admin | `app.api.v1.analytics.admin.top_sellers` |
| GET | `/api/v1/admin/cod-queue` | get_current_user_payload, require_admin | `app.api.v1.admin.cod_queue.list_cod_queue` |
| POST | `/api/v1/admin/cod-queue/{order_id}/cancel` | get_current_user_payload, require_admin | `app.api.v1.admin.cod_queue.cancel_cod_order` |
| POST | `/api/v1/admin/cod-queue/{order_id}/verify` | get_current_user_payload, require_admin | `app.api.v1.admin.cod_queue.verify_cod_order` |
| GET | `/api/v1/admin/content/banners` | get_current_user_payload, require_admin | `app.api.v1.admin.content.list_banners` |
| POST | `/api/v1/admin/content/banners` | get_current_user_payload, require_admin | `app.api.v1.admin.content.create_banner` |
| DELETE | `/api/v1/admin/content/banners/{banner_id}` | get_current_user_payload, require_admin | `app.api.v1.admin.content.delete_banner` |
| PATCH | `/api/v1/admin/content/banners/{banner_id}` | get_current_user_payload, require_admin | `app.api.v1.admin.content.update_banner` |
| GET | `/api/v1/admin/dashboard` | get_current_user_payload, require_admin | `app.api.v1.admin.dashboard.admin_dashboard` |
| GET | `/api/v1/admin/disputes` | get_current_user_payload, require_admin | `app.api.v1.returns.admin_list_disputes` |
| POST | `/api/v1/admin/disputes/{dispute_id}/resolve` | get_current_user_payload, require_admin | `app.api.v1.returns.admin_resolve_dispute` |
| GET | `/api/v1/admin/inventory` | get_current_user_payload, require_admin | `app.api.v1.inventory.admin_list_inventory` |
| POST | `/api/v1/admin/inventory/bulk-update` | get_current_user_payload, require_admin | `app.api.v1.inventory.admin_bulk_update_inventory` |
| POST | `/api/v1/admin/notifications/broadcast` | get_current_user_payload, require_admin | `app.api.v1.notifications.broadcast_notification` |
| GET | `/api/v1/admin/notifications/email-log` | get_current_user_payload, require_admin | `app.api.v1.notifications.get_email_log` |
| GET | `/api/v1/admin/orders` | get_current_user_payload, require_admin | `app.api.v1.admin.orders.list_all_orders` |
| GET | `/api/v1/admin/payouts` | get_current_user_payload, require_admin | `app.api.v1.admin.payouts.list_all_payouts` |
| POST | `/api/v1/admin/payouts/{payout_id}/approve` | get_current_user_payload, require_admin | `app.api.v1.admin.payouts.approve_payout` |
| POST | `/api/v1/admin/payouts/{payout_id}/complete` | get_current_user_payload, require_admin | `app.api.v1.admin.payouts.complete_payout` |
| POST | `/api/v1/admin/payouts/{payout_id}/reject` | get_current_user_payload, require_admin | `app.api.v1.admin.payouts.reject_payout` |
| GET | `/api/v1/admin/products` | get_current_user_payload, require_admin | `app.api.v1.products.admin_list_products` |
| POST | `/api/v1/admin/products/{product_id}/hide` | get_current_user_payload, require_admin | `app.api.v1.products.admin_hide_product` |
| POST | `/api/v1/admin/products/{product_id}/unhide` | get_current_user_payload, require_admin | `app.api.v1.products.unhide_product` |
| GET | `/api/v1/admin/returns` | get_current_user_payload, require_admin | `app.api.v1.returns.admin_list_returns` |
| POST | `/api/v1/admin/returns/{return_id}/approve` | get_current_user_payload, require_admin | `app.api.v1.returns.admin_approve_return` |
| POST | `/api/v1/admin/returns/{return_id}/received` | get_current_user_payload, require_admin | `app.api.v1.returns.admin_mark_received` |
| POST | `/api/v1/admin/returns/{return_id}/refund` | get_current_user_payload, require_admin | `app.api.v1.returns.admin_process_refund` |
| POST | `/api/v1/admin/returns/{return_id}/reject` | get_current_user_payload, require_admin | `app.api.v1.returns.admin_reject_return` |
| GET | `/api/v1/admin/reviews` | get_current_user_payload, require_admin | `app.api.v1.admin.reviews.list_reviews` |
| PATCH | `/api/v1/admin/reviews/{review_id}` | get_current_user_payload, require_admin | `app.api.v1.admin.reviews.moderate_review` |
| GET | `/api/v1/admin/sellers` | get_current_user_payload, require_admin | `app.api.v1.admin.brands.list_sellers` |
| GET | `/api/v1/admin/sellers/{seller_id}` | get_current_user_payload, require_admin | `app.api.v1.admin.brands.get_seller` |
| POST | `/api/v1/admin/sellers/{seller_id}/approve` | get_current_user_payload, require_admin | `app.api.v1.admin.brands.approve_seller` |
| POST | `/api/v1/admin/sellers/{seller_id}/registration-payment` | get_current_user_payload, require_admin | `app.api.v1.admin.brands.record_registration_payment` |
| POST | `/api/v1/admin/sellers/{seller_id}/reinstate` | get_current_user_payload, require_admin | `app.api.v1.admin.brands.reinstate_seller` |
| POST | `/api/v1/admin/sellers/{seller_id}/reject` | get_current_user_payload, require_admin | `app.api.v1.admin.brands.reject_seller` |
| POST | `/api/v1/admin/sellers/{seller_id}/suspend` | get_current_user_payload, require_admin | `app.api.v1.admin.brands.suspend_seller` |
| GET | `/api/v1/admin/settings` | get_current_user_payload, require_admin | `app.api.v1.admin.settings.get_settings` |
| PATCH | `/api/v1/admin/settings` | get_current_user_payload, require_admin | `app.api.v1.admin.settings.update_settings` |
| GET | `/api/v1/admin/wallet/overview` | get_current_user_payload, require_admin | `app.api.v1.wallet.admin_wallet_overview` |
| GET | `/api/v1/admin/wallet/payouts` | get_current_user_payload, require_admin | `app.api.v1.wallet.admin_list_payouts` |
| POST | `/api/v1/admin/wallet/payouts/{payout_id}/approve` | get_current_user_payload, require_admin | `app.api.v1.wallet.admin_approve_payout` |
| POST | `/api/v1/admin/wallet/payouts/{payout_id}/complete` | get_current_user_payload, require_admin | `app.api.v1.wallet.admin_complete_payout` |
| POST | `/api/v1/admin/wallet/payouts/{payout_id}/reject` | get_current_user_payload, require_admin | `app.api.v1.wallet.admin_reject_payout` |
| POST | `/api/v1/auth/change-password` | get_current_user_payload, require_customer | `app.api.v1.auth.change_password` |
| POST | `/api/v1/auth/forgot-password` | Public / handler checks | `app.api.v1.auth.forgot_password` |
| GET | `/api/v1/auth/google` | Public / handler checks | `app.api.v1.auth.google_login` |
| GET | `/api/v1/auth/google/callback` | Public / handler checks | `app.api.v1.auth.google_callback` |
| POST | `/api/v1/auth/login` | Public / handler checks | `app.api.v1.auth.login` |
| POST | `/api/v1/auth/logout` | get_current_user_payload | `app.api.v1.auth.logout` |
| GET | `/api/v1/auth/me` | get_current_user_payload, require_customer | `app.api.v1.auth.get_me` |
| POST | `/api/v1/auth/refresh` | Public / handler checks | `app.api.v1.auth.refresh` |
| POST | `/api/v1/auth/register` | Public / handler checks | `app.api.v1.auth.register` |
| POST | `/api/v1/auth/resend-verification` | Public / handler checks | `app.api.v1.auth.resend_verification` |
| POST | `/api/v1/auth/reset-password` | Public / handler checks | `app.api.v1.auth.reset_password` |
| POST | `/api/v1/auth/setup-2fa` | get_current_user_payload, require_customer | `app.api.v1.auth.setup_2fa` |
| POST | `/api/v1/auth/setup-2fa/verify` | get_current_user_payload, require_customer | `app.api.v1.auth.verify_2fa_setup` |
| GET | `/api/v1/auth/verify-email` | Public / handler checks | `app.api.v1.auth.verify_email` |
| GET | `/api/v1/brands` | Public / handler checks | `app.api.v1.storefront.brands` |
| GET | `/api/v1/brands/{slug}` | Public / handler checks | `app.api.v1.storefront.brand_detail` |
| GET | `/api/v1/brands/{slug}/products` | Public / handler checks | `app.api.v1.storefront.brand_products` |
| GET | `/api/v1/cart` | get_current_user_payload, require_customer | `app.api.v1.cart.get_cart` |
| POST | `/api/v1/cart` | get_current_user_payload, require_customer | `app.api.v1.cart.add_to_cart` |
| POST | `/api/v1/cart/clear` | get_current_user_payload, require_customer | `app.api.v1.cart.clear_cart` |
| POST | `/api/v1/cart/sync` | get_current_user_payload, require_customer | `app.api.v1.cart.sync_cart` |
| DELETE | `/api/v1/cart/{variant_id}` | get_current_user_payload, require_customer | `app.api.v1.cart.remove_cart_item` |
| PATCH | `/api/v1/cart/{variant_id}` | get_current_user_payload, require_customer | `app.api.v1.cart.update_cart_item` |
| GET | `/api/v1/categories` | Public / handler checks | `app.api.v1.storefront.categories` |
| GET | `/api/v1/content/banners` | Public / handler checks | `app.api.v1.storefront.public_banners` |
| POST | `/api/v1/coupons/validate` | get_current_user_payload, require_customer | `app.api.v1.orders.validate_coupon` |
| DELETE | `/api/v1/customers/me` | get_current_user_payload, require_customer | `app.api.v1.customers.delete_account` |
| GET | `/api/v1/customers/me` | get_current_user_payload, require_customer | `app.api.v1.customers.get_profile` |
| PATCH | `/api/v1/customers/me` | get_current_user_payload, require_customer | `app.api.v1.customers.update_profile` |
| GET | `/api/v1/customers/me/addresses` | get_current_user_payload, require_customer | `app.api.v1.customers.list_addresses` |
| POST | `/api/v1/customers/me/addresses` | get_current_user_payload, require_customer | `app.api.v1.customers.create_address` |
| DELETE | `/api/v1/customers/me/addresses/{address_id}` | get_current_user_payload, require_customer | `app.api.v1.customers.delete_address` |
| PATCH | `/api/v1/customers/me/addresses/{address_id}` | get_current_user_payload, require_customer | `app.api.v1.customers.update_address` |
| POST | `/api/v1/customers/me/addresses/{address_id}/set-default` | get_current_user_payload, require_customer | `app.api.v1.customers.set_default_address` |
| POST | `/api/v1/customers/me/avatar` | get_current_user_payload, require_customer | `app.api.v1.customers.upload_avatar` |
| POST | `/api/v1/customers/me/change-password` | get_current_user_payload, require_customer | `app.api.v1.customers.change_password` |
| GET | `/api/v1/customers/me/notification-preferences` | get_current_user_payload, require_customer | `app.api.v1.customers.get_notification_preferences` |
| PATCH | `/api/v1/customers/me/notification-preferences` | get_current_user_payload, require_customer | `app.api.v1.customers.update_notification_preferences` |
| GET | `/api/v1/customers/me/reviews` | get_current_user_payload, require_customer | `app.api.v1.customers.list_my_reviews` |
| POST | `/api/v1/customers/me/reviews` | get_current_user_payload, require_customer | `app.api.v1.customers.create_review` |
| DELETE | `/api/v1/customers/me/reviews/{review_id}` | get_current_user_payload, require_customer | `app.api.v1.customers.delete_review` |
| PATCH | `/api/v1/customers/me/reviews/{review_id}` | get_current_user_payload, require_customer | `app.api.v1.customers.update_review` |
| GET | `/api/v1/customers/me/wishlist` | get_current_user_payload, require_customer | `app.api.v1.customers.get_wishlist` |
| POST | `/api/v1/customers/me/wishlist` | get_current_user_payload, require_customer | `app.api.v1.customers.add_to_wishlist` |
| DELETE | `/api/v1/customers/me/wishlist/{product_id}` | get_current_user_payload, require_customer | `app.api.v1.customers.remove_from_wishlist` |
| GET | `/api/v1/customers/reviews/product/{product_id}` | Public / handler checks | `app.api.v1.customers.list_product_reviews` |
| POST | `/api/v1/customers/reviews/{review_id}/helpful` | get_current_user_payload, require_customer | `app.api.v1.customers.mark_review_helpful` |
| GET | `/api/v1/health` | Public / handler checks | `app.api.v1.health.health_check` |
| GET | `/api/v1/notifications` | get_current_user_payload, require_customer | `app.api.v1.notifications.list_notifications` |
| GET | `/api/v1/notifications/preferences` | get_current_user_payload, require_customer | `app.api.v1.notifications.get_preferences` |
| PATCH | `/api/v1/notifications/preferences` | get_current_user_payload, require_customer | `app.api.v1.notifications.update_preferences` |
| POST | `/api/v1/notifications/read-all` | get_current_user_payload, require_customer | `app.api.v1.notifications.mark_all_read` |
| POST | `/api/v1/notifications/{notification_id}/read` | get_current_user_payload, require_customer | `app.api.v1.notifications.mark_notification_read` |
| GET | `/api/v1/orders` | get_current_user_payload, require_customer | `app.api.v1.orders.list_orders` |
| POST | `/api/v1/orders` | get_current_user_payload, require_customer | `app.api.v1.orders.place_order` |
| POST | `/api/v1/orders/guest` | Public / handler checks | `app.api.v1.orders.place_guest_order` |
| GET | `/api/v1/orders/number/{order_number}` | get_optional_user_payload | `app.api.v1.orders.get_order_by_number` |
| GET | `/api/v1/orders/{order_id}` | get_optional_user_payload | `app.api.v1.orders.get_order` |
| POST | `/api/v1/orders/{order_id}/cancel` | get_current_user_payload, require_customer | `app.api.v1.orders.cancel_order` |
| GET | `/api/v1/payments` | get_current_user_payload, require_admin | `app.api.v1.payments.list_payments` |
| POST | `/api/v1/payments/callback/payfast` | Public / handler checks | `app.api.v1.payments.payfast_callback` |
| GET | `/api/v1/payments/gateway-status` | get_current_user_payload, require_admin | `app.api.v1.payments.gateway_status` |
| POST | `/api/v1/payments/initiate` | get_optional_user_payload | `app.api.v1.payments.initiate_payment` |
| POST | `/api/v1/payments/refunds/{refund_id}/confirm` | get_current_user_payload, require_admin | `app.api.v1.payments.confirm_refund` |
| POST | `/api/v1/payments/{order_id}/retry` | get_optional_user_payload | `app.api.v1.payments.retry_payment` |
| GET | `/api/v1/payments/{order_id}/status` | get_optional_user_payload | `app.api.v1.payments.get_payment_status` |
| POST | `/api/v1/payments/{payment_id}/cod-collection` | get_current_user_payload, require_admin | `app.api.v1.payments.record_cod_collection` |
| POST | `/api/v1/payments/{payment_id}/refund` | get_current_user_payload, require_admin | `app.api.v1.payments.refund_payment` |
| GET | `/api/v1/products` | Public / handler checks | `app.api.v1.products.list_products` |
| GET | `/api/v1/products/search/suggestions` | Public / handler checks | `app.api.v1.products.search_suggestions` |
| GET | `/api/v1/products/slug/{slug}` | Public / handler checks | `app.api.v1.products.get_product_by_slug` |
| GET | `/api/v1/products/{product_id}` | Public / handler checks | `app.api.v1.products.get_product` |
| GET | `/api/v1/products/{product_id}/reviews` | Public / handler checks | `app.api.v1.products.get_product_reviews` |
| POST | `/api/v1/products/{product_id}/reviews` | get_current_user_payload, require_customer | `app.api.v1.products.submit_review` |
| GET | `/api/v1/products/{product_id}/variants` | Public / handler checks | `app.api.v1.products.get_product_variants` |
| GET | `/api/v1/returns` | get_current_user_payload, require_customer | `app.api.v1.returns.list_returns` |
| POST | `/api/v1/returns` | get_current_user_payload, require_customer | `app.api.v1.returns.request_return` |
| GET | `/api/v1/returns/{return_id}` | get_current_user_payload, require_customer | `app.api.v1.returns.get_return` |
| GET | `/api/v1/returns/{return_id}/dispute` | get_current_user_payload, require_customer | `app.api.v1.returns.get_dispute` |
| POST | `/api/v1/returns/{return_id}/dispute` | get_current_user_payload, require_customer | `app.api.v1.returns.open_dispute` |
| POST | `/api/v1/returns/{return_id}/dispute/messages` | get_current_user_payload, require_customer | `app.api.v1.returns.add_dispute_message` |
| GET | `/api/v1/seller/analytics/inventory-health` | get_current_user_payload, require_seller | `app.api.v1.analytics.seller.seller_inventory_health` |
| GET | `/api/v1/seller/analytics/overview` | get_current_user_payload, require_seller | `app.api.v1.analytics.seller.seller_overview` |
| GET | `/api/v1/seller/analytics/revenue` | get_current_user_payload, require_seller | `app.api.v1.analytics.seller.seller_revenue_series` |
| GET | `/api/v1/seller/analytics/top-products` | get_current_user_payload, require_seller | `app.api.v1.analytics.seller.seller_top_products` |
| GET | `/api/v1/seller/bank-accounts` | get_current_user_payload, require_customer | `app.api.v1.sellers.list_bank_accounts` |
| POST | `/api/v1/seller/bank-accounts` | get_current_user_payload, require_customer | `app.api.v1.sellers.add_bank_account` |
| DELETE | `/api/v1/seller/bank-accounts/{account_id}` | get_current_user_payload, require_customer | `app.api.v1.sellers.delete_bank_account` |
| GET | `/api/v1/seller/dashboard` | get_current_user_payload, require_customer | `app.api.v1.sellers.get_dashboard` |
| GET | `/api/v1/seller/inventory` | get_current_user_payload, require_seller | `app.api.v1.inventory.list_seller_inventory` |
| GET | `/api/v1/seller/inventory/low-stock` | get_current_user_payload, require_seller | `app.api.v1.inventory.get_low_stock_alerts` |
| GET | `/api/v1/seller/inventory/{variant_id}` | get_current_user_payload, require_seller | `app.api.v1.inventory.get_variant_stock` |
| PUT | `/api/v1/seller/inventory/{variant_id}` | get_current_user_payload, require_seller | `app.api.v1.inventory.set_variant_stock` |
| POST | `/api/v1/seller/inventory/{variant_id}/adjust` | get_current_user_payload, require_seller | `app.api.v1.inventory.adjust_variant_stock` |
| POST | `/api/v1/seller/logo` | get_current_user_payload, require_customer | `app.api.v1.sellers.upload_logo` |
| GET | `/api/v1/seller/me` | get_current_user_payload, require_customer | `app.api.v1.sellers.get_seller_profile` |
| PATCH | `/api/v1/seller/me` | get_current_user_payload, require_customer | `app.api.v1.sellers.update_seller_profile` |
| GET | `/api/v1/seller/orders` | get_current_user_payload, require_seller | `app.api.v1.orders.list_seller_orders` |
| GET | `/api/v1/seller/orders/{seller_order_id}` | get_current_user_payload, require_seller | `app.api.v1.orders.get_seller_order` |
| PUT | `/api/v1/seller/orders/{seller_order_id}/status` | get_current_user_payload, require_seller | `app.api.v1.orders.update_seller_order_status` |
| GET | `/api/v1/seller/products` | get_current_user_payload, require_seller | `app.api.v1.products.list_seller_products` |
| POST | `/api/v1/seller/products` | get_current_user_payload, require_seller | `app.api.v1.products.create_product` |
| DELETE | `/api/v1/seller/products/{product_id}` | get_current_user_payload, require_seller | `app.api.v1.products.delete_product` |
| GET | `/api/v1/seller/products/{product_id}` | get_current_user_payload, require_seller | `app.api.v1.products.seller_product_detail` |
| PUT | `/api/v1/seller/products/{product_id}` | get_current_user_payload, require_seller | `app.api.v1.products.update_product` |
| POST | `/api/v1/seller/products/{product_id}/images` | get_current_user_payload, require_seller | `app.api.v1.products.upload_product_images` |
| PUT | `/api/v1/seller/products/{product_id}/images/order` | get_current_user_payload, require_seller | `app.api.v1.products.reorder_images` |
| DELETE | `/api/v1/seller/products/{product_id}/images/{image_id}` | get_current_user_payload, require_seller | `app.api.v1.products.delete_image` |
| PUT | `/api/v1/seller/products/{product_id}/images/{image_id}/primary` | get_current_user_payload, require_seller | `app.api.v1.products.primary_image` |
| POST | `/api/v1/seller/products/{product_id}/publish` | get_current_user_payload, require_seller | `app.api.v1.products.publish_product` |
| POST | `/api/v1/seller/products/{product_id}/unpublish` | get_current_user_payload, require_seller | `app.api.v1.products.unpublish_product` |
| POST | `/api/v1/seller/products/{product_id}/variants` | get_current_user_payload, require_seller | `app.api.v1.products.add_variant` |
| PATCH | `/api/v1/seller/products/{product_id}/variants/{variant_id}` | get_current_user_payload, require_seller | `app.api.v1.products.update_variant` |
| POST | `/api/v1/seller/register` | Public / handler checks | `app.api.v1.sellers.register_seller` |
| GET | `/api/v1/seller/register/slot-price` | Public / handler checks | `app.api.v1.sellers.get_slot_pricing` |
| POST | `/api/v1/seller/slots/purchase` | get_current_user_payload, require_customer | `app.api.v1.sellers.purchase_slots` |
| GET | `/api/v1/seller/wallet` | get_current_user_payload, require_seller | `app.api.v1.wallet.get_wallet_summary` |
| GET | `/api/v1/seller/wallet/commission-breakdown` | get_current_user_payload, require_seller | `app.api.v1.wallet.get_commission_breakdown` |
| GET | `/api/v1/seller/wallet/payouts` | get_current_user_payload, require_seller | `app.api.v1.wallet.get_payout_history` |
| GET | `/api/v1/seller/wallet/transactions` | get_current_user_payload, require_seller | `app.api.v1.wallet.get_wallet_transactions` |
| POST | `/api/v1/seller/wallet/withdraw` | get_current_user_payload, require_seller | `app.api.v1.wallet.request_withdrawal` |

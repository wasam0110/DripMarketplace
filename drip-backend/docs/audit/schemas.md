# Backend source index: schemas

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## app/schemas/admin.py

170 lines; SHA-256 `079106efb4d82db39aab73be58c0f6a2730edb64388adbc626f711242f96a133`. [Open source](../../app/schemas/admin.py).

- Class `AdminDashboardResponse`, lines 13-24; bases: BaseModel.
  Annotated fields: `period`, `total_gmv`, `platform_revenue`, `slot_revenue`, `total_revenue`, `total_orders`, `active_sellers`, `pending_sellers`, `cod_unverified`, `pending_payouts`, `new_customers`.
- Class `AdminSellerRowResponse`, lines 29-41; bases: BaseModel.
  Annotated fields: `id`, `brand_name`, `status`, `slots_used`, `total_slots`, `product_count`, `total_gmv`, `platform_cut`, `available_balance`, `joined_at`.
- Class `AdminSellerDetailResponse`, lines 44-53; bases: AdminSellerRowResponse.
  Annotated fields: `slug`, `description`, `whatsapp_number`, `instagram_handle`, `logo_url`, `return_policy`, `pending_balance`, `registration_fee`, `rejected_reason`.
- Class `RejectSellerRequest`, lines 56-57; bases: BaseModel.
  Annotated fields: `reason`.
- Class `SuspendSellerRequest`, lines 60-61; bases: BaseModel.
  Annotated fields: `reason`.
- Class `PaginatedAdminSellers`, lines 64-69; bases: BaseModel.
  Annotated fields: `data`, `total`, `page`, `per_page`, `total_pages`.
- Class `AdminOrderRowResponse`, lines 74-86; bases: BaseModel.
  Annotated fields: `id`, `order_number`, `status`, `customer_name`, `seller_count`, `subtotal`, `total`, `commission`, `payment_method`, `created_at`.
- Class `OrderTotals`, lines 89-92; bases: BaseModel.
  Annotated fields: `total_gmv`, `total_commission`, `order_count`.
- Class `PaginatedAdminOrders`, lines 95-99; bases: BaseModel.
  Annotated fields: `data`, `totals`, `total`, `page`.
- Class `CODQueueItem`, lines 104-113; bases: BaseModel.
  Annotated fields: `order_id`, `order_number`, `customer_name`, `customer_phone`, `total`, `brand_names`, `placed_at`, `expires_at`, `minutes_remaining`.
- Class `CODVerifyRequest`, lines 116-117; bases: BaseModel.
  Annotated fields: `note`.
- Class `BannerResponse`, lines 122-134; bases: BaseModel.
  Annotated fields: `id`, `title`, `image_url`, `link_url`, `position`, `sort_order`, `is_active`, `valid_from`, `valid_until`, `created_at`.
- Class `UpdateSettingsRequest`, lines 139-146; bases: BaseModel.
  Annotated fields: `commission_rate`, `registration_fee`, `extra_slot_price`, `free_shipping_threshold`, `standard_shipping_fee`, `cod_timeout_minutes`, `wallet_hold_days`.
- Class `PlatformSettingsResponse`, lines 149-156; bases: BaseModel.
  Annotated fields: `commission_rate`, `registration_fee`, `extra_slot_price`, `free_shipping_threshold`, `standard_shipping_fee`, `cod_timeout_minutes`, `wallet_hold_days`.
- Class `UpdateBannerRequest`, lines 158-165; bases: BaseModel.
  Annotated fields: `title`, `link_url`, `position`, `sort_order`, `is_active`, `valid_from`, `valid_until`.
- Class `SellerRegistrationPaymentRequest`, lines 168-170; bases: BaseModel.
  Annotated fields: `amount`, `reference`.

## app/schemas/analytics.py

146 lines; SHA-256 `db9714abfaf4d3059a52a56168252c656562ab820f6a240a37077f84f5fb36de`. [Open source](../../app/schemas/analytics.py).

- Class `SellerAnalyticsOverview`, lines 9-18; bases: BaseModel.
  Annotated fields: `period`, `gross_revenue`, `commission_paid`, `net_earnings`, `order_count`, `units_sold`, `avg_order_value`, `total_views`, `conversion_rate`.
- Class `RevenueDayRow`, lines 21-26; bases: BaseModel.
  Annotated fields: `date`, `gross`, `commission`, `net`, `orders`.
- Class `RevenueSeriesResponse`, lines 29-32; bases: BaseModel.
  Annotated fields: `period`, `granularity`, `data`.
- Class `TopProductRow`, lines 35-42; bases: BaseModel.
  Annotated fields: `product_id`, `product_name`, `image_url`, `revenue`, `units_sold`, `views`, `avg_rating`.
- Class `TopProductsResponse`, lines 45-48; bases: BaseModel.
  Annotated fields: `period`, `sort_by`, `data`.
- Class `InventoryHealthResponse`, lines 51-56; bases: BaseModel.
  Annotated fields: `total_variants`, `in_stock`, `low_stock`, `out_of_stock`, `total_units`.
- Class `PlatformAnalytics`, lines 61-71; bases: BaseModel.
  Annotated fields: `period`, `total_gmv`, `commission_revenue`, `slot_revenue`, `total_orders`, `new_customers`, `active_sellers`, `avg_order_value`, `cod_rate`, `cancellation_rate`.
- Class `TopSellerRow`, lines 74-80; bases: BaseModel.
  Annotated fields: `seller_id`, `brand_name`, `logo_url`, `gmv`, `commission`, `order_count`.
- Class `TopSellersResponse`, lines 83-85; bases: BaseModel.
  Annotated fields: `period`, `data`.
- Class `CohortRow`, lines 88-91; bases: BaseModel.
  Annotated fields: `cohort_month`, `cohort_size`, `retention`.
- Class `CohortResponse`, lines 94-96; bases: BaseModel.
  Annotated fields: `months`, `data`.
- Class `PaymentMethodStat`, lines 99-104; bases: BaseModel.
  Annotated fields: `count`, `total`, `share`, `verified_rate`, `cancellation_rate`.
- Class `PaymentMethodsResponse`, lines 107-110; bases: BaseModel.
  Annotated fields: `period`, `payfast`, `cod`.
- Class `CityRow`, lines 113-117; bases: BaseModel.
  Annotated fields: `city`, `order_count`, `total_gmv`, `share`.
- Class `CitiesResponse`, lines 120-122; bases: BaseModel.
  Annotated fields: `period`, `data`.
- Class `ConversionResponse`, lines 125-134; bases: BaseModel.
  Annotated fields: `measurement`, `tracked_since`, `period`, `product_views`, `add_to_cart`, `orders_completed`, `view_to_cart_rate`, `cart_to_order_rate`, `overall_cvr`.
- Class `SearchQueryRow`, lines 137-140; bases: BaseModel.
  Annotated fields: `query`, `count`, `no_result_rate`.
- Class `SearchQueriesResponse`, lines 143-146; bases: BaseModel.
  Annotated fields: `tracked_since`, `period`, `data`.

## app/schemas/auth.py

202 lines; SHA-256 `73d09c5a7c4676decaba854f0493d609e20312962da183d735204169ce7aeedd`. [Open source](../../app/schemas/auth.py).

Backend imports: `app.schemas.common`.

- Class `RegisterRequest`, lines 24-80; bases: DRIPBaseModel.
  Annotated fields: `first_name`, `last_name`, `email`, `password`, `phone`.
- `RegisterRequest.normalise_email` (sync), lines 33-42: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `any`, `field_validator`, `len`, `re.match`, `v.endswith`, `v.strip`, `v.strip().lower`.
- `RegisterRequest.validate_password` (sync), lines 46-57: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `_PWD_DIGIT.search`, `_PWD_LOWER.search`, `_PWD_UPPER.search`, `field_validator`, `len`.
- `RegisterRequest.validate_name` (sync), lines 61-67: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `len`, `v.strip`.
- `RegisterRequest.normalise_phone` (sync), lines 71-80: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `_PHONE.match`, `clean.startswith`, `field_validator`, `re.sub`.
- Class `LoginRequest`, lines 83-91; bases: DRIPBaseModel.
  Annotated fields: `email`, `password`, `totp_code`.
- `LoginRequest.normalise_email` (sync), lines 90-91: No function docstring; consult the source body and layer walkthrough.
  Calls: `field_validator`, `v.strip`, `v.strip().lower`.
- Class `RefreshRequest`, lines 94-97; bases: DRIPBaseModel.
- Class `ForgotPasswordRequest`, lines 100-106; bases: DRIPBaseModel.
  Annotated fields: `email`.
- `ForgotPasswordRequest.normalise_email` (sync), lines 105-106: No function docstring; consult the source body and layer walkthrough.
  Calls: `field_validator`, `v.strip`, `v.strip().lower`.
- Class `ResetPasswordRequest`, lines 109-126; bases: DRIPBaseModel.
  Annotated fields: `token`, `new_password`.
- `ResetPasswordRequest.validate_password` (sync), lines 115-126: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `_PWD_DIGIT.search`, `_PWD_LOWER.search`, `_PWD_UPPER.search`, `field_validator`, `len`.
- Class `ChangePasswordRequest`, lines 129-152; bases: DRIPBaseModel.
  Annotated fields: `current_password`, `new_password`.
- `ChangePasswordRequest.validate_new` (sync), lines 135-146: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `_PWD_DIGIT.search`, `_PWD_LOWER.search`, `_PWD_UPPER.search`, `field_validator`, `len`.
- `ChangePasswordRequest.passwords_differ` (sync), lines 149-152: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `model_validator`.
- Class `VerifyTOTPRequest`, lines 155-164; bases: DRIPBaseModel.
  Annotated fields: `code`.
- `VerifyTOTPRequest.validate_code` (sync), lines 160-164: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `re.match`, `v.strip`.
- Class `UserResponse`, lines 169-180; bases: DRIPResponseModel.
  Annotated fields: `id`, `email`, `role`, `first_name`, `last_name`, `phone`, `avatar_url`, `has_verified_email`, `is_2fa_enabled`, `seller_id`, `created_at`.
- Class `AuthResponse`, lines 183-186; bases: DRIPResponseModel.
  Annotated fields: `access_token`, `token_type`, `user`.
- Class `TokenResponse`, lines 189-191; bases: DRIPResponseModel.
  Annotated fields: `access_token`, `token_type`.
- Class `TOTPSetupResponse`, lines 194-197; bases: DRIPResponseModel.
  Annotated fields: `secret`, `qr_uri`, `message`.
- Class `MessageResponse`, lines 200-202; bases: DRIPResponseModel.
  Annotated fields: `message`, `success`.

## app/schemas/common.py

197 lines; SHA-256 `22dc53d6521dcc4b9ddaa8f752e32416131f0152ad61bade8b0f3874a4ccdbae`. [Open source](../../app/schemas/common.py).

- Class `DRIPBaseModel`, lines 32-43; bases: BaseModel.
- Class `DRIPResponseModel`, lines 46-56; bases: BaseModel.
- Class `CursorPagination`, lines 61-65; bases: DRIPResponseModel.
  Annotated fields: `next_cursor`, `has_next`, `limit`.
- Class `PagePagination`, lines 68-81; bases: DRIPResponseModel.
  Annotated fields: `page`, `per_page`, `total`, `total_pages`.
- `PagePagination.has_next` (sync), lines 76-77: No function docstring; consult the source body and layer walkthrough.
- `PagePagination.has_prev` (sync), lines 80-81: No function docstring; consult the source body and layer walkthrough.
- Class `PaginatedResponse`, lines 84-87; bases: DRIPResponseModel, Generic[T].
  Annotated fields: `data`, `pagination`.
- Class `ErrorDetail`, lines 92-96; bases: DRIPResponseModel.
  Annotated fields: `code`, `message`, `fields`, `request_id`.
- Class `ErrorResponse`, lines 99-100; bases: DRIPResponseModel.
  Annotated fields: `error`.
- Class `MessageResponse`, lines 103-106; bases: DRIPResponseModel.
  Annotated fields: `message`, `success`.
- `validate_phone` (sync), lines 123-138: Normalise a Pakistani phone number to international format 923XXXXXXXXX.
  Calls: `ValueError`, `_PHONE_PATTERN.match`, `clean.startswith`, `re.sub`.
- Class `PKRAmount`, lines 143-162; bases: int.
- `PKRAmount.__get_validators__` (sync), lines 150-151: No function docstring; consult the source body and layer walkthrough.
- `PKRAmount.validate` (sync), lines 154-162: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `cls`, `int`, `isinstance`.
- Class `PaginationParams`, lines 167-174; bases: DRIPBaseModel.
  Annotated fields: `page`, `per_page`.
- `PaginationParams.offset` (sync), lines 173-174: No function docstring; consult the source body and layer walkthrough.
- Class `DateRangeParams`, lines 177-187; bases: DRIPBaseModel.
  Annotated fields: `date_from`, `date_to`.
- `DateRangeParams.validate_range` (sync), lines 183-187: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `model_validator`.
- Class `HealthResponse`, lines 192-197; bases: DRIPResponseModel.
  Annotated fields: `status`, `database`, `redis`, `version`, `environment`.

## app/schemas/notification.py

75 lines; SHA-256 `08f0c01fcfda875116f82815eeb14e276471291d6f156e5336b4efc09853c968`. [Open source](../../app/schemas/notification.py).

- Class `NotificationResponse`, lines 10-19; bases: BaseModel.
  Annotated fields: `id`, `type`, `title`, `body`, `action_url`, `is_read`, `created_at`.
- Class `NotificationListResponse`, lines 22-26; bases: BaseModel.
  Annotated fields: `data`, `unread_count`, `total`, `page`.
- Class `NotificationPreferencesResponse`, lines 29-37; bases: BaseModel.
  Annotated fields: `order_updates_email`, `order_updates_push`, `promotions_email`, `payout_notifications`, `new_review_notifications`, `low_stock_alerts`.
- Class `UpdatePreferencesRequest`, lines 40-46; bases: BaseModel.
  Annotated fields: `order_updates_email`, `order_updates_push`, `promotions_email`, `payout_notifications`, `new_review_notifications`, `low_stock_alerts`.
- Class `BroadcastRequest`, lines 49-53; bases: BaseModel.
  Annotated fields: `title`, `body`, `audience`, `action_url`.
- Class `BroadcastResponse`, lines 56-58; bases: BaseModel.
  Annotated fields: `recipient_count`, `task_id`.
- Class `EmailLogResponse`, lines 61-71; bases: BaseModel.
  Annotated fields: `id`, `recipient_email`, `subject`, `template_id`, `status`, `resend_id`, `error_message`, `sent_at`.
- Class `MarkReadResponse`, lines 74-75; bases: BaseModel.
  Annotated fields: `updated_count`.

## app/schemas/order.py

271 lines; SHA-256 `bdaf9507eb3fd9232bc86549b015467701cfe7340122e8c9a6ab2a79de8d86ca`. [Open source](../../app/schemas/order.py).

Backend imports: `app.models.order`.

- Class `ShippingAddressInput`, lines 15-28; bases: BaseModel.
  Annotated fields: `recipient_name`, `phone`, `street`, `city`, `province`, `note`.
- `ShippingAddressInput.validate_phone` (sync), lines 25-28: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `re.match`.
- Class `ShippingAddressResponse`, lines 31-39; bases: BaseModel.
  Annotated fields: `recipient_name`, `phone`, `street`, `city`, `province`, `note`.
- Class `CartItemInput`, lines 44-46; bases: BaseModel.
  Annotated fields: `variant_id`, `quantity`.
- Class `CartItemResponse`, lines 49-62; bases: BaseModel.
  Annotated fields: `variant_id`, `product_id`, `product_name`, `brand_name`, `brand_color`, `primary_image`, `size`, `colour`, `unit_price`, `quantity`, `subtotal`, `available_stock`, `seller_id`.
- Class `SellerCartGroup`, lines 65-70; bases: BaseModel.
  Annotated fields: `seller_id`, `brand_name`, `brand_color`, `items`, `group_subtotal`.
- Class `CartResponse`, lines 73-79; bases: BaseModel.
  Annotated fields: `items`, `grouped_by_seller`, `item_count`, `subtotal`, `shipping_fee`, `total`.
- Class `AddToCartRequest`, lines 82-84; bases: BaseModel.
  Annotated fields: `variant_id`, `quantity`.
- Class `UpdateCartItemRequest`, lines 87-88; bases: BaseModel.
  Annotated fields: `quantity`.
- Class `SyncCartRequest`, lines 91-92; bases: BaseModel.
  Annotated fields: `items`.
- Class `CreateOrderRequest`, lines 97-102; bases: BaseModel.
  Annotated fields: `shipping_address`, `payment_method`, `coupon_code`, `notes`.
- Class `CreateGuestOrderRequest`, lines 105-117; bases: CreateOrderRequest.
  Annotated fields: `guest_email`, `guest_name`, `guest_phone`, `items`.
- `CreateGuestOrderRequest.validate_phone` (sync), lines 114-117: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `re.match`.
- Class `GuestCheckoutQuoteRequest`, lines 120-124; bases: BaseModel.
  Annotated fields: `items`, `coupon_code`.
- Class `PaymentMethodAvailability`, lines 127-130; bases: BaseModel.
  Annotated fields: `method`, `available`, `unavailable_reason`.
- Class `GuestCheckoutQuoteResponse`, lines 133-145; bases: BaseModel.
  Annotated fields: `items`, `item_count`, `subtotal`, `discount_amount`, `shipping_fee`, `total`, `free_shipping_threshold`, `amount_until_free_shipping`, `currency`, `coupon_requires_sign_in`, `payment_methods`, `will_revalidate_on_order`.
- Class `CreateOrderResponse`, lines 148-156; bases: BaseModel.
  Annotated fields: `order_id`, `order_number`, `status`, `total`, `payment_method`, `guest_token`, `payment_url`, `whatsapp_url`.
- Class `OrderItemResponse`, lines 161-172; bases: BaseModel.
  Annotated fields: `id`, `seller_id`, `product_id`, `variant_id`, `product_name`, `variant_label`, `unit_price`, `quantity`, `subtotal`.
- Class `SellerOrderResponse`, lines 175-186; bases: BaseModel.
  Annotated fields: `id`, `seller_id`, `brand_name`, `status`, `subtotal`, `tracking_number`, `courier_name`, `shipped_at`, `delivered_at`.
- Class `OrderDetailResponse`, lines 189-204; bases: BaseModel.
  Annotated fields: `id`, `order_number`, `status`, `payment_method`, `subtotal`, `discount_amount`, `shipping_fee`, `total`, `notes`, `address`, `items`, `seller_orders`, `created_at`.
- Class `OrderRowResponse`, lines 207-215; bases: BaseModel.
  Annotated fields: `id`, `order_number`, `status`, `total`, `item_count`, `created_at`.
- Class `PageInfo`, lines 218-222; bases: BaseModel.
  Annotated fields: `page`, `per_page`, `total`, `total_pages`.
- Class `PaginatedOrders`, lines 225-227; bases: BaseModel.
  Annotated fields: `data`, `pagination`.
- Class `CancelOrderRequest`, lines 232-233; bases: BaseModel.
  Annotated fields: `reason`.
- Class `ValidateCouponRequest`, lines 238-240; bases: BaseModel.
  Annotated fields: `code`, `subtotal`.
- Class `CouponValidationResponse`, lines 243-248; bases: BaseModel.
  Annotated fields: `code`, `discount_type`, `discount_value`, `discount_amount`, `new_subtotal`.
- Class `UpdateSellerOrderRequest`, lines 253-262; bases: BaseModel.
  Annotated fields: `status`, `tracking_number`, `courier_name`.
- `UpdateSellerOrderRequest.tracking_required_for_shipped` (sync), lines 259-262: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `model_validator`.
- Class `OrderTrackingResponse`, lines 267-271; bases: BaseModel.
  Annotated fields: `order_number`, `status`, `seller_orders`, `created_at`.

## app/schemas/payment.py

161 lines; SHA-256 `2fc381479883f11989669792ea6c16a4fa24cd7b70d5ea4af4e43fa6501afdfb`. [Open source](../../app/schemas/payment.py).

Backend imports: `app.models.order`.

- Class `InitiatePaymentRequest`, lines 17-18; bases: BaseModel.
  Annotated fields: `order_id`.
- Class `PayFastCheckoutResponse`, lines 21-27; bases: BaseModel.
  Annotated fields: `payment_id`, `checkout_url`, `payload`, `expires_at`.
- Class `PaymentInitResponse`, lines 30-37; bases: BaseModel.
  Annotated fields: `payment_id`, `method`, `checkout_url`, `payfast_payload`, `expires_at`.
- Class `PaymentStatusResponse`, lines 40-47; bases: BaseModel.
  Annotated fields: `order_id`, `payment_id`, `status`, `method`, `amount`, `gateway_reference`, `paid_at`.
- Class `RetryPaymentRequest`, lines 50-51; bases: BaseModel.
  Annotated fields: `payment_method`.
- Class `RefundRequest`, lines 54-57; bases: BaseModel.
  Annotated fields: `idempotency_key`, `amount`, `reason`.
- Class `RefundResponse`, lines 60-70; bases: BaseModel.
  Annotated fields: `status`, `processed_at`, `refund_id`, `payment_id`, `amount`, `reason`, `gateway_ref`, `created_at`.
- Class `AdminRefundRowResponse`, lines 73-86; bases: BaseModel.
  Annotated fields: `refund_id`, `payment_id`, `order_id`, `order_number`, `return_id`, `status`, `amount`, `reason`, `transfer_reference`, `requested_by`, `confirmed_by`, `requested_at`, `processed_at`.
- Class `PaginatedRefunds`, lines 89-92; bases: BaseModel.
  Annotated fields: `data`, `total`, `page`.
- Class `RefundHistoryEvent`, lines 95-99; bases: BaseModel.
  Annotated fields: `event`, `occurred_at`, `actor_id`, `transfer_reference`.
- Class `RefundPaymentBalanceResponse`, lines 102-113; bases: BaseModel.
  Annotated fields: `payment_id`, `order_id`, `order_number`, `payment_status`, `payment_method`, `payment_amount`, `pending_refund_amount`, `completed_refund_amount`, `reserved_refund_amount`, `remaining_refundable_amount`, `can_request_refund`.
- Class `AdminRefundDetailResponse`, lines 116-118; bases: AdminRefundRowResponse.
  Annotated fields: `payment`, `history`.
- Class `PaymentRefundHistoryResponse`, lines 121-122; bases: RefundPaymentBalanceResponse.
  Annotated fields: `refunds`.
- Class `GatewayStatusResponse`, lines 125-127; bases: BaseModel.
  Annotated fields: `payfast`, `cod`.
- Class `PayFastReconcileResponse`, lines 130-137; bases: BaseModel.
  Annotated fields: `order_id`, `payment_id`, `provider_status`, `local_status`, `transaction_id`, `matched`, `detail`.
- Class `PaymentRowResponse`, lines 140-151; bases: BaseModel.
  Annotated fields: `id`, `order_id`, `order_number`, `method`, `status`, `amount`, `gateway_reference`, `paid_at`, `created_at`.
- Class `PaginatedPayments`, lines 154-157; bases: BaseModel.
  Annotated fields: `data`, `total`, `page`.
- Class `TransferConfirmationRequest`, lines 160-161; bases: BaseModel.
  Annotated fields: `reference`.

## app/schemas/product.py

217 lines; SHA-256 `5e7fa83ffa941c9a0260943a8a2ba16be37eedbb4c26135d8f2df724624fb329`. [Open source](../../app/schemas/product.py).

- Class `CreateVariantRequest`, lines 14-20; bases: BaseModel.
  Annotated fields: `size_type`, `size_value`, `colour`, `stock`, `price_override`, `sku`.
- Class `VariantWithStockResponse`, lines 23-34; bases: BaseModel.
  Annotated fields: `id`, `sku`, `size_type`, `size_value`, `colour`, `price`, `stock`, `available_stock`, `is_active`.
- Class `CreateProductRequest`, lines 39-54; bases: BaseModel.
  Annotated fields: `name`, `description`, `price`, `sale_price`, `category_id`, `is_published`, `meta_title`, `meta_description`, `variants`.
- `CreateProductRequest.sale_must_be_less_than_price` (sync), lines 51-54: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `model_validator`.
- Class `UpdateProductRequest`, lines 57-70; bases: BaseModel.
  Annotated fields: `name`, `description`, `price`, `sale_price`, `category_id`, `meta_title`, `meta_description`.
- `UpdateProductRequest.at_least_one` (sync), lines 67-70: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `model_validator`.
- Class `ProductImageResponse`, lines 75-82; bases: BaseModel.
  Annotated fields: `id`, `url`, `alt_text`, `sort_order`, `is_primary`.
- Class `CategoryResponse`, lines 87-92; bases: BaseModel.
  Annotated fields: `id`, `name`, `slug`.
- Class `SellerSummaryResponse`, lines 97-107; bases: BaseModel.
  Annotated fields: `id`, `brand_name`, `slug`, `logo_url`, `brand_color`, `return_policy`, `whatsapp_number`, `avg_rating`.
- Class `ProductCardResponse`, lines 112-130; bases: BaseModel.
  Annotated fields: `id`, `seller_id`, `brand_name`, `brand_color`, `name`, `slug`, `price`, `sale_price`, `primary_image`, `colours`, `alpha_sizes`, `numeric_sizes`, `avg_rating`, `review_count`, `is_new`, `has_stock`.
- Class `ProductDetailResponse`, lines 133-141; bases: ProductCardResponse.
  Annotated fields: `description`, `meta_title`, `meta_description`, `images`, `variants`, `seller`, `category`, `created_at`.
- Class `CursorPagination`, lines 144-147; bases: BaseModel.
  Annotated fields: `next_cursor`, `has_next`, `limit`.
- Class `CataloguePage`, lines 150-152; bases: BaseModel.
  Annotated fields: `data`, `pagination`.
- Class `SellerProductRowResponse`, lines 157-169; bases: BaseModel.
  Annotated fields: `id`, `name`, `slug`, `category`, `price`, `total_stock`, `is_published`, `avg_rating`, `review_count`, `image_count`.
- Class `SlotInfoResponse`, lines 172-175; bases: BaseModel.
  Annotated fields: `total_slots`, `slots_used`, `slots_available`.
- Class `SellerProductsPage`, lines 178-180; bases: BaseModel.
  Annotated fields: `data`, `slot_info`.
- Class `UploadImagesResponse`, lines 183-184; bases: BaseModel.
  Annotated fields: `images`.
- Class `SearchSuggestion`, lines 189-194; bases: BaseModel.
  Annotated fields: `id`, `name`, `primary_image`, `price`, `brand_name`.
- Class `BrandSuggestion`, lines 197-201; bases: BaseModel.
  Annotated fields: `id`, `brand_name`, `logo_url`, `slug`.
- Class `SearchSuggestionsResponse`, lines 204-206; bases: BaseModel.
  Annotated fields: `products`, `brands`.
- Class `UpdateVariantRequest`, lines 208-213; bases: BaseModel.
  Annotated fields: `size_type`, `size_value`, `colour`, `price_override`, `is_active`.
- Class `ReorderImagesRequest`, lines 216-217; bases: BaseModel.
  Annotated fields: `image_ids`.

## app/schemas/return_.py

171 lines; SHA-256 `54592014ead9f46b2cb81ef19524a769416c33e571a7206d58242c52b4e4014e`. [Open source](../../app/schemas/return_.py).

- Class `ReturnItemRequest`, lines 11-14; bases: BaseModel.
  Annotated fields: `order_item_id`, `quantity`, `reason`.
- Class `CreateReturnRequest`, lines 17-21; bases: BaseModel.
  Annotated fields: `seller_order_id`, `reason`, `items`, `notes`.
- Class `ReturnItemResponse`, lines 24-30; bases: BaseModel.
  Annotated fields: `id`, `order_item_id`, `quantity`, `reason`.
- Class `ReturnRowResponse`, lines 33-43; bases: BaseModel.
  Annotated fields: `id`, `order_id`, `seller_order_id`, `status`, `reason`, `item_count`, `requested_at`, `resolved_at`.
- Class `ReturnDetailResponse`, lines 46-48; bases: ReturnRowResponse.
  Annotated fields: `notes`, `items`.
- Class `AdminReturnCustomerResponse`, lines 51-57; bases: BaseModel.
  Annotated fields: `user_id`, `is_guest`, `email`, `first_name`, `last_name`, `phone`.
- Class `AdminReturnSellerResponse`, lines 60-62; bases: BaseModel.
  Annotated fields: `seller_id`, `brand_name`.
- Class `AdminReturnOrderResponse`, lines 65-75; bases: BaseModel.
  Annotated fields: `order_id`, `order_number`, `status`, `payment_method`, `subtotal`, `discount_amount`, `shipping_fee`, `total`, `payment_id`, `payment_status`.
- Class `AdminReturnItemResponse`, lines 78-89; bases: BaseModel.
  Annotated fields: `id`, `order_item_id`, `product_id`, `variant_id`, `product_name`, `variant_label`, `unit_price`, `purchased_quantity`, `requested_quantity`, `line_subtotal`, `reason`.
- Class `AdminReturnRefundResponse`, lines 92-98; bases: BaseModel.
  Annotated fields: `refund_id`, `status`, `amount`, `transfer_reference`, `requested_at`, `processed_at`.
- Class `AdminReturnDisputeResponse`, lines 101-103; bases: BaseModel.
  Annotated fields: `dispute_id`, `status`.
- Class `AdminReturnDetailResponse`, lines 106-115; bases: ReturnRowResponse.
  Annotated fields: `notes`, `customer`, `seller`, `order`, `items`, `estimated_refund_amount`, `available_actions`, `refund`, `dispute`.
- Class `SellerReturnDetailResponse`, lines 118-125; bases: ReturnRowResponse.
  Annotated fields: `notes`, `order_number`, `items`, `estimated_refund_amount`, `available_actions`, `refund_status`, `dispute_status`.
- Class `PaginatedReturns`, lines 128-132; bases: BaseModel.
  Annotated fields: `data`, `total`, `page`, `total_pages`.
- Class `OpenDisputeRequest`, lines 135-136; bases: BaseModel.
  Annotated fields: `message`.
- Class `AddDisputeMessageRequest`, lines 139-140; bases: BaseModel.
  Annotated fields: `body`.
- Class `DisputeMessageResponse`, lines 143-149; bases: BaseModel.
  Annotated fields: `id`, `sender_id`, `body`, `created_at`.
- Class `DisputeDetailResponse`, lines 152-162; bases: BaseModel.
  Annotated fields: `id`, `return_id`, `seller_id`, `status`, `resolution_note`, `created_at`, `resolved_at`, `messages`.
- Class `AdminReturnActionRequest`, lines 165-166; bases: BaseModel.
  Annotated fields: `admin_note`.
- Class `ResolveDisputeRequest`, lines 169-171; bases: BaseModel.
  Annotated fields: `in_favor_of`, `resolution_note`.

## app/schemas/seller.py

247 lines; SHA-256 `607e00015698693a8df7bc4554a820534893c3137597ff4da9938970295dbd63`. [Open source](../../app/schemas/seller.py).

- Class `SellerRegistrationRequest`, lines 14-40; bases: BaseModel.
  Annotated fields: `email`, `password`, `first_name`, `last_name`, `brand_name`, `description`, `return_policy`, `whatsapp_number`, `instagram_handle`, `extra_slots`.
- `SellerRegistrationRequest.validate_pk_phone` (sync), lines 28-31: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `re.match`.
- `SellerRegistrationRequest.password_strength` (sync), lines 35-40: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `re.search`.
- Class `SellerRegistrationResponse`, lines 43-46; bases: BaseModel.
  Annotated fields: `amount_due`, `seller_id`, `message`.
- Class `SlotPricingResponse`, lines 51-58; bases: BaseModel.
  Annotated fields: `registration_fee`, `base_slots`, `extra_slots`, `extra_slot_price`, `extra_cost`, `total_cost`, `total_slots`.
- Class `SlotPurchaseRequest`, lines 61-63; bases: BaseModel.
  Annotated fields: `quantity`, `payment_method`.
- Class `SlotPurchaseResponse`, lines 66-70; bases: BaseModel.
  Annotated fields: `slots_purchased`, `new_total_slots`, `new_slots_available`, `amount_charged`.
- Class `SellerProfileResponse`, lines 75-93; bases: BaseModel.
  Annotated fields: `registration_amount_due`, `registration_paid_at`, `id`, `brand_name`, `slug`, `description`, `logo_url`, `brand_color`, `return_policy`, `whatsapp_number`, `instagram_handle`, `status`, `total_slots`, `slots_used`, `slots_available`, `joined_at`.
- Class `SellerProfileUpdateRequest`, lines 96-107; bases: BaseModel.
  Annotated fields: `description`, `return_policy`, `whatsapp_number`, `instagram_handle`, `brand_color`.
- `SellerProfileUpdateRequest.at_least_one_field` (sync), lines 104-107: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `all`, `model_validator`, `self.model_dump`, `self.model_dump().values`.
- Class `LogoUploadResponse`, lines 110-111; bases: BaseModel.
  Annotated fields: `logo_url`.
- Class `OrderStatusBreakdown`, lines 116-122; bases: BaseModel.
  Annotated fields: `pending`, `processing`, `shipped`, `delivered`, `cancelled`, `returned`.
- Class `SellerDashboardResponse`, lines 125-136; bases: BaseModel.
  Annotated fields: `period`, `gross_revenue`, `commission_paid`, `net_earnings`, `order_count`, `product_count`, `slots_used`, `slots_available`, `pending_balance`, `available_balance`, `status_breakdown`.
- Class `SellerOrderRow`, lines 141-152; bases: BaseModel.
  Annotated fields: `id`, `order_number`, `status`, `subtotal`, `net_amount`, `payment_method`, `cod_verified`, `item_count`, `created_at`.
- Class `ShippingAddressSchema`, lines 155-158; bases: BaseModel.
  Annotated fields: `street`, `city`, `province`.
- Class `OrderItemSchema`, lines 161-166; bases: BaseModel.
  Annotated fields: `product_name`, `variant_label`, `unit_price`, `quantity`, `subtotal`.
- Class `SellerOrderDetailResponse`, lines 169-177; bases: SellerOrderRow.
  Annotated fields: `customer_name`, `customer_phone`, `shipping_address`, `items`, `tracking_number`, `courier_name`, `commission_rate`, `commission_amount`.
- Class `UpdateOrderStatusRequest`, lines 180-189; bases: BaseModel.
  Annotated fields: `status`, `tracking_number`, `courier_name`.
- `UpdateOrderStatusRequest.tracking_required_for_shipped` (sync), lines 186-189: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `model_validator`.
- Class `CreateBankAccountRequest`, lines 194-206; bases: BaseModel.
  Annotated fields: `bank_name`, `account_title`, `account_number`, `is_default`.
- `CreateBankAccountRequest.at_least_one_payment_method` (sync), lines 201-206: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `model_validator`.
- Class `BankAccountResponse`, lines 209-217; bases: BaseModel.
  Annotated fields: `id`, `bank_name`, `account_title`, `account_number`, `is_default`, `created_at`.
- Class `RevenueDayRow`, lines 222-227; bases: BaseModel.
  Annotated fields: `date`, `gross`, `commission`, `net`, `order_count`.
- Class `RevenueAnalyticsResponse`, lines 230-233; bases: BaseModel.
  Annotated fields: `period`, `granularity`, `data`.
- Class `PagePagination`, lines 238-242; bases: BaseModel.
  Annotated fields: `page`, `per_page`, `total`, `total_pages`.
- Class `PaginatedSellerOrders`, lines 245-247; bases: BaseModel.
  Annotated fields: `data`, `pagination`.

## app/schemas/user.py

302 lines; SHA-256 `d0da353c20cc315477d83b5bbb37be5bd760283e26d38e943cdc404ddcbb488d`. [Open source](../../app/schemas/user.py).

Backend imports: `app.schemas.common`.

- Class `UserProfileResponse`, lines 29-39; bases: DRIPResponseModel.
  Annotated fields: `id`, `email`, `first_name`, `last_name`, `phone`, `avatar_url`, `has_verified_email`, `is_2fa_enabled`, `last_login_at`, `created_at`.
- Class `UpdateProfileRequest`, lines 42-67; bases: DRIPBaseModel.
  Annotated fields: `first_name`, `last_name`, `phone`.
- `UpdateProfileRequest.validate_name` (sync), lines 49-57: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `len`, `re.match`, `v.strip`.
- `UpdateProfileRequest.validate_phone` (sync), lines 61-67: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `_PHONE.match`, `field_validator`, `v.strip`.
- Class `ChangePasswordRequest`, lines 70-94; bases: DRIPBaseModel.
  Annotated fields: `current_password`, `new_password`, `confirm_password`.
- `ChangePasswordRequest.validate_new_password` (sync), lines 77-88: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `len`, `re.search`.
- `ChangePasswordRequest.passwords_match` (sync), lines 91-94: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `model_validator`.
- Class `AvatarUploadResponse`, lines 97-98; bases: DRIPResponseModel.
  Annotated fields: `avatar_url`.
- Class `AddressResponse`, lines 103-110; bases: DRIPResponseModel.
  Annotated fields: `id`, `label`, `street`, `city`, `province`, `is_default`, `created_at`.
- Class `CreateAddressRequest`, lines 113-148; bases: DRIPBaseModel.
  Annotated fields: `label`, `street`, `city`, `province`, `is_default`.
- `CreateAddressRequest.validate_street` (sync), lines 122-128: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `len`, `v.strip`.
- `CreateAddressRequest.validate_location` (sync), lines 132-138: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `len`, `v.strip`.
- `CreateAddressRequest.validate_label` (sync), lines 142-148: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `len`, `v.strip`.
- Class `UpdateAddressRequest`, lines 151-156; bases: DRIPBaseModel.
  Annotated fields: `label`, `street`, `city`, `province`, `is_default`.
- Class `ReviewImageResponse`, lines 161-164; bases: DRIPResponseModel.
  Annotated fields: `id`, `url`, `sort_order`.
- Class `ReviewAuthorResponse`, lines 167-171; bases: DRIPResponseModel.
  Annotated fields: `id`, `first_name`, `last_name`, `avatar_url`.
- Class `ReviewResponse`, lines 174-187; bases: DRIPResponseModel.
  Annotated fields: `id`, `user`, `product_id`, `rating`, `title`, `body`, `status`, `is_verified_purchase`, `helpful_count`, `unhelpful_count`, `images`, `created_at`, `updated_at`.
- Class `CreateReviewRequest`, lines 190-222; bases: DRIPBaseModel.
  Annotated fields: `product_id`, `order_id`, `rating`, `title`, `body`.
- `CreateReviewRequest.validate_rating` (sync), lines 199-202: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`.
- `CreateReviewRequest.validate_title` (sync), lines 206-212: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `len`, `v.strip`.
- `CreateReviewRequest.validate_body` (sync), lines 216-222: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `len`, `v.strip`.
- Class `UpdateReviewRequest`, lines 225-235; bases: DRIPBaseModel.
  Annotated fields: `rating`, `title`, `body`.
- `UpdateReviewRequest.validate_rating` (sync), lines 232-235: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`.
- Class `ReviewHelpfulRequest`, lines 238-239; bases: DRIPBaseModel.
  Annotated fields: `helpful`.
- Class `PaginatedReviews`, lines 242-249; bases: DRIPResponseModel.
  Annotated fields: `data`, `total`, `page`, `per_page`, `pages`, `avg_rating`, `rating_breakdown`.
- Class `WishlistItemResponse`, lines 254-263; bases: DRIPResponseModel.
  Annotated fields: `id`, `product_id`, `product_name`, `product_slug`, `product_image`, `price`, `sale_price`, `is_in_stock`, `added_at`.
- Class `WishlistResponse`, lines 266-268; bases: DRIPResponseModel.
  Annotated fields: `items`, `total`.
- Class `AddToWishlistRequest`, lines 271-272; bases: DRIPBaseModel.
  Annotated fields: `product_id`.
- Class `NotificationPreferencesResponse`, lines 277-282; bases: DRIPResponseModel.
  Annotated fields: `email_order_updates`, `email_promotions`, `email_new_arrivals`, `sms_order_updates`, `whatsapp_order_updates`.
- Class `UpdateNotificationPreferencesRequest`, lines 285-290; bases: DRIPBaseModel.
  Annotated fields: `email_order_updates`, `email_promotions`, `email_new_arrivals`, `sms_order_updates`, `whatsapp_order_updates`.
- Class `DeleteAccountRequest`, lines 293-302; bases: DRIPBaseModel.
  Annotated fields: `password`, `confirm_phrase`.
- `DeleteAccountRequest.validate_phrase` (sync), lines 299-302: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `v.strip`.

## app/schemas/wallet.py

102 lines; SHA-256 `2371e566a95066ea0cbd288d178992c02bd3d1e633670f2b679483b28a1ae334`. [Open source](../../app/schemas/wallet.py).

- Class `WalletSummaryResponse`, lines 11-15; bases: BaseModel.
  Annotated fields: `available_balance`, `pending_balance`, `total_earned`, `total_commission`.
- Class `WalletTransactionResponse`, lines 18-27; bases: BaseModel.
  Annotated fields: `id`, `type`, `amount`, `balance_after`, `reference`, `note`, `created_at`.
- Class `PaginatedTransactions`, lines 30-35; bases: BaseModel.
  Annotated fields: `data`, `total`, `page`, `per_page`, `total_pages`.
- Class `WithdrawalRequest`, lines 38-41; bases: BaseModel.
  Annotated fields: `amount`, `bank_account_id`, `note`.
- Class `PayoutResponse`, lines 44-55; bases: BaseModel.
  Annotated fields: `id`, `amount`, `payment_method`, `payment_detail`, `status`, `admin_note`, `requested_at`, `completed_at`, `transfer_reference`.
- Class `PaginatedPayouts`, lines 58-62; bases: BaseModel.
  Annotated fields: `data`, `total`, `page`, `total_pages`.
- Class `CommissionEntryResponse`, lines 65-74; bases: BaseModel.
  Annotated fields: `id`, `seller_order_id`, `gross_amount`, `commission_rate`, `commission_amount`, `seller_amount`, `settled_at`.
- Class `CommissionSummary`, lines 77-80; bases: BaseModel.
  Annotated fields: `total_gross`, `total_commission`, `total_net`.
- Class `CommissionBreakdownResponse`, lines 83-87; bases: BaseModel.
  Annotated fields: `data`, `summary`, `total`, `page`.
- Class `AdminPayoutActionRequest`, lines 90-91; bases: BaseModel.
  Annotated fields: `admin_note`.
- Class `CompletePayoutRequest`, lines 94-95; bases: BaseModel.
  Annotated fields: `reference`.
- Class `AdminWalletOverviewResponse`, lines 98-102; bases: BaseModel.
  Annotated fields: `total_available_balance`, `total_pending_balance`, `total_payouts_pending`, `total_payouts_completed`.



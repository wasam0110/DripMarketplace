# DRIP Backend — Build Progress

> **Read this first every session.** Tells you exactly where we are, what's done, and what's next.
> Update checkboxes as each file is completed.

---

## Tech Stack (locked)
- **Framework:** FastAPI + Python 3.13
- **ORM:** SQLAlchemy 2.x async + asyncpg
- **DB:** PostgreSQL 15 (Supabase)
- **Cache/Queue:** Redis + ARQ
- **Auth:** JWT RS256 + Argon2id + Refresh tokens + TOTP (admin)
- **Email:** Resend
- **Payments:** JazzCash · Easypaisa · Stripe · COD
- **Storage:** Supabase Storage
- **Deploy:** Railway (API + Worker) · Vercel (frontend)

---

## Block Status

| Block | Name | Status |
|-------|------|--------|
| 1 | Foundation | ✅ Complete |
| 2 | Auth | ✅ Complete |
| 3 | Sellers & Slots | ✅ Complete |
| 4 | Products & Images | ✅ Complete |
| 5 | Cart & Orders | ✅ Complete |
| 6 | Payments | ❌ Not started |
| 7 | Wallet & Commission | ❌ Not started |
| 8 | Admin Panel | ❌ Not started |
| 9 | Notifications | ❌ Not started |
| 10 | Returns & Disputes | ❌ Not started |
| 11 | Analytics | ❌ Not started |
| 12 | Tests & Hardening | ❌ Not started |

---

## Block 1 — Foundation ✅
**Completed:** Session 1
**Commit:** `feat: Block 1 — foundation`

### What was built
- Full project scaffold — Dockerfile, docker-compose, Makefile, .env.example, .gitignore
- `app/core/config.py` — Pydantic Settings with all env var validators
- `app/core/logging.py` — structlog JSON logger with PII scrubber
- `app/core/exceptions.py` — 30+ typed exception hierarchy (`DRIPException` base)
- `app/core/database.py` — async SQLAlchemy engine + session factory + `get_db`
- `app/core/redis.py` — connection pool + key helpers + cache utils
- `app/core/middleware.py` — security headers, request ID, logging, rate limiting
- `app/core/security.py` — Argon2id hashing, RS256 JWT, refresh tokens, TOTP
- `app/models/base.py` — `Base`, `UUIDPrimaryKeyMixin`, `AuditMixin`, `SoftDeleteMixin`
- `app/schemas/common.py` — pagination, error response, shared field validators
- `app/repositories/base.py` — generic async CRUD
- `app/api/deps.py` — `get_db`, `require_customer`, `require_seller`, `require_admin`, `CurrentUser`, `CurrentSeller`, `CurrentAdmin`
- `app/api/v1/health.py` — health check endpoint
- `app/api/v1/router.py` — master router
- `app/tasks/worker.py` — ARQ WorkerSettings stub
- `main.py` — app factory, lifespan, middleware, exception handlers
- `tests/conftest.py` — shared fixtures
- All `__init__.py` files
- **Verified:** `python -c "from app.core.config import Settings"` ✅

---

## Block 2 — Auth ✅
**Completed:** Session 1
**Commit:** `feat: Block 2 — auth`

### What was built
- `app/models/user.py` — `User`, `UserSession`, `UserAddress`
  - `User`: email, password_hash, role (customer/seller/admin), first_name, last_name, phone, avatar_url, has_verified_email, google_id, totp_secret, is_2fa_enabled, last_login_at
  - `UserSession`: token_hash, ip_address, user_agent, expires_at
  - `UserAddress`: label, street, city, province, is_default
- `app/repositories/user_repo.py` — `UserRepository`, `SessionRepository`, `AddressRepository`
- `app/schemas/auth.py` — 12 schemas: RegisterRequest, LoginRequest, AuthResponse, TokenResponse, RefreshRequest, and more
- `app/services/auth_service.py` — register, login, refresh, logout, verify_email, forgot_password, reset_password, google_oauth, setup_2fa
- `app/integrations/resend_client.py` — email wrapper + templates
- `app/tasks/email_tasks.py` — send_verification_email, send_password_reset_email
- `app/api/v1/auth.py` — 12 endpoints
- `alembic/versions/001_create_users.py` (revision: `001`)
- **Migration stamped:** `001` ✅

---

## Block 3 — Sellers & Slots ✅
**Completed:** Session 2
**Commit:** `feat: Block 3 — sellers & slots`
**Tests:** 50/50 ✅

### What was built
- `app/models/seller.py` — `Seller`, `SellerWallet`, `SellerBankAccount`
  - `Seller`: brand_name, slug, status (pending_payment/pending_approval/active/suspended/rejected), total_slots, slots_used, registration_fee, approved_by
  - DB constraints: slots_used ≤ total_slots, slots_used ≥ 0, total_slots ≥ 50
  - `SellerWallet`: available_balance, pending_balance, total_earned, total_commission
  - `SellerBankAccount`: bank_name, account_number, jazzcash_number, easypaisa_number, is_default
- `app/repositories/seller_repo.py` — `SellerRepository`, `WalletRepository`, `BankAccountRepository`
- `app/schemas/seller.py` — 20 Pydantic schemas
- `app/services/seller_service.py` — register (User + Seller atomically), profile, dashboard, bank accounts
- `app/services/slot_service.py` — calculate_pricing, purchase_slots, assert_slot_available
- `app/api/v1/sellers.py` — 11 endpoints (registration, profile, slots, dashboard, bank accounts, analytics stub)
- `alembic/versions/002_create_sellers.py` (revision: `002_create_sellers`)
- **Migration stamped:** `002_create_sellers` ✅

### Key decisions
- Seller registration is public — creates User (role=seller) + Seller + Wallet atomically
- `CurrentUser` returns JWT payload dict; `current_user["sub"]` = user_id
- `DRIPException.http_status` (not `status_code`)

---

## Block 4 — Products & Images ✅
**Completed:** Session 2
**Commit:** `feat: Block 4 — products & images`
**Tests:** 40/40 ✅

### What was built
- `app/models/product.py` — `Category`, `Product`, `ProductImage`, `ProductVariant`, `ProductInventory`, `Tag`, `product_tags`
  - Price constraints: PKR 100–500,000, sale_price < price
  - Inventory constraints: stock ≥ 0, reserved ≥ 0, stock ≥ reserved
  - Variant unique constraint: (product_id, size_value, colour)
- `app/repositories/product_repo.py` — `ProductRepository`, `VariantRepository`
- `app/repositories/inventory_repo.py` — `InventoryRepository` (reserve, release, deduct)
- `app/schemas/product.py` — 18 schemas
- `app/services/product_service.py` — create, update, delete, publish/unpublish (slot guard), catalogue (cursor pagination), search
- `app/services/image_service.py` — magic-byte validation, WebP conversion, Supabase upload
- `app/integrations/supabase_storage.py` — async httpx Supabase Storage wrapper
- `app/api/v1/products.py` — 17 endpoints (public catalogue, seller management, admin stubs)
- `alembic/versions/003_create_products.py` (revision: `003_create_products`)
- **Migration stamped:** `003_create_products` ✅

### Key decisions
- Slot consumed only on publish, freed on unpublish/delete
- Publish requires: ≥1 image, ≥1 variant, available slot
- `CurrentSeller` payload: `current_user["seller_id"]`

---

## Block 5 — Cart & Orders ✅
**Completed:** Session 3
**Commit:** `feat: Block 5 — cart & orders`
**Tests:** 43/43 ✅

### What was built
- `app/models/order.py` — `Order`, `OrderAddress`, `OrderItem`, `SellerOrder`, `OrderStatusHistory`
  - `Order`: user_id (nullable for guest), order_number (unique), status, guest_email/name/phone, subtotal, discount_amount, shipping_fee, total, payment_method, coupon_id, notes
  - DB constraints: total > 0, user_id IS NOT NULL OR guest_email IS NOT NULL
  - `OrderItem`: snapshots product_name + variant_label at order time; qty > 0
  - `SellerOrder`: per-seller subtotal, tracking_number, courier_name, shipped_at, delivered_at
  - `OrderStatusHistory`: full audit trail for every status change
- `app/models/coupon.py` — `Coupon`, `CouponUsage`
  - Coupon: percentage (max 70%) or fixed discount, min_order_amount, per-customer usage limit, validity window
- `app/repositories/order_repo.py` — `OrderRepository` (create, get_by_id, get_by_number, get_customer_orders, update_status, add_status_history), `SellerOrderRepository`
- `app/schemas/order.py` — 20+ schemas: CreateOrderRequest, CreateGuestOrderRequest, CartResponse, CartItemResponse, SellerCartGroup, OrderDetailResponse, CouponValidationResponse, UpdateSellerOrderRequest, and more
- `app/services/order_service.py` — create_order (atomic: validate stock → create order + items + seller_orders → reserve inventory → clear cart → enqueue COD timeout), create_guest_order, get_order, cancel_order (releases inventory), get_seller_orders, update_seller_order_status
- `app/services/cart_service.py` — Redis hash-based cart (CART_TTL 7 days), add_item (stock check), update_item, remove_item, clear, sync (guest→server merge on login), get_raw_items (used by order creation)
- `app/services/coupon_service.py` — validate (checks active, expiry, usage limits, per-customer limit), apply_to_order (records CouponUsage, increments uses_count)
- `app/api/v1/orders.py` — 9 endpoints: POST /orders, POST /orders/guest, GET /orders, GET /orders/{id}, GET /orders/number/{number}, POST /orders/{id}/cancel, POST /coupons/validate, GET/PUT /seller/orders, GET /seller/orders/{id}
- `app/api/v1/cart.py` — 6 endpoints: GET/POST /cart, PATCH/DELETE /cart/{variant_id}, POST /cart/clear, POST /cart/sync
- `app/tasks/order_tasks.py` — `cod_verification_timeout` (auto-cancel after 30 min), `send_order_confirmation` (stub — Block 9)
- `alembic/versions/004_create_orders.py` — discount_type, order_status, payment_method, seller_order_status enums + all 6 tables (revision: `004_create_orders`)
- **Modified:** `app/models/seller.py` (re-added seller_orders relationship), `app/models/user.py` (added orders relationship), `app/api/v1/sellers.py` (removed order stubs now live in orders.py), `app/api/v1/router.py`, `alembic/env.py`, `app/tasks/worker.py`
- **Migration stamped:** `004_create_orders` ✅

### Key decisions
- Cart is Redis-based (`cart:{user_id}` hash, TTL 7 days); order creation reads from Redis for auth users, from request body for guests
- Inventory is reserved (not deducted) at order time; deducted on delivery (Block 7)
- COD orders auto-cancel via ARQ task after 30 minutes if not verified
- Max COD: PKR 25,000 (BR-COD-01)
- Shipping: PKR 200 flat, free above PKR 5,000
- WhatsApp verification URL returned in CreateOrderResponse for COD orders
- Seller order status transitions: pending → processing → shipped → delivered
- `SellerOrder.back_populates="seller"` re-added to `Seller` model now that SellerOrder exists

---

## Block 6 — Payments ❌

- [ ] `app/models/payment.py` — Payment · PaymentCallback · Refund
- [ ] `app/repositories/payment_repo.py`
- [ ] `app/schemas/payment.py`
- [ ] `app/services/payment_service.py`
- [ ] `app/integrations/jazzcash.py` — HMAC build + verify + initiate
- [ ] `app/integrations/easypaisa.py` — hash build + verify + initiate
- [ ] `app/integrations/stripe_client.py` — PaymentIntent + webhook verify
- [ ] `app/api/v1/payments.py` — initiate + 3 callback endpoints + retry
- [ ] Tests (mock gateway callbacks)

---

## Block 7 — Wallet & Commission ❌

- [ ] `app/models/wallet.py` — WalletTransaction · CommissionLedger · Payout
- [ ] `app/repositories/wallet_repo.py`
- [ ] `app/schemas/wallet.py`
- [ ] `app/services/wallet_service.py` — double-entry ledger operations
- [ ] `app/services/commission_service.py` — settle_commission (called by ARQ task)
- [ ] `app/api/v1/wallet.py`
- [ ] `app/tasks/wallet_tasks.py` — settle_commission · move_pending_to_available
- [ ] `alembic/versions/005_create_wallet.py`
- [ ] Tests

---

## Block 8 — Admin ❌

- [ ] `app/api/v1/admin/brands.py`
- [ ] `app/api/v1/admin/orders.py`
- [ ] `app/api/v1/admin/payouts.py`
- [ ] `app/api/v1/admin/cod_queue.py`
- [ ] `app/api/v1/admin/content.py` — banners
- [ ] `app/api/v1/admin/settings.py` — system_settings
- [ ] Tests

---

## Block 9 — Notifications ❌

- [ ] `app/models/notification.py`
- [ ] `app/services/notification_service.py`
- [ ] `app/api/v1/notifications.py`
- [ ] Email templates (Resend)
- [ ] Tests

---

## Block 10 — Returns & Disputes ❌

- [ ] `app/models/return_.py` — Return · ReturnItem · Dispute · DisputeMessage
- [ ] `app/services/return_service.py`
- [ ] `app/api/v1/returns.py`
- [ ] Tests

---

## Block 11 — Analytics ❌

- [ ] `app/api/v1/analytics/seller.py`
- [ ] `app/api/v1/analytics/admin.py`
- [ ] Tests

---

## Block 12 — Hardening ❌

- [ ] Full test suite run — all blocks
- [ ] `pip-audit` — zero high/critical CVEs
- [ ] Load test with Locust (catalogue + order endpoints)
- [ ] OWASP ZAP scan
- [ ] `alembic/versions/` — final migration review
- [ ] Railway production deploy
- [ ] Sentry + UptimeRobot configured
- [ ] Backup restore drill

---

## Key Business Rules (quick ref)

| Rule | Value |
|------|-------|
| Registration fee | PKR 5,000 |
| Base slots | 50 |
| Extra slot price | PKR 50 each |
| Commission | 15% of subtotal (excl. shipping) |
| Shipping | PKR 200 flat / free above PKR 5,000 |
| COD timeout | 30 minutes |
| Wallet hold | 3 days after delivery |
| Min withdrawal | PKR 500 |
| Max COD order | PKR 25,000 |

---

## Current Session — Start Here

**Last completed:** Block 5 — Cart & Orders ✅ (43/43 tests, migration at head)
**Next to build:** Block 6 — Payments
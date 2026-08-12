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
| 5 | Cart & Orders | ❌ Not started |
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
- `app/models/user.py` — `User`, `UserSession`, `UserAddress` with full column set
  - `User`: email, password_hash, role (customer/seller/admin), first_name, last_name, phone, avatar_url, has_verified_email, google_id, totp_secret, is_2fa_enabled, last_login_at
  - `UserSession`: token_hash, ip_address, user_agent, expires_at
  - `UserAddress`: label, street, city, province, is_default
- `app/repositories/user_repo.py` — `UserRepository` (get_by_email, create, update, soft-delete), `SessionRepository`, `AddressRepository`
- `app/schemas/auth.py` — `RegisterRequest`, `LoginRequest`, `AuthResponse`, `TokenResponse`, `RefreshRequest`, 12 total schemas
- `app/services/auth_service.py` — register, login, refresh, logout, verify_email, forgot_password, reset_password, google_oauth, setup_2fa
- `app/integrations/resend_client.py` — email wrapper + templates (verification, password reset, welcome)
- `app/tasks/email_tasks.py` — `send_verification_email`, `send_password_reset_email` ARQ tasks
- `app/api/v1/auth.py` — 12 endpoints: POST /register, /login, /refresh, /logout, /forgot-password, /reset-password, /verify-email, /google, /google/callback, /me, /change-password, /setup-2fa
- `alembic/versions/001_create_users.py` — users, user_sessions, user_addresses tables (revision: `001`)
- Tests: `test_security.py`, `test_auth_service.py`, `test_auth_api.py`, `test_auth_security.py`
- **Migration stamped:** `001` ✅

---

## Block 3 — Sellers & Slots ✅
**Completed:** Session 2
**Commit:** `feat: Block 3 — sellers & slots`
**Tests:** 50/50 ✅

### What was built
- `app/models/seller.py` — `Seller`, `SellerWallet`, `SellerBankAccount`
  - `Seller`: brand_name, slug, description, logo_url, brand_color, return_policy, whatsapp_number, instagram_handle, status (pending_payment/pending_approval/active/suspended/rejected), total_slots, slots_used, registration_fee, approved_by, approved_at
  - DB constraints: slots_used ≤ total_slots, slots_used ≥ 0, total_slots ≥ 50
  - `SellerWallet`: available_balance, pending_balance, total_earned, total_commission
  - `SellerBankAccount`: bank_name, account_number, jazzcash_number, easypaisa_number, is_default
- `app/repositories/seller_repo.py` — `SellerRepository`, `WalletRepository`, `BankAccountRepository`
- `app/schemas/seller.py` — 20 Pydantic schemas covering registration, profile, slots, dashboard, orders (shapes), bank accounts, analytics, pagination
- `app/services/seller_service.py` — register (creates User + Seller atomically), get_profile, update_profile, update_logo, get_dashboard, list/add/delete bank accounts
- `app/services/slot_service.py` — `calculate_pricing` (static), `purchase_slots` (wallet live; JazzCash/Easypaisa wired in Block 6), `assert_slot_available`
- `app/api/v1/sellers.py` — 14 endpoints (public registration, profile, slots, dashboard, orders stub, bank accounts, analytics stub)
- `alembic/versions/002_create_sellers.py` — seller_status enum, sellers, seller_wallets, seller_bank_accounts (revision: `002_create_sellers`)
- **Modified:** `app/models/user.py` (real seller relationship), `app/api/v1/router.py`, `app/core/exceptions.py`
- **Migration stamped:** `002_create_sellers` ✅

### Key decisions
- Seller registration is public — creates User (role=seller) + Seller + Wallet atomically
- `CurrentUser` returns JWT payload dict; use `current_user["sub"]` for user_id
- `DRIPException.http_status` (not `status_code`) matches Block 1 base class

---

## Block 4 — Products & Images ✅
**Completed:** Session 2
**Commit:** `feat: Block 4 — products & images`
**Tests:** 40/40 ✅

### What was built
- `app/models/product.py` — `Category`, `Product`, `ProductImage`, `ProductVariant`, `ProductInventory`, `Tag`, `product_tags` association table
  - `Category`: self-referential parent/children, name, slug, image_url, sort_order, is_active
  - `Product`: seller_id, category_id, name, slug, description, price, sale_price, is_published, admin_hidden, meta_title, meta_description, avg_rating, review_count, view_count
  - DB constraints: price PKR 100–500,000, sale_price < price, avg_rating 0–5
  - `ProductVariant`: sku (unique), size_type (alpha/numeric/one_size), size_value, colour, price_override, is_active. Unique constraint on (product_id, size_value, colour)
  - `ProductInventory`: stock, reserved, available_stock property. Constraints: stock ≥ 0, reserved ≥ 0, stock ≥ reserved
  - `ProductImage`: url, alt_text, sort_order, is_primary (max 6 per product)
  - `Tag`: many-to-many with Product via product_tags
- `app/repositories/product_repo.py` — `ProductRepository` (create, get_by_id, get_by_slug, slug_exists, get_seller_products, list_catalogue with cursor pagination + filters, search_suggestions, soft_delete, increment_view_count, image management), `VariantRepository`
- `app/repositories/inventory_repo.py` — `InventoryRepository` (create, get_by_variant, update_stock, reserve, release, deduct)
- `app/schemas/product.py` — 18 Pydantic schemas: CreateProductRequest, UpdateProductRequest, CreateVariantRequest, ProductCardResponse, ProductDetailResponse, VariantWithStockResponse, SellerProductRowResponse, SlotInfoResponse, CursorPagination, SearchSuggestionsResponse, and more
- `app/services/product_service.py` — create_product (draft; optional publish), update_product, delete_product (frees slot if published), publish_product (validates images + variants + slot), unpublish_product (frees slot), get_catalogue (cursor-based with full filters), get_product_detail, get_product_by_slug, get_seller_products, add_images, get_variants, search_suggestions
- `app/services/image_service.py` — magic-byte validation (JPEG/PNG/WebP), 5MB limit, Pillow WebP conversion, Supabase upload
- `app/integrations/supabase_storage.py` — async httpx wrapper for Supabase Storage REST API (upload, get_public_url, delete)
- `app/api/v1/products.py` — 17 endpoints:
  - Public: `GET /products`, `GET /products/{id}`, `GET /products/slug/{slug}`, `GET /products/{id}/variants`, `GET /products/{id}/reviews` (stub), `POST /products/{id}/reviews` (stub), `GET /products/search/suggestions`
  - Seller: `GET /seller/products`, `POST /seller/products`, `PUT /seller/products/{id}`, `DELETE /seller/products/{id}`, `POST /seller/products/{id}/publish`, `POST /seller/products/{id}/unpublish`, `POST /seller/products/{id}/images`
  - Admin: `GET /admin/products` (stub — Block 8), `POST /admin/products/{id}/hide` (stub — Block 8)
- `alembic/versions/003_create_products.py` — size_type enum, categories, products, product_images, product_variants, product_inventory, tags, product_tags (revision: `003_create_products`)
- **Modified:** `app/api/v1/router.py` (products router), `app/models/seller.py` (removed future block relationships that caused mapper errors), `alembic/env.py` (Product model import), `app/api/deps.py` (fixed `SellerRepository(db).get_by_user_id()` instance method call)
- **Migration stamped:** `003_create_products` ✅

### Key decisions
- Creating a product never consumes a slot — slot consumed only on publish
- Deleting or unpublishing a published product frees the slot immediately
- Publish requires: ≥1 image, ≥1 variant, available slot
- Catalogue uses cursor pagination (created_at + id) for infinite scroll
- Images validated by magic bytes (not just extension), converted to WebP before upload
- `seller_orders`, `wallet_transactions`, `payouts` relationships removed from Seller model until Block 5/7 are built — will be re-added then
- `CurrentSeller` payload dict: use `current_user["seller_id"]` for seller_id

---

## Block 5 — Cart & Orders ❌

- [ ] `app/models/order.py` — Order · OrderItem · OrderAddress · SellerOrder · OrderStatusHistory
- [ ] `app/models/coupon.py` — Coupon · CouponUsage
- [ ] `app/repositories/order_repo.py`
- [ ] `app/schemas/order.py`
- [ ] `app/services/order_service.py` — create_order (atomic stock decrement) · cancel_order · cod_timeout
- [ ] `app/services/coupon_service.py`
- [ ] `app/api/v1/orders.py`
- [ ] `app/api/v1/cart.py`
- [ ] `app/tasks/order_tasks.py` — cod_verification_timeout · send_order_confirmation
- [ ] `alembic/versions/004_create_orders.py`
- [ ] Tests

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

**Last completed:** Block 4 — Products & Images ✅ (40/40 tests, migration at head)
**Next to build:** Block 5 — Cart & Orders
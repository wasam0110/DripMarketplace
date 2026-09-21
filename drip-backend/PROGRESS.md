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
- **Payments:** PayFast Pakistan · COD
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
| 6 | Payments (PayFast + COD) | ✅ Complete |
| 7 | Wallet & Commission | ✅ Complete |
| 8 | Admin Panel | ✅ Complete |
| 9 | Notifications | ✅ Complete |
| 10 | Returns & Disputes | ✅ Complete |
| 11 | Analytics | ✅ Complete (stubs) |
| 12 | Reviews & Inventory | ✅ Complete |
| 13 | Tests & Hardening | 🔄 In progress |

---

## Block 1 — Foundation ✅
**Completed:** Session 1

### What was built
- Full project scaffold — Dockerfile, docker-compose, Makefile, .env.example, .gitignore
- `app/core/config.py` — Pydantic Settings with all env var validators
- `app/core/logging.py` — structlog JSON logger with PII scrubber
- `app/core/exceptions.py` — 30+ typed exception hierarchy
- `app/core/database.py` — async SQLAlchemy engine + session factory
- `app/core/redis.py` — connection pool + key helpers + cache utils
- `app/core/middleware.py` — security headers, request ID, logging, rate limiting
- `app/core/security.py` — Argon2id hashing, RS256 JWT, refresh tokens, TOTP
- `app/models/base.py` — Base, UUIDPrimaryKeyMixin, AuditMixin, SoftDeleteMixin
- `app/schemas/common.py` — pagination, error response, shared field validators
- `app/repositories/base.py` — generic async CRUD
- `app/api/deps.py` — get_db, require_customer, require_seller, require_admin
- `app/api/v1/health.py` — health check endpoint
- `app/api/v1/router.py` — master router
- `app/tasks/worker.py` — ARQ WorkerSettings
- `main.py` — app factory, lifespan, middleware, exception handlers

---

## Block 2 — Auth ✅
**Completed:** Session 1

### What was built
- `app/models/user.py` — User, UserSession, UserAddress
- `app/repositories/user_repo.py` — UserRepository, SessionRepository, AddressRepository
- `app/schemas/auth.py` — 12 schemas
- `app/services/auth_service.py` — register, login, refresh, logout, verify_email, forgot/reset password, google_oauth, 2FA
- `app/integrations/resend_client.py` — email wrapper + templates
- `app/tasks/email_tasks.py` — send_verification_email, send_password_reset_email
- `app/api/v1/auth.py` — 12 endpoints
- `alembic/versions/001_create_users.py`

### Known fixes applied
- `auth_service.py` line 186: replaced lazy `user.seller` load with explicit async query to avoid MissingGreenlet error

---

## Block 3 — Sellers & Slots ✅
**Completed:** Session 2

### What was built
- `app/models/seller.py` — Seller, SellerWallet, SellerBankAccount
- `app/repositories/seller_repo.py`
- `app/schemas/seller.py` — 20 schemas
- `app/services/seller_service.py`
- `app/services/slot_service.py` — calculate_pricing, purchase_slots
- `app/api/v1/sellers.py` — 11 endpoints
- `alembic/versions/002_create_sellers.py`

---

## Block 4 — Products & Images ✅
**Completed:** Session 2

### What was built
- `app/models/product.py` — Category, Product, ProductImage, ProductVariant, ProductInventory, Tag
- `app/repositories/product_repo.py`, `inventory_repo.py`
- `app/schemas/product.py` — 18 schemas
- `app/services/product_service.py`, `image_service.py`
- `app/integrations/supabase_storage.py`
- `app/api/v1/products.py` — 17 endpoints
- `alembic/versions/003_create_products.py`

---

## Block 5 — Cart & Orders ✅
**Completed:** Session 3

### What was built
- `app/models/order.py` — Order, OrderAddress, OrderItem, SellerOrder, OrderStatusHistory
- `app/models/coupon.py` — Coupon, CouponUsage
- `app/repositories/order_repo.py`
- `app/schemas/order.py` — 20+ schemas
- `app/services/order_service.py` — create_order, cancel_order, get_seller_orders
- `app/services/cart_service.py` — Redis hash-based cart (TTL 7 days)
- `app/services/coupon_service.py`
- `app/api/v1/orders.py` — 9 endpoints
- `app/api/v1/cart.py` — 6 endpoints
- `app/tasks/order_tasks.py` — cod_verification_timeout
- `alembic/versions/004_create_orders.py`

---

## Block 6 — Payments (PayFast + COD) ✅
**Completed:** Session 4

### What was built
- `app/integrations/payfast.py` — PayFast Pakistan client (HMAC-SHA256 signing, IPN verification, checkout payload builder)
- `app/schemas/payment.py` — PayFast + COD schemas only
- `app/services/payment_service.py` — initiate, status, retry, IPN callback handler, refund, gateway status
- `app/api/v1/payments.py` — initiate, status, retry, `/callback/payfast` IPN endpoint, admin refund
- `alembic/versions/010_payfast_methods.py` — adds `payfast` to payment_method enum

### Key decisions
- Removed JazzCash, Easypaisa, Stripe completely
- PayFast + COD only
- IPN callback at `/api/v1/payments/callback/payfast` (no auth, called by PayFast)
- Refunds are manual (PayFast has no automated refund API)
- `PAYFAST_MERCHANT_ID`, `PAYFAST_SECURED_KEY`, `PAYFAST_SANDBOX` in .env

---

## Block 7 — Wallet & Commission ✅
**Completed:** Session 4

### What was built
- `app/models/wallet.py` — WalletTransaction, CommissionLedger, Payout
- `app/repositories/wallet_repo.py`
- `app/schemas/wallet.py`
- `app/services/wallet_service.py` — double-entry ledger
- `app/services/commission_service.py` — settle_commission (idempotent)
- `app/api/v1/wallet.py`
- `app/tasks/wallet_tasks.py` — settle_commission, move_pending_to_available
- `alembic/versions/006_create_wallet.py`

---

## Block 8 — Admin Panel ✅
**Completed:** Session 4

### What was built
- `app/api/v1/admin/brands.py` — seller approval/rejection
- `app/api/v1/admin/orders.py`
- `app/api/v1/admin/payouts.py` — payout approval
- `app/api/v1/admin/cod_queue.py` — COD verification queue
- `app/api/v1/admin/content.py` — banners
- `app/api/v1/admin/settings.py` — system settings
- `alembic/versions/007_create_admin.py`

---

## Block 9 — Notifications ✅
**Completed:** Session 4

### What was built
- `app/models/notification.py`
- `app/services/notification_service.py`
- `app/api/v1/notifications.py`
- `app/tasks/notification_tasks.py` — send_order_confirmation, send_order_status_update, send_payout_notification, notify_seller_decision, broadcast_notification
- `alembic/versions/008_create_notifications.py`

---

## Block 10 — Returns & Disputes ✅
**Completed:** Session 4

### What was built
- `app/models/return_.py` — Return, ReturnItem, Dispute, DisputeMessage
- `app/services/return_service.py`
- `app/api/v1/returns.py`
- `alembic/versions/009_create_returns.py`

---

## Block 11 — Analytics ✅ (stubs)
**Completed:** Session 4

### What was built
- `app/api/v1/admin/dashboard.py` — platform dashboard (GMV, orders, pending payouts)
- `app/api/v1/sellers.py` — seller dashboard (revenue, orders, slots)
- Full analytics to be expanded post-launch

---

## Block 12 — Reviews & Inventory ✅
**Completed:** Session 4

### What was built
- `app/models/review.py` — Review, ReviewImage
- `app/schemas/user.py` — full customer profile schemas (addresses, reviews, wishlist, notifications)
- `app/api/v1/customers.py` — 18 endpoints (profile, avatar, password, addresses, reviews, wishlist, notification prefs, account deletion)
- `app/api/v1/inventory.py` — 8 endpoints (seller inventory list/get/set/adjust/low-stock + admin list/bulk-update)
- `app/services/customer_service.py`
- `app/services/inventory_service.py`
- `app/repositories/inventory_repo.py`
- `app/tasks/cleanup_tasks.py` — 6 cleanup tasks (sessions, soft-deleted users, carts, reset tokens, notifications, orphaned images)
- `alembic/versions/011_create_reviews.py`

---

## Block 13 — Tests & Hardening 🔄

- ✅ `tests/unit/test_commission_service.py`
- ✅ `tests/unit/test_slot_service.py`
- ✅ `tests/security/test_auth.py` — rate limiting, JWT tamper, RBAC, HMAC, injection
- ✅ `tests/load/locustfile.py` — 4 Locust user classes (BrowseUser 70%, CustomerUser 25%, SellerUser 4%, AdminUser 1%)
- ❌ Full test suite run — all blocks
- ❌ `pip-audit` — zero high/critical CVEs
- ❌ Load test run (Locust)
- ❌ OWASP ZAP scan
- ❌ Railway production deploy
- ❌ Sentry + UptimeRobot configured
- ❌ Backup restore drill

---

## Migration History

| Version | Name | Status |
|---------|------|--------|
| 001 | create_users | ✅ Applied |
| 002_create_sellers | create_sellers | ✅ Applied |
| 003_create_products | create_products | ✅ Applied |
| 004_create_orders | create_orders | ✅ Applied |
| 005_create_payments | create_payments | ✅ Applied |
| 006_create_wallet | create_wallet | ✅ Applied |
| 007_create_admin | create_admin | ✅ Applied |
| 008_create_notifications | create_notifications | ✅ Applied |
| 009_create_returns | create_returns | ✅ Applied |
| 010_payfast_methods | payfast_methods | ✅ Applied |
| 011_create_reviews | create_reviews | ✅ Applied |

---

## Current Environment

| Item | Value |
|------|-------|
| DB | Supabase PostgreSQL |
| DB connection | Port 6543 (connection pooler) |
| Redis | localhost:6379 |
| Backend | http://127.0.0.1:8000 |
| Frontend | http://localhost:3000 |
| Docs | http://127.0.0.1:8000/docs (loads in some browsers) |

---

## Test Users (seeded)

| Email | Password | Role |
|-------|----------|------|
| admin@drip.pk | Admin1234 | admin |
| customer@drip.pk | Test1234 | customer |
| seller@drip.pk | Test1234 | seller |

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
| Payment methods | PayFast + COD only |

---

## Current Session — Start Here

**Last completed:** Full backend + frontend built and running locally
**Backend status:** Running on http://127.0.0.1:8000 ✅
**Frontend status:** Running on http://localhost:3000 ✅
**DB status:** All 11 migrations applied ✅
**Next:** Run full test suite, production deploy to Railway + Vercel
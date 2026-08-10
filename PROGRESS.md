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
| 2 | Auth | 🔄 In Progress |
| 3 | Sellers & Slots | ❌ Not started |
| 4 | Products & Images | ❌ Not started |
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

- [x] `requirements.txt` — all pinned deps
- [x] `pyproject.toml` — pytest + ruff + mypy config
- [x] `Makefile` — all dev commands
- [x] `Dockerfile` — production API image (multi-stage)
- [x] `Dockerfile.worker` — ARQ worker image
- [x] `docker-compose.yml` — local Postgres + Redis + pgAdmin
- [x] `.env.example` — all env vars documented
- [x] `.gitignore`
- [x] `alembic.ini`
- [x] `alembic/env.py` — async-compatible
- [x] `app/core/config.py` — Pydantic Settings with validators
- [x] `app/core/logging.py` — structlog JSON + PII scrubber
- [x] `app/core/exceptions.py` — full exception hierarchy (30+ types)
- [x] `app/core/database.py` — async engine + session factory + get_db
- [x] `app/core/redis.py` — connection pool + key helpers + cache utils
- [x] `app/core/middleware.py` — security headers + request ID + logging + rate limit
- [x] `app/core/security.py` — Argon2id + RS256 JWT + refresh tokens + TOTP
- [x] `app/models/base.py` — Base + UUIDPrimaryKeyMixin + TimestampMixin + SoftDeleteMixin
- [x] `app/schemas/common.py` — pagination + error response + field validators
- [x] `app/repositories/base.py` — generic async CRUD (create/read/update/soft-delete/list)
- [x] `app/api/deps.py` — get_db + auth dependencies + role guards
- [x] `app/api/v1/health.py` — health check endpoint
- [x] `app/api/v1/router.py` — master router (stubs for future blocks)
- [x] `app/tasks/worker.py` — ARQ WorkerSettings stub
- [x] `main.py` — app factory + lifespan + middleware + exception handlers
- [x] `tests/conftest.py` — shared fixtures (test DB, client, auth headers)
- [x] All `__init__.py` files
- [x] **Verified:** `python -c "from app.core.config import Settings"` passes

---

## Block 2 — Auth 🔄

### Models
- [x] `app/models/user.py` — User · UserSession · UserAddress

### Repositories
- [ ] `app/repositories/user_repo.py` — UserRepository (get_by_email, create_session, etc.)

### Schemas
- [ ] `app/schemas/auth.py` — RegisterRequest · LoginRequest · AuthResponse · TokenResponse

### Services
- [ ] `app/services/auth_service.py` — register · login · refresh · logout · verify_email · reset_password · google_oauth

### Integrations
- [ ] `app/integrations/resend_client.py` — send_email wrapper + templates

### Tasks
- [ ] `app/tasks/email_tasks.py` — send_verification_email · send_password_reset_email

### Routes
- [ ] `app/api/v1/auth.py` — 12 endpoints (POST /register, /login, /refresh, /logout, /forgot-password, /reset-password, /verify-email, /google, /google/callback, /me, /change-password, /setup-2fa)

### Migration
- [ ] `alembic/versions/001_create_users.py` — users · user_sessions · user_addresses tables

### Tests
- [ ] `tests/unit/test_security.py` — hash/verify, JWT encode/decode, TOTP
- [ ] `tests/unit/test_auth_service.py` — register, login, refresh, logout flows
- [ ] `tests/integration/test_auth_api.py` — full HTTP flow tests
- [ ] `tests/security/test_auth_security.py` — rate limit, brute force, token revocation

---

## Block 3 — Sellers & Slots ❌

- [ ] `app/models/seller.py` — Seller · SellerWallet · SellerBankAccount · SellerVerification
- [ ] `app/repositories/seller_repo.py`
- [ ] `app/schemas/seller.py`
- [ ] `app/services/seller_service.py`
- [ ] `app/services/slot_service.py` — consume_slot · release_slot · purchase_extra_slots
- [ ] `app/api/v1/sellers.py`
- [ ] `alembic/versions/002_create_sellers.py`
- [ ] Tests

---

## Block 4 — Products & Images ❌

- [ ] `app/models/product.py` — Product · ProductVariant · ProductInventory · ProductImage · Category · Tag
- [ ] `app/repositories/product_repo.py`
- [ ] `app/repositories/inventory_repo.py`
- [ ] `app/schemas/product.py`
- [ ] `app/services/product_service.py`
- [ ] `app/services/image_service.py` — magic-byte validation + WebP conversion + Supabase upload
- [ ] `app/api/v1/products.py`
- [ ] `app/integrations/supabase_storage.py`
- [ ] `alembic/versions/003_create_products.py`
- [ ] Tests

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

- [ ] `app/models/wallet.py` — SellerWallet · WalletTransaction · CommissionLedger · Payout
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

## Current Session — Start Here

**Last completed:** Block 1 foundation verified ✅, Block 2 User model created
**Next to build:** Block 2 — user_repo → auth schemas → auth service → routes → migration → tests
# Backend walkthrough

Reviewed 11–12 October 2026. Backend only; no frontend source was inspected. Read this with [the findings](BACKEND_DEEP_REVIEW.md), [the repair queue](BACKEND_REPAIR_QUEUE.md) and [the source index](audit/README.md).

## Architecture

WearHowZ is a FastAPI modular monolith with a separate ARQ worker process. PostgreSQL stores durable business records; Redis holds temporary application state and the worker queue. Pydantic schemas define HTTP inputs/outputs, SQLAlchemy models describe persistence, and Alembic migrations evolve the deployed schema.

The usual request flow is `main.py → middleware → dependency/role checks → route → service → repository/SQLAlchemy → database → response schema`. External adapters handle PayFast, Google identity, Supabase Storage and Resend. Some routes/services issue SQL directly, so the layering is a convention rather than an enforced boundary.

### Entry points and infrastructure

- `main.py`: constructs the application, mounts routes, registers middleware/error handlers and starts/stops shared resources through its lifespan. Importing the app is not the same as executing startup.
- `app/api/deps.py`: validates bearer tokens, revocation, DB account state, email verification, role and auth version; defines user/seller/admin dependencies and ownership helpers. `CurrentUser` allows all authenticated roles, whereas `CurrentSeller` additionally requires an active seller.
- `app/core/config.py`: cached environment settings and selected validators. Local `.env` is excluded in test mode. Runtime commercial settings stored in the database are a separate policy mechanism.
- `app/core/database.py`: async engine/session factory, request sessions, worker access and transaction support. Services often commit themselves; callers must not assume nested service operations share one indivisible transaction.
- `app/core/redis.py`: Redis lifecycle, key/TTL and cache helpers. Redis is used for more than performance caching: losing security/queue state can have functional consequences.
- `app/core/security.py`: Argon2 passwords, RS256 tokens, opaque refresh-token hashing, revocation, email/reset audiences, TOTP and cookie configuration.
- `app/core/middleware.py`: request IDs, security headers, logging and rate limiting. Middleware runs before route authentication, which matters for identity-based throttling.
- `app/core/logging.py`: structured logging/redaction. `app/core/exceptions.py`: domain errors, status codes and error serialization. Direct HTTP exceptions do not all follow the custom envelope.

## Main business flows

### Authentication

Registration creates an unverified customer and the route dispatches verification email. Verification checks a specially scoped token, marks the email verified and creates a session. Login verifies password/email state and an enrolled admin's TOTP, then returns an access token and sets a refresh cookie. Only the refresh-token hash is stored. Refresh rotates the stored session credential; password changes and account state are checked against current DB state rather than trusting a signed token indefinitely.

Google sign-in uses state, nonce and PKCE. The callback consumes browser-bound Redis state, exchanges the code, validates signed identity claims, and creates an eligible customer session. Email equality does not automatically authorize linking an existing account. The redirect contains no access token; the browser obtains it through refresh. This is source behaviour, not proof of a live Google journey.

Guest order access uses a scoped bearer capability, not merely knowledge of an order number or email. `order_access.py` is shared by order/payment/return operations. Token expiry and recovery need an explicit product policy.

### Catalogue and stock

Seller → product → variant → inventory is the principal ownership chain. Product images/tags/categories support catalogue presentation. Visibility combines publication, moderation, deletion and seller state. Order items snapshot purchase descriptions/prices so later catalogue edits do not rewrite purchase history.

`ProductService` manages owned catalogue edits, visibility, variants and media; `ProductRepository` provides public filtering, sorting and cursors. `ImageService` validates/converts image data and delegates remote storage. Remote object writes and DB commits are not one transaction.

Inventory distinguishes physical stock from reserved units. Available stock is `stock - reserved`. Checkout reserves; shipping consumes; cancellation/expiry releases; confirmed return refunds credit returned units. A return request alone is not evidence that stock should be credited. Seller stock writes must preserve ownership and reservation constraints.

### Cart and checkout

The Redis cart stores variant quantities, not price guarantees or reservations. The service reads current product data to render it. Authenticated checkout reads that cart; guest checkout supplies/merges explicit items. The shared calculation checks availability, current prices, seller state and runtime shipping policy. A guest quote is read-only and is revalidated at order creation.

The order builder validates/locks a coupon if applicable, enforces payment availability and the COD cap, creates parent/address/item snapshots and seller sub-orders, distributes discounts, reserves stock and records usage. Durable DB commit and later Redis/cart/job operations are separate effects. Creating an order currently does not imply that its notification was queued.

### Payments and fulfilment

Parent order, seller order and payment statuses describe different facts. COD verification is not collection; delivery is not payment. Payment initiation authorizes order access, creates/reuses a local payment and returns COD or PayFast hosted-checkout details. A browser success redirect is not trusted proof of payment.

The callback handler verifies/parses provider data and records audit/state transitions. Reconciliation asks the provider about a missed callback. Mandatory amount/currency evidence needs repair before either path can be declared production-ready.

Sellers act on their own sub-orders through processing/shipped/delivered transitions. Shipping needs tracking information. Services coordinate stock changes and parent status aggregation. Cancellation/expiry use allowed states and reservation-release logic.

### Settlement and payouts

Commission settlement requires delivery and collected funds, creates one seller-order ledger, applies runtime commission and credits pending earnings. The scheduled release job later moves mature eligible earnings to available balance. Refund and dispute holds are currently incomplete; maturity alone is not sufficient for financial correctness.

Withdrawal validates the seller's bank account/amount and reserves available funds in a payout request. Approval, rejection and completion have distinct meanings; rejection restores funds and completion records a manual transfer receipt. No automatic bank transfer occurs merely because a payout status changes. The older admin completion route bypasses the stronger service and must be unified.

### Returns and disputes

Return requests verify order ownership/guest capability, seller-order identity, delivery and item quantities. Customer, seller and admin details expose different scoped views. Ordinary flow: requested → approved → received → refund requested → transfer confirmed. A pending refund reserves refundable capacity but does not claim money was sent.

Confirmation coordinates refund receipt, return status, stock credit, seller reversal and payment state. Request creation currently commits before linking the return; the later atomic confirmation does not fix that earlier gap. Rejected returns can be disputed, but favourable dispute resolution currently changes only the dispute and does not reopen the return workflow.

### Customer/admin/reporting

Customer operations cover profile/avatar/password, addresses, reviews/votes, wishlist/preferences and deletion. A review can be unverified; an optional order reference is checked to determine a verified-purchase badge. Normal review mutations refresh aggregates. Account deletion and eventual retention/purge need a coherent lifecycle.

Admin operations include onboarding/registration receipts, seller moderation, COD verification, orders, payouts, refunds, content and settings. Admin authorization is necessary but does not validate the internal financial transition.

Analytics aggregates ledgers/orders/catalogue and recorded server events. These are not complete browser-session conversion or marketing-attribution measurements. Refund-adjusted reporting and monetary precision must be reconciled with ledger semantics.

## File responsibilities

The linked index enumerates all 163 baseline Python files and 1,953 class/function definitions with source ranges, backend imports and syntactic calls. It is navigation, not a runtime call graph; source docstrings can be stale.

| Layer | Files and purpose |
| --- | --- |
| Routes | `auth`, `cart`, `orders`, `payments`, `products`, `storefront`, `sellers`, `inventory`, `wallet`, `customers`, `returns`, `notifications`, `health` expose their domain HTTP surfaces. `router.py` mounts them. Admin submodules split brand decisions, COD, content, dashboard, orders, payouts, reviews and settings; analytics submodules separate seller/admin reports. |
| Services | Domain-named services own the flows above. `slot_service` manages seller listing capacity and wallet-funded purchases; `coupon_service` eligibility/usage; `platform_settings` typed commercial policy; `revenue` shared aggregation queries; `order_access` owner/guest authorization; `google_oauth` external identity. |
| Repositories | `base` supplies generic persistence helpers. User/session, seller/wallet/bank, product/catalogue, inventory, order, payment/refund, wallet/ledger/payout, return/dispute and notification repositories provide specialized queries. A repository write does not substitute for authorization or a state machine. |
| Models | `user`, `seller`, `product`, `coupon`, `order`, `payment`, `wallet`, `return_`, `review`, `notification`, `admin`, `analytics` define durable concepts; `base` defines shared metadata/conventions. Foreign keys and checks enforce selected invariants, not an entire business workflow. |
| Schemas | Domain modules define input/output projections, pagination and validators; `common` provides shared helpers. Optional fields do not automatically determine whether null clears or ignores a value: service update logic decides. Decimal/int differences affect the public contract. |
| Integrations | PayFast handles checkout/callback/status protocol; Supabase handles object storage; Resend handles SDK calls/templates. A residual Stripe adapter exists but does not mean Stripe is an active supported checkout route. |
| Tasks | `worker` registers ARQ jobs/lifecycle/schedules; email and notification tasks wrap delivery; order tasks handle timeout/expiry; wallet tasks settle/release; cleanup handles expired state, archive, deletion and opt-in orphan storage cleanup. Registration alone does not dispatch a business event. |

## Configuration and deployment files

Settings groups cover API metadata/environment; CORS; DB pooling; Redis; JWT keys/lifetimes; Supabase buckets/cleanup gate; email sender; WhatsApp; commercial defaults; Sentry; PayFast merchant URLs/credentials/enablement/allowlists; Google credentials; guest capability lifetime; and public frontend/API URLs. Required/non-empty configuration is not evidence that a credential, domain or provider endpoint actually works. Public URL sources and duplicated schema/policy limits need consolidation.

`requirements.txt` declares runtime packages; `requirements-dev.txt` test tooling. `pyproject.toml` configures pytest, the unchanged 85% gate, lint and type-check policy. Dockerfiles build API/worker images; development Compose is not a hardened deployment template. `compose.test.yml` uses separate loopback ports and disposable PostgreSQL/Redis. `Makefile` supplies command shortcuts. Ignore files govern repository/image inclusion, not secret revocation. `.env.example` is a template; secret values and private key files were excluded from review output.

`fix_migration.py` is a guarded migration utility; `seed_users.py` explicitly seeds users without overwriting existing credentials/roles. Scripts export contracts, package reviewed source and perform explicitly configured connected-service checks. Provider probes can have external effects and were not run against live accounts.

## Migration sequence

001 introduces users/sessions/addresses; 002 sellers/wallets/banks; 003 catalogue/inventory; 004 coupons/orders/sub-orders/history; 005 payments/callbacks/refunds; 006 payouts/commission/wallet transactions; 007 settings/banners; 008 notifications/preferences/email logs; 009 returns/disputes and the refund return FK; 010 PayFast enum support; 011 reviews; 012 accumulated marketplace/auth/payment/ledger repairs; 013 notification archive/read fields; 014 refund-request audit; 015 guest-return ownership.

`alembic/env.py` supports normal migration execution and a supplied test connection. Old enum labels can remain for compatibility. A successful empty-schema downgrade/upgrade is not proof that production historical data survives the same operation. Model-created test tables and migrated tables should be compared for constraints/defaults/indexes, not just readable columns.

## Tests and evidence

The test source was reviewed across unit, HTTP smoke, database regression, B4/dispute, native concurrency/migrations, worker and load modules. Unit tests generally exercise schemas, pure calculations and mocked boundaries. Several HTTP smoke modules also mock the DB and accept broad status sets, sometimes including 500; they cannot certify the complete named feature.

Stronger tests in marketplace regressions, release journeys, B4 and dispute authorization use persisted state and explicit ownership/amount assertions. Native tests use separate committed sessions for selected races and execute migrations. Real Redis worker tests check retries/result persistence on a dedicated DB/queue. These are valuable but do not cover every mixed-operation race or money-conservation invariant.

The legacy security module unconditionally skips itself. The Locust script has stale paths/filters and default users cannot pass current verification/approval flows; it also labels expected 404 reads successful and does not implement the checkout activity described in its docstring. No load traffic was generated by this audit.

See the findings and repair queue for fresh results and limitations. Historical README/progress/task reports and saved test/advisory artifacts describe their own snapshots, not proof of current release readiness. No review can guarantee absence of all defects; this is a completed static risk review, not a per-line teaching transcript or production sign-off.

# Backend release limitations

Updated 19 October 2026. Passing coverage is not production approval.

The user-supplied 162-item pre-ship checklist audit is still in progress; see
[current tracking and verification](docs/PRE_SHIP_AUDIT.md). Proxy/cursor/startup and
seller-moderation repairs do not close the remaining payment, privacy, dependency,
worker-recovery and deployment gates.

## Release blockers

- **Legacy test quality:** checkpoint 20 replaces 11 payment smoke cases with 43
  native HTTP cases, validating guest/account access, admin permissions, exact
  fractional amounts and pending-refund behavior. Checkpoint 18 replaces product smoke tests accepting
  500 or conflating 401/422 with 29 native cases using exact statuses, error fields,
  real seller authentication, positive controls and rejected-write snapshots.
  No application behavior changed. These tests require disposable PostgreSQL;
  skipping them without TEST_DATABASE_URL is not validation. Other legacy API
  smoke files remain open. See
  [checkpoint 20](docs/PRE_SHIP_CHECKPOINT_20.md) and
  [checkpoint 18](docs/PRE_SHIP_CHECKPOINT_18.md).

- **Dependency reproducibility:** checkpoint 2 upgrades affected dependencies and
  replaces python-jose/ecdsa with pinned PyJWT RS256 verification. The new installed-
  environment scan reports zero known vulnerabilities; see
  `docs/audit/preship2-dependency-audit-2026-10-14.json`. The earlier 45-advisory report
  is historical. This is not a security guarantee or a complete hashed transitive
  dependency lock, and a clean Linux release-image validation remains outstanding.
- **Historical money:** no real historical settlement records or transfer receipts
  were supplied. Legacy release protection remains unchanged. Follow SETUP.md before
  reopening any historical pending balance. Local synthetic races do not reconcile
  a merchant's real books or approve platform absorption of refund shortfalls.
- **Live provider acceptance remains gated:** PayFast now follows the published hosted
  checkout/token/callback adapter. Callback success now requires authoritative status
  verification of identifiers and explicit matching amount/currency; local regressions
  reject missing/conflicting evidence, provider errors and mismatched transactions.
  Merchant endpoint access and actual response-field mapping still require UAT. Google, Supabase,
  Resend and worker flows have local signed/mocked coverage. These checks do not prove
  merchant-specific endpoints, source IPs, real Google consent, Supabase permissions or
  Resend delivery. Keep PayFast and Supabase orphan deletion disabled until the staging
  checklists pass. No real charge, email or upload was performed in this review.

## Verification boundaries and technical debt

- **Deletion is not universal erasure:** customer self-deletion now blocks privileged
  roles, missing password reauthentication, active orders, open returns/disputes and
  pending refunds. Profile credentials, names, phone, avatar reference, sessions and
  saved addresses are removed; financial identity and order records remain. Checkpoint 4
  also clears notifications/preferences/review free text and image references, and
  persists retryable cache/safe-image cleanup. Deletion versus new returns, disputes and
  refresh sessions now shares an account lock and has native race tests. Unverifiable
  or shared assets require manual review. Checkpoint 5 adds send-time identity and
  opt-out checks to legacy email jobs, plus zero ARQ result retention. Historical
  records, pending/old queue payloads, backups, consent versions, final retention
  periods and seller/admin offboarding remain
  open. See [customer privacy](docs/CUSTOMER_PRIVACY.md). No production cleanup was run.
- **Checkpoint 3:** durable notification completion/recovery, bounded failed queues,
  audited admin replay, one-time legacy preference import and full 42-table migrated
  schema comparison are now implemented with local tests. All 190 API operations are
  classified by a reviewed route policy; protected-route identity/role denials are
  exercised through HTTP. This is not exhaustive owner-versus-other-user testing of
  every business operation; existing targeted ownership regressions remain separate.
- **Audit still open:** exhaustive resource-level ownership cases, mixed-operation
  races, money presentation/configuration consistency, static/type debt, reproducible
  dependency locking and remaining checklist evidence still require work. Notification
  alert delivery and uncertain provider email outcomes still require staging acceptance.

- **Ownership expansion:** checkpoint 4 adds real two-customer/two-seller HTTP tests
  covering foreign resource IDs, nested product/image/variant IDs, private lists,
  bank-account withdrawal ownership, profile/preferences/cart/wishlist isolation and
  wallet history. Denied mutations compare stored rows before/after. These tests add
  concrete evidence, not a claim that every possible input/interleaving is tested.
  Checkpoint 6 additionally tests all four seller analytics routes and low-stock lists
  with distinct two-seller data, period/grouping/sort/filter combinations and stale
  seller-ID claims. Dashboard low-stock classification now uses persisted reorder
  points; active/in-stock/out-of-stock population semantics remain unchanged.

- **Admin bulk stock:** checkpoint 7 repairs false success counts after a database
  row error. Per-row savepoints, unique/bounded input and consistent bulk lock order
  preserve valid corrections and reservations. Fatal errors return no success result.
  This does not add durable request IDs, a permanent correction/reason audit trail,
  or certify every mixed-operation race. A lost commit acknowledgement can still
  require reading stored stock before deciding whether to retry an absolute correction.

- **Analytics money:** checkpoint 8 preserves fractions in all eight money-bearing
  analytics routes. Their 16 money fields now return decimal strings in PKR units;
  integer-only clients must update. Refund-adjusted ledger reports and order snapshot
  reports still have different bases. Platform averages still divide qualifying GMV
  by all period orders; city shares cover the returned subset. Remaining legacy/untyped
  money contracts remain open
  under F16. See [the contract notes](docs/PRE_SHIP_CHECKPOINT_8.md).

- **Slot/notification presentation:** checkpoint 10 makes five slot money fields
  JSON decimal strings and preserves fractions in order/payout notices and legacy
  order-email rendering. Slot settings still accept whole PKR; no pricing or wallet
  accounting policy changed. Clients must update slot money types. Existing stored
  notices, sent emails and old truncated queue values are not repaired/resubmitted.
  Providers remain mocked in local tests. See [checkpoint 10](docs/PRE_SHIP_CHECKPOINT_10.md).

- **Catalogue/wishlist prices:** checkpoint 11 removes integer truncation from
  product cards/details, variants, suggestions, seller listings and wishlists.
  Their seven underlying price/sale-price fields now return two-decimal PKR strings;
  clients must update response types. Existing whole-rupee product/variant entry and
  filter policies are unchanged. Product-level cards/suggestions do not override
  selected-variant pricing; checkout still revalidates current prices and stock.
  Remaining legacy/untyped money shapes are not certified by this change. See
  [checkpoint 11](docs/PRE_SHIP_CHECKPOINT_11.md) for verification status and scope.

- **Canonical public links:** checkpoint 12 separates customer link destinations
  from browser CORS origins and normalizes auth, tracking, seller, Google and PayFast
  app URLs. Existing routes are retained. Root origins, HTTPS in production and
  `/api/v1` are now validated; subpath hosting/custom API prefixes are unsupported.
  Existing sent emails and stored notification HTML are not rewritten. Domain
  ownership, DNS/TLS, deployed frontend routes and merchant/Google-console settings
  still require acceptance; this does not validate all legacy caller-supplied URLs
  or all email-template escaping. See [checkpoint 12](docs/PRE_SHIP_CHECKPOINT_12.md).

- **Error-response compatibility:** checkpoint 13 replaces direct HTTP/router
  `detail` responses with the existing `error` envelope. Clients must read
  `error.message`/`error.code`; domain codes and statuses are retained. Common errors
  now use no-store, and pre-response unexpected failures keep outer headers.
  Readiness health, CORS preflight, bodyless HTTP statuses, proxy/outer-middleware
  failures and post-start streaming/background errors have documented boundaries.
  This is not a universal input/message-privacy or live monitoring sign-off. See
  [checkpoint 13](docs/PRE_SHIP_CHECKPOINT_13.md) for contract and verification status.

- **Seller-order read contracts:** checkpoint 14 replaces untyped list/detail
  responses with schemas matching the existing payload. Seller subtotal and item
  unit_price/subtotal are exact two-decimal PKR strings; timestamps, nullable address
  fallback and pagination fields are preserved. No ledger or fulfilment rule changed.
  Old placeholder fields are not newly promised. Dormant legacy analytics classes
  are not evidence of a live truncation bug. See [checkpoint 14](docs/PRE_SHIP_CHECKPOINT_14.md).

- **Admin product contract:** checkpoint 15 types the existing seven row fields
  and page/per_page/total pagination. Price is the base product price serialized as
  a two-decimal PKR string, not sale/variant/checkout pricing. Admin-only access,
  seller/hidden filters, drafts and hidden visibility, soft-delete exclusion and
  ordering are unchanged. Clients must consume the documented string type.
  This is scoped validation, not a fresh full-suite or universal schema sign-off;
  broader contract parity remains open. See [checkpoint 15](docs/PRE_SHIP_CHECKPOINT_15.md).

- **Withdrawal limit configuration:** checkpoint 16 removes the hardcoded schema
  bounds and service minimum in favor of validated startup settings, and adds the
  service maximum guard. Defaults remain inclusive PKR 500–200,000, with two-decimal
  withdrawal amounts. This is not a new runtime admin setting or changed payout
  accounting policy. Restart API/workers together for configuration changes.
  See [checkpoint 16](docs/PRE_SHIP_CHECKPOINT_16.md).

- **Catalogue/media limits:** checkpoint 17 shares fixed price/image-count/upload-byte
  constants across existing enforcement points. Current values, whole-PKR request
  policy, sale-price rules, zero catalogue minimum filter and API contracts are
  unchanged. Database price constraints remain independently enforced and tested;
  changing policy requires migration review. This does not newly certify upload
  concurrency, image-decoder resource safety or external-storage cleanup. See
  [checkpoint 17](docs/PRE_SHIP_CHECKPOINT_17.md).

- **Coupon money:** checkpoint 9 preserves fractional preview values/minimums,
  rounds discounts explicitly and bounds multi-seller allocations. Preview remains
  an estimate; checkout rechecks current prices and usage eligibility. Existing
  historical seller allocations are not automatically repaired. Zero-total orders
  with free shipping remain outside this verification; orders still require total
  > 0. The legacy apply helper is not newly certified for concurrent usage. See
  [checkpoint 9](docs/PRE_SHIP_CHECKPOINT_9.md) for tests and contract details.

- Post-review repair batches 1 through 4 fix payout-transition integrity, atomic
  return-refund linkage, wallet audit balances, seller-specific refund allocation,
  finite ledger holds/releases, refund-adjusted reporting and customer-won dispute
  continuation. A favourable dispute decision approves the return only after locked
  quantity revalidation; it does not claim receipt or transfer money. The retained policy
  makes the platform absorb refunded shipping, reversed platform commission and any
  seller-funds shortfall; it does not create recoverable seller debt. Historical
  refunds without revision-016 allocation remain quarantined. See
  `docs/BACKEND_B1_REPORT.md`, `docs/BACKEND_B2_REPORT.md`,
  `docs/BACKEND_B3_REPORT.md`, `docs/BACKEND_B4_REPORT.md` and the repair queue.

- The Task 7 dispute-message ownership finding is fixed in this working tree.
  Only the return owner can use the customer reply route; non-owner sellers and
  admins have no bypass. Eighteen new API/PostgreSQL regression cases are part of
  the passing focused suite. B4 later adds a separate admin-only detail/reply path
  with dispute-row locking against resolution races. Seller dispute replies remain
  unsupported. See [the Task 7 review](docs/TASK_7_DESIGN_REVIEW.md).
- Guest checkout now has a public, read-only quote contract for current item prices,
  stock, runtime shipping, totals and payment availability. It intentionally creates
  no reservation and is not a guaranteed future price; order creation revalidates all
  values. Guest coupons still require authentication.
- Admin refund queue/detail/payment-history reads now expose pending, completed,
  reserved and remaining amounts. Revision 014 separates requester from confirmer for
  new records. Older completed rows are backfilled from the prior single actor field,
  so their `requested_by` value is best-effort and may identify the confirmer.
- Admin return detail exposes authorized item/order/customer/seller context,
  discount-prorated estimated refund value, linked refund/dispute state and allowed
  lifecycle actions. Sellers can list, inspect, approve, reject and acknowledge receipt
  only for their own brand returns; refund request/confirmation remains admin-only.
- Admin dispute detail and replies are available without weakening the owner-only
  customer route. Guest cancellation and return creation/detail require the signed
  capability token for the exact order; matching an email never grants access. Guest
  disputes remain unsupported because the dispute model requires an account owner.
- Native PostgreSQL tests exercise competing reservations, withdrawal requests,
  settlement/release, refund confirmation, signed payment callbacks and expiry
  sweeps. They are controlled two-contender regressions, not a load test or proof of
  every interleaving, crash/restart or distributed failure mode.
- Revision 017 provides a transactional notification outbox, deterministic ARQ job IDs,
  keyed in-app/email delivery and retryable failed email logs. Native tests force queue
  and provider failure/recovery without sending a real message. This gives local
  idempotency, not a provider-level exactly-once guarantee: the installed Resend client
  exposes no idempotency key, so a connection loss after provider acceptance but before
  receipt persistence can still produce an external duplicate. Staging must verify the
  minute publisher schedule, crash recovery, sender/domain and real delivery behavior.
- Customer and notification preference endpoints now share the database record. Routine
  registered order email/push and payout notices honor their toggles. Order placement,
  guest lifecycle messages and seller decisions are required transactional notices.
  Promotion/new-arrival, SMS and WhatsApp preferences are persisted but this batch does
  not add those delivery providers. Admin broadcasts remain in-app announcements.
- Guest notification links carry a signed order-scoped token in the query string so a
  future frontend can send the existing `X-Guest-Token` API header. The frontend must
  avoid logging the token, apply a restrictive referrer policy and remove it from the
  visible URL after capture. Forged and cross-order capabilities are rejected.
- Checkpoint 19 replaces the inherited security module with 47 active cases using
  generated tokens, real account rows, throttle thresholds and callback rejection.
  Execution requires the shared disposable database fixture; collection has no
  unconditional skip. This does not establish comprehensive penetration testing.
  The one security skip in checkpoint 14's full-suite result is historical, not counted
  as passing security coverage.
- PayFast forwarding headers are accepted only from configured trusted proxies. The
  actual proxy and PayFast callback IP/CIDR lists remain deployment-specific and must be
  confirmed before enabling the gateway.
- Health returns HTTP 503 on a failed database/Redis probe and 200 when healthy,
  as verified in checkpoint 2. Separate process-only liveness and actual deployment
  routing/draining behavior remain unverified.
- Repository-wide Ruff has a substantial inherited backlog. Targeted formatting
  does not establish a clean lint gate. Strict typing is configured but mypy is not
  part of the checked-in development requirements; a clean type-check result has
  not been established.
- Prior migration testing used a fresh isolated schema and a 016 → 012 → 016 round trip.
  Batch 4 additionally passed a fresh upgrade through 017 and a 017 → 016 → 017 round trip.
  These checks used an empty disposable database, not a populated production backup.
  Deeper rollback drops notification delivery/audit data, refund accounting/allocation
  tables and the refund requester audit field. Revision 015 cannot downgrade while
  guest-return rows with null user ownership remain; reconcile them explicitly rather
  than deleting them silently.
- API/worker image build success alone does not prove deployment, health, secrets,
  network policy, scheduled delivery, backup/restore or operational monitoring.

The release evidence above covers backend Tasks 3, 4 and 6. Task 7 has begun
as a Canva/API review with user-approved B1–B4 backend fixes. Asset extraction and
full visual/interaction design review remain outstanding.
No frontend application implementation, Canva edits or publishing was performed.

# WearHowZ backend source review

Review dates: 11–12 October 2026. Scope: `drip-backend` only. This is a review, not a repair or release approval. See the [walkthrough](BACKEND_WALKTHROUGH.md), [definition index](audit/README.md) and [prioritized repair queue](BACKEND_REPAIR_QUEUE.md).

## Bottom line

Historical baseline below. Subsequent repairs and current remaining boundaries are
tracked in [the pre-ship audit](PRE_SHIP_AUDIT.md); checkpoint 8 partially repairs F16
with exact Decimal analytics and documented response-type changes. Checkpoint 7's
bulk-stock integrity and checkpoint 6's seller isolation/reorder repairs remain in place.

The backend has substantial working functionality and useful regression tests, but it is **not complete except for production configuration**. Financial workflow, notification, account-lifecycle and validation gaps remain in application code. The highest-priority issues are listed below with source locations, consequences and proposed verification.

The review itself changed no application logic, development/production data, provider configuration or frontend source. Backend repair batches 1 through 3 were subsequently implemented on 12–13 October and are recorded below and in their source supplements. Runtime checks used disposable local test services and synthetic data. New review documents are separate from historical release reports.

## What was actually reviewed and verified

The pre-repair tracked backend baseline contains 189 files, including 163 Python files and 29,590 Python source lines. Application layers, routes, services, repositories, schemas, models, integrations, tasks, migrations and operational entry points were read. The remaining unit, HTTP smoke, persisted-state, B4/dispute, native, worker and load-test source was reviewed on 12 October. All 163 baseline Python files and 1,953 class/function definitions were indexed without source drift. Batch-specific [batch-1](audit/b1-changes.md) and [batch-2](audit/b2-changes.md) supplements supersede affected baseline entries. Generated symbol indexes are navigation aids, not evidence of correctness.

The static source/test risk review is complete. This is **not** a literal teaching transcript explaining every source line, an assurance that no defects remain, or production approval. The walkthrough explains the application and its connections; the index locates individual definitions. Native runtime results and external limitations must be considered separately.

Fresh checks in this review:

| Check | Observed result | Limit |
| --- | --- | --- |
| Unit suite | 347 passed, 27 warnings | Unit evidence alone does not validate persisted workflows |
| Full suite, native services enabled | 602 passed, 1 skipped, 501 warnings; exit 0 in 730.50 seconds | The legacy security module is unconditionally skipped; broad smoke assertions remain |
| Full-run coverage | 7,339 / 8,575 statements, 85.586% | Passing the unchanged 85% gate does not establish correctness of unasserted invariants |
| Fatal-error Ruff selection | Passed | Not a clean full lint/type-check claim |
| Full Ruff / type tooling | 1,018 Ruff findings; Mypy not installed | Mostly style/import/annotation findings; no strict type-check result |
| Dependency consistency | `pip check` passed | Not a fresh vulnerability/advisory scan |
| Offline OpenAPI comparison | Current and saved schema equal; 185 documented operations | Does not exercise HTTP behaviour; hidden routes are excluded |
| Model metadata | 39 tables | Model metadata alone does not prove migrated constraint parity |
| Existing native checks | All 10 native tests and both Redis retry cases passed, included in the full suite | Selected races only; not all mixed-operation histories |
| Migrations | Fresh upgrade through 015, downgrade to 012, upgrade to 015; all 39 model tables readable | Disposable empty schema, not a production-data migration rehearsal or complete constraint comparison |
| Native financial probes | F01-F05 reproduced on PostgreSQL 15 | Synthetic service/ORM fixtures, not live bank/provider journeys; see [probe evidence](audit/native-probes-2026-10-12.json) |
| ORM refund-debit probe | Incorrect transaction balance reproduced on SQLite and PostgreSQL | Not proof of every concurrent refund scenario |
| Catalogue cursor probes | Unhandled `AttributeError` and `decimal.InvalidOperation` reproduced | Service/repository boundary, not full HTTP server |
| Forwarded-IP probe | Same peer selects different rate-limit identities by changing header | Exploitability depends on ingress header handling |
| Native test services | Dedicated PostgreSQL 15 / Redis 7 containers started on 12 October | Separate project, loopback ports and synthetic data; development Redis untouched |
| Live providers | Not exercised | No real charges, email sends, uploads or Google sign-ins |

Commands, from the backend directory:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit -o addopts= --no-cov -p no:cacheprovider -q --tb=short
.\.venv\Scripts\python.exe -m ruff check app main.py scripts --select E9,F63,F7,F82 --output-format concise
docker compose -p wearhowz-review-20261012 -f compose.test.yml up -d --wait --pull never
$env:TEST_DATABASE_URL = 'postgresql+asyncpg://test:test@127.0.0.1:55432/wearhowz_test'
$env:TEST_REDIS_URL = 'redis://127.0.0.1:56379/15'
$env:PAYFAST_ENABLED = 'false'
$env:GOOGLE_CLIENT_ID = ''
$env:GOOGLE_CLIENT_SECRET = ''
$auditResults = Join-Path ([System.IO.Path]::GetTempPath()) ('wearhowz-review-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $auditResults | Out-Null
$env:COVERAGE_FILE = Join-Path $auditResults '.coverage'
.\.venv\Scripts\python.exe -m pytest tests -o addopts= --strict-markers --tb=short --cov=app --cov-report=term --cov-fail-under=85 --junitxml="$auditResults\pytest.xml" -p no:cacheprovider -q
```

Docker was unavailable during the initial check on 11 October, but available on 12 October. This review then created its own `wearhowz-review-20261012` Compose project using the existing disposable test configuration and locally available images. It did not use or stop the development `drip_redis` container. Test imports used the repository's isolated test settings and ephemeral signing keys, not local `.env` values. Coverage and JUnit artifacts were directed to a temporary review directory; existing repository coverage artifacts were not overwritten.

The final run's JUnit record confirms 603 cases, zero failures/errors and one skip. [Structured verification](audit/verification-2026-10-12.json) records this review's results separately from historical release snapshots. Passing tests coexist with the reproduced defects: the missing invariants need new regression assertions before fixes can be signed off.

After verification, `docker compose -p wearhowz-review-20261012 -f compose.test.yml down` removed only this review's two disposable containers and network, discarding their synthetic test data. The existing `drip_redis` container remained healthy. Temporary test-result artifacts were retained.

## High-priority code findings

### F01 — Legacy payout completion bypasses the payout state machine

**Resolved in backend batch 1 (12 October 2026).** The compatibility route now requires a transfer reference and delegates to the same locked `WalletService.admin_complete_payout` transition as the newer route. The legacy listing preserves Decimal amounts and exposes the stored receipt. Native regression coverage rejects requested/rejected completion, verifies replay/conflict behavior, and races completion against rejection.

Source: `app/api/v1/admin/payouts.py:66`; compare `WalletService.admin_complete_payout` in `app/services/wallet_service.py`.

The legacy `/admin/payouts/{id}/complete` route fetches a payout and directly writes `completed`. It does not delegate to the service that requires approval, locks the record and checks receipt/idempotency. Its optional `payment_reference` input is ignored. Both this router and the newer wallet router are mounted.

An authorized admin can consequently complete a rejected payout whose reserved funds were already restored, or complete a requested payout without approval or a persisted transfer receipt. This is an internal workflow bypass, not unauthenticated access. The legacy list also casts amounts to integers and omits the stored receipt. Native PostgreSQL reproduction on 12 October: withdraw PKR 500 from PKR 1,000, reject it, then invoke the legacy completion route function; status becomes `completed`, available balance remains PKR 1,000 and `transfer_reference` is null despite supplying `payment_reference`.

Recommended repair: make both routes use one transition service and one receipt contract. Test every route against requested, approved, completed and rejected states, including concurrent rejection/completion and conflicting receipt replays.

### F02 — Return-linked refund creation is not atomic

**Resolved in backend batch 1 (12 October 2026).** `PaymentService.refund` now accepts the return association and caller-owned commit policy. `ReturnService.process_refund` creates/links the refund while both locks remain held and performs one outer commit. Failure injection after the refund flush followed by rollback leaves no refund row; retry produces one linked request.

Source: `app/services/return_service.py:444`, particularly lines 462–467; `app/services/payment_service.py:365`, particularly lines 391–401.

`process_refund` calls `PaymentService.refund`, which commits a new refund with no return link. Only after that commit does the caller attach `return_id` and commit again. The first commit also releases the caller's return lock.

A crash or concurrent confirmation in that interval exposes a refund as a direct order-wide refund. Confirmation can then allocate the reversal across brands and omit return-specific stock credit/status updates. Request idempotency does not make these two commits atomic. Native failure injection immediately after the inner refund commit, followed by rollback of the caller, left a persisted pending refund with `return_id=None`.

Recommended repair: create the refund with its return association in a single caller-owned transaction. Add failure-injection at the old commit boundary and a concurrent request/confirmation test that asserts seller allocation and exactly-once stock credit.

### F03 — Refund wallet audit balance subtracts the debit twice

**Resolved in backend batch 1 (12 October 2026).** `_apply_debit` captures pending and available balances before the SQL update and derives the combined post-transaction balance from those snapshots. Native cases cover pending-only, available-only, mixed balances and a seller-funds shortfall.

Source: `app/services/commission_service.py`, `_apply_debit`.

The SQLAlchemy ORM update synchronizes the loaded wallet instance. The subsequent `balance_after` calculation subtracts the same pending/available deltas again. A focused in-memory ORM probe produced:

| Starting pending | Debit | Actual final pending | Recorded `balance_after` |
| --- | --- | --- | --- |
| PKR 1,000 | PKR 100 | PKR 900 | PKR 800 |

The underlying wallet was debited once; this finding concerns incorrect financial history, not a second actual withdrawal. A second reproduction using native PostgreSQL and production-style session settings began with PKR 2,040 pending, reversed PKR 1,020, and produced an actual pending balance of PKR 1,020 but an audit balance of PKR 0. Existing refund regression tests assert wallet balances and transaction amounts but do not assert this audit balance (`tests/integration/test_marketplace_regressions.py:1392`).

Recommended repair: use a refreshed/returned balance or a captured pre-update value, with one clear meaning for `balance_after`. Test pending-only, available-only, mixed-balance and shortfall cases using real ORM updates rather than mocked wallet objects.

### F04 — Partial refunds indefinitely block settlement release; open disputes are not actually checked

**Resolved in backend batch 2 (13 October 2026).** The scheduled worker delegates to a ledger-level release scanner. It releases only `net_seller_amount`, checks real return/dispute states, and does not let one seller's refund freeze another seller's ledger. Requested/approved/received returns and open/under-review/customer-won disputes remain held; a rejected return with a seller-win terminal dispute can release. Historical confirmed refunds without revision-016 accounting remain quarantined.

Source: `app/tasks/wallet_tasks.py:33`, especially the refund lookup and `continue` at lines 54–56.

The release worker skips a ledger whenever *any* refund exists on its parent order. This includes completed partial refunds and refunds belonging to another seller. It never subtracts accounted-for reversals from the releasable ledger amount, and there is no implemented reconciliation transition that clears this condition for new refunds.

Separately, the comment says disputed orders are held, but the query checks `Refund`, not open returns/disputes. An open dispute without a refund does not meet this hold condition. Native reproduction after completing a partial refund and ageing its ledger ten days left PKR 1,020 pending, PKR 0 available and no release timestamp after running the release worker.

Recommended repair: model seller/ledger-level remaining entitlement and explicit hold reasons. Keep historical revision-012 balances quarantined until separately reconciled. Test partial/full refund, another seller's refund, open dispute, resolved dispute and eventual release of the correct remainder.

### F05 — Pre-settlement refund allocation can debit an unrelated brand

**Resolved in backend batch 2 (13 October 2026).** Revision 016 persists deterministic allocations by refund and seller order. Return-linked refunds allocate only to the linked seller order; direct refunds split against remaining merchandise capacity with a final residual owner. The same pending allocation is consumed as a settlement offset if collection occurs later, so another brand's settlement is unchanged.

Source: `app/services/commission_service.py:66`.

`settle` sums every confirmed refund on the payment and prorates that sum across all seller subtotals. It does not inspect a refund's return association. Example: brands A and B each sell PKR 1,000; A has a return-linked PKR 500 refund; B is delivered/settled later. B's gross is reduced by PKR 250 even though B had no returned goods. A's already-settled ledger may already have borne its own reversal.

Native PostgreSQL reproduction on 12 October used two PKR 2,400 seller orders. After brand A's PKR 1,200 return was confirmed, later settlement of brand B recorded gross PKR 1,800 and seller earnings PKR 1,530, despite brand B having no returned goods. The expected unaffected gross was PKR 2,400 (seller earnings PKR 2,040 under that fixture's commission rate). The synthetic fixture created the second seller order directly; allocation and settlement used the real service and database.

Recommended repair: persist allocation per refund and seller order, and consume the same allocation in both pre- and post-settlement accounting. Test staggered deliveries and refunds across brands, not just two already-settled sellers with a direct proportional refund.

### F06 — Refund accounting does not produce a complete net ledger

**Resolved in backend batch 2 (13 October 2026).** The ledger retains original amounts and records refunded gross, reversed commission/seller entitlement, actual recovered funds, pre-settlement offsets and platform shortfall. Refund accounting separately stores merchandise and shipping and enforces seller/platform conservation with database checks. Seller/admin/analytics aggregates use net values, while API responses expose original and reconciliation fields.

Source: `CommissionService._reverse_one`, `_reverse_across_order`, `_apply_debit`; `app/services/analytics_service.py`; `app/models/wallet.py`.

Reversal creates a seller-wallet debit but leaves original commission-ledger amounts and cumulative earned/commission counters unchanged. Analytics reading those values therefore report original settlement amounts rather than refund-adjusted results. Preserving immutable original entries is reasonable only if compensating entries are included in net reporting; that reconciliation is absent here.

Shortfalls are logged as the full *intended* debit, without separate structured fields for actual collection and platform loss. Direct refund allocation also applies the entire payment refund to merchandise proportions, without an explicit shipping allocation or final-seller rounding residual. These need a documented accounting policy, not an assumed formula change.

Recommended repair: distinguish original gross, seller reversal, platform commission reversal, shipping component, actual recovery and platform-funded shortfall. Add conservation-of-money assertions for fractional PKR amounts and partially paid-out funds.

### F07 — Successful dispute resolution does not reconnect the return workflow

**Resolved in backend batch 3 (13 October 2026).** A customer-win now locks the rejected return and its seller order, revalidates every claimed item against other non-rejected returns, and atomically changes the return to `approved` with the dispute resolution. A seller-win leaves it rejected. Receipt, refund request and transfer confirmation remain separate explicit transitions; resolution creates none of them. A native race proves a customer-win and a competing claim cannot both own the same purchased quantity.

Current repair source: `app/services/return_service.py:509` and `:568`. The original finding concerned the former dispute resolution and return-transition methods.

A customer opens a dispute on a rejected return. Resolving it in the customer's favour changes the dispute only; the return stays rejected. Approval requires `requested`, receipt requires `approved`, and refund requires `received`. There is no implemented admin transition that lets the favourable decision proceed through the existing return/refund flow.

Recommended repair: define the appropriate reopening/approval transition, with quantity revalidation because rejected returns no longer reserve returnable quantity. A favourable decision must not automatically claim that money was transferred. Test the complete reject → dispute → favourable resolution → receive → request refund → confirm transfer journey.

### F08 — Payment reconciliation does not verify amount and currency

14 October update: local fail-closed verification implemented and regression-tested;
see [checkpoint 2](PRE_SHIP_CHECKPOINT_2.md). Merchant response mapping/UAT remains
gated. The following text records the original finding, not current implementation.

Source: `app/services/payment_service.py:251`.

Reconciliation matches basket and transaction identifiers, then treats several provider statuses as success. It does not compare authoritative provider amount/currency with the stored payment before setting `completed`. The callback path has an amount comparison only when an amount is supplied, so missing-value handling also needs protocol-level validation.

The provider documentation URL returned HTTP 403 during this review. Therefore this report does not certify provider field names, signature coverage or endpoint behaviour. `PAYFAST_ENABLED=False` is an important safeguard, not proof the integration is ready after merely entering keys.

Recommended repair: obtain the merchant-specific response contract and require verified amount/currency evidence before crediting payment, with a fail-closed/manual-review outcome when absent. Test missing, wrong, replayed and mismatched values through callback and reconciliation separately.

## Other actionable code findings

### F09 — Important notifications have workers but no business-event dispatch

Source: `app/tasks/worker.py`, `app/services/notification_service.py`, and `enqueue_job` call sites under `app`.

Order confirmation/status, payout and seller-decision worker functions are registered, but their corresponding business services do not enqueue them. Existing dispatches cover verification/reset email, COD timeout, broadcast and a settlement helper. Calling task functions directly in tests does not prove a checkout or payout produces a job.

Additionally, `NotificationService.send_email` catches delivery errors, logs them and returns `None`; its notification callers do not raise on that result. ARQ sees a successful task, so this path does not retry failed delivery like the separate email task wrappers do. Customer preferences use a Redis `notif_prefs` path while notification preferences use DB rows with different fields; event delivery does not consult these settings consistently. The release-journey test sets `order_updates_push=False` but still expects the order notifications, so it does not establish opt-out enforcement.

Recommended repair: transaction-safe event delivery with deduplication (for example an outbox), consistent retry signalling, and tests beginning at real business actions and ending at queue/delivery assertions. Do not send real customer messages during tests.

### F10 — Rate limiting trusts arbitrary forwarding headers

Source: `app/core/middleware.py:205`; logging counterpart at `:115`; `app/api/v1/auth.py:413`.

Changing `X-Forwarded-For` changes the rate-limit identifier for the same direct peer. Unlike the payment callback's proxy handling, this logic does not establish a trusted peer first. Whether public clients can exploit it depends on the deployment proxy overwriting/filtering that header.

The user-based branch also depends on request state that is not populated by the authentication dependency; middleware runs before that dependency. Buckets use the concrete path, not simply the named rule prefix. This is an IP-based, fixed-window implementation in practice, not the more general policy described in comments.

Recommended repair: use one trusted-proxy address resolver and explicit bucket scope. Test spoofed headers from untrusted peers, a trusted multi-hop proxy, and configured limits against a real Redis instance.

### F11 — Account deletion misses active payment states; eventual hard deletion conflicts with retained orders

14 October update: eligibility/profile safeguards implemented and bulk hard-delete
disabled; complete retention/offboarding/erasure remains open. See checkpoint 2.

Source: `app/services/customer_service.py:595`; `app/tasks/cleanup_tasks.py:79`; `app/models/order.py:55`; migrations 001, 002 and 004.

The active-order guard omits `pending_payment` and `payment_confirmed`, so a customer with a paid but unfulfilled order can soft-delete their account. The shared `CurrentUser` dependency also permits sellers/admins on customer endpoints; seller offboarding needs an explicit policy rather than inheriting customer deletion.

The 90-day cleanup then bulk-deletes users. Registered orders normally have no guest email; `ON DELETE SET NULL` on their user reference conflicts with the order constraint requiring a user or guest email. Seller and other historical foreign keys can also reject deletion. One blocked record can abort the batch. Reviews use cascading deletion despite the cleanup comment saying they are retained.

Recommended repair: explicit retention/anonymization and seller-offboarding design, then per-case tests using migrated tables. Do not solve this by indiscriminately deleting financial history.

### F12 — Malformed catalogue cursors can become HTTP 500 errors

Source: `app/repositories/product_repo.py:183`.

Base64 decoding and JSON parsing do not validate that the result is an object before `.get`; a JSON list produces `AttributeError`. A bad price value produces `decimal.InvalidOperation`, outside the caught exception tuple. Both exceptions were reproduced before any DB access.

Recommended repair: validate cursor shape, expected sort, UUID and finite numeric/date value, and consistently return a client error. Add malformed list/null/scalar/price/date/oversized cursor cases.

### F13 — Inventory reorder-point input is accepted but ignored

14 October update: repaired with persisted per-item thresholds in migration 018 and
native regression tests; see checkpoint 2. On 16 October, checkpoint 6 also replaces
the analytics inventory-health constant with the persisted per-variant threshold,
with failing-before/passing-after HTTP regressions. The text below is the original finding.

Source: `app/services/inventory_service.py:155` and inventory route schemas.

`set_stock` accepts `reorder_point` but never persists it. Response conversion and low-stock checks use a fixed threshold, and the model has no corresponding field. The API can report success without applying the user's requested configuration.

Recommended repair: implement persisted threshold semantics, or remove/reject the unsupported input until supported; test read-after-write and low-stock classification.

### F14 — Seller reinstatement clears independent product moderation

Source: `app/services/admin_service.py:200` and `:220`.

Suspension sets `admin_hidden=True` on all seller products; reinstatement sets it to false on all of them. A product hidden independently for moderation before suspension is therefore unhidden too.

Recommended repair: separate seller visibility from product moderation, or track independent reasons. Test that reinstatement preserves pre-existing product takedowns.

### F15 — Enabling configured Sentry can fail startup

Source: `main.py:62`; `requirements.txt`.

Production startup imports `sentry_sdk` when a DSN is configured, but the SDK is absent from declared runtime requirements and from the inspected virtual environment. The conditional path is therefore not validated by ordinary development startup.

Recommended repair: declare the runtime dependency if supported, and test the enabled configuration. Also guarantee resource cleanup if a later startup step fails after pools are opened.

### F16 — Configuration, precision and response contracts need consolidation

Checkpoint 8 partially repairs this finding: all eight money-bearing analytics
routes now preserve Decimal fractions and emit PKR decimal strings, with explicit
two-place average rounding. Native fractional/empty/share cases and schema tests
cover the change. Coupon/slot/notification precision, canonical links and error
envelopes remain open. See [checkpoint 8](PRE_SHIP_CHECKPOINT_8.md) for compatibility
changes and unchanged reporting bases; the historical description below is the baseline.

Sources: `app/integrations/resend_client.py:121` and `:138`; `app/core/config.py`; `app/schemas/analytics.py`; `app/services/analytics_service.py`; `main.py` exception handlers.

Verification/reset links use `ALLOWED_ORIGINS[0]` whereas other links use `FRONTEND_URL`; their defaults even point to different ports. Analytics and legacy seller/payout shapes cast monetary values to integers while newer contracts preserve Decimal fractions. Direct `HTTPException` responses do not use the custom error envelope, so clients cannot assume one shape for every error.

Recommended repair: one canonical public URL source, one documented money representation, and a documented/consistent error contract. Compatibility names such as JWT audience or refresh-cookie names should not be renamed casually.

### F17 — Test-quality and tooling gaps weaken completion evidence

Source: `tests/integration/test_product_api.py`, other legacy API smoke modules, `tests/security/test_auth.py`, `tests/load/locustfile.py`, and `tests/unit/test_connected_services.py`.

Several catalogue smoke assertions explicitly allow 500 responses; many supposed validation tests run without authentication and accept either 401 or 422. These can pass without testing the named rule. The legacy security module is unconditionally skipped. The load script uses stale paths/filters and defaults that cannot complete email verification/seller approval, silently falls back to anonymous headers, accepts expected 404 reads, and lacks the checkout actions advertised in its docstring. Provider unit helpers also mutate shared settings without consistently restoring them.

Full configured Ruff over `app main.py scripts` reports 1,018 findings, largely style/import/type-annotation issues; the fatal-error subset passes. `pip check` passes but does not constitute an advisory scan. Mypy is not installed, so strict type checking was not performed. These results are distinct from application correctness and should not be described as 1,018 independent functional bugs.

Recommended repair: precise authenticated assertions, boundary-level regression tests for the findings, environment-aware security tests, valid seeded load journeys and explicit separation of mock/native/live evidence. Keep useful coverage requirements unchanged.

## Security and operational observations requiring further verification

- Authentication includes signed RS256 tokens, DB-backed auth-version checks, email verification and Redis revocation checks. These are valuable controls. Admin TOTP is conditional on enrolment; the dependency checks admin role, not an independent MFA assurance claim. Mandatory-enrolment/step-up policy needs an explicit decision.
- Synchronous Argon2 hashing and image conversion are called from asynchronous service paths. Offload or benchmark them under realistic concurrency before treating asynchronous I/O as evidence of good CPU-bound performance.
- The development Redis configuration uses `allkeys-lru`, while Redis carries security state, carts and worker jobs. Do not reuse this eviction policy for critical session-revocation or durable queue guarantees without designing failure behaviour.
- Request logging redaction is not a universal guarantee that arbitrary nested provider payloads or personal data are scrubbed. Review actual production logging and retention separately; no local secrets were printed in this audit.
- Lock ordering and ORM identity-map freshness deserve native tests across mixed operations, not only duplicates of the same operation. In particular, examine multi-variant checkout order and return/fulfilment lock order. These are investigation targets, not reproduced deadlock claims.
- The historical security module has an unconditional module-level skip, not an environment-sensitive opt-in (`tests/security/test_auth.py:26`). Some assertions would also accept success where a security rejection was expected. Other active security/regression tests exist; the skip does not mean there is no security testing at all.
- Model-created tables and Alembic-created tables are not identical evidence. For example, migration 009 adds the refund-to-return foreign key, but the model's `return_id` declaration lacks it. The migration test reads all model columns but does not compare every constraint/index/default.

## Documentation and historical evidence

`docs/openapi.json` matches the current application schema exactly in an offline comparison. That is positive contract evidence.

`docs/verification.json` is explicitly the older Task 6 snapshot (8 October, 570 tests, revision 013, 171 schema operations). Later source and documentation include revisions 014/015 and more endpoints. Preserve that file as historical evidence or clearly version it; do not describe it as current verification. This review's fresh checks are recorded above, separately from historical results. The stored dependency advisory report is likewise historical, not a fresh vulnerability scan.

## Original suggested repair order — current status

1. **Completed in batch 1:** unify payout transitions; make return/refund creation atomic; correct wallet audit balances.
2. **Completed in batch 2:** design coherent refund allocation, net accounting, shortfalls and hold/release reconciliation.
3. **Partially completed in batch 3:** favourable disputes are reconnected with end-to-end regressions; notification business events remain open.
4. Correct trusted-proxy handling, deletion lifecycle, cursor validation and moderation/configuration gaps.
5. Rerun migrated native PostgreSQL/Redis tests, full coverage, contract checks, dependency/security review and production-like startup.
6. Perform separately authorized provider sandbox and deployment checks; keep real charges and publishing gated.

This was the review's proposed follow-up order. Batches 1–3 subsequently completed the items marked above. No commit, provider write, historical-balance reopening or deployment was performed by those batches.

# Backend repair queue before frontend implementation

Current status, 17 October 2026: [pre-ship checkpoint 11](PRE_SHIP_CHECKPOINT_11.md)
supersedes the baseline below. Cross-account resource tests and approved limited
customer cleanup supplement notification recovery, legacy preference import,
190 route policies and complete migrated-schema parity. Migration head: 020.
Full suite (17 October): 977 passed, 1 skipped, 87.55% coverage. Checkpoint 11 fixes
catalogue/wishlist price truncation, documents seven underlying decimal-string
fields and adds 35 native/unit cases. Price-entry/filter policy stays whole PKR;
variant, cart, guest quote and checkout amounts agree in regression tests. Checkpoint 10 fixes
slot/notification money presentation, publishes five slot decimal-string fields and
adds 49 native/unit cases while retaining pricing/accounting/privacy policy. Checkpoint 9 repairs
coupon preview/checkout precision, exact minimums and multi-seller rounding residuals;
39 new native/unit cases cover the changes. Checkpoint 8 preserves
fractional analytics money and publishes decimal-string response contracts with
rounding/empty-data/share regressions. F16 remains partially open. Checkpoint 7 fixes
admin bulk-stock false success after row errors, validates batches and tests rollback
and reservation/bulk races. Checkpoint 6 adds seller aggregate/filter isolation and
fixes inventory-health thresholds;
checkpoint 5's legacy email privacy checks and zero ARQ result retention remain.
F08 has fail-closed local monetary verification (merchant acceptance still gated);
F13 is implemented. F11 now has durable customer cleanup and deletion/case/refresh
race safeguards, but final policy, pending/old queue payloads, cross-system erasure and managed
offboarding remain open. Exhaustive ownership, static/type and broader review remain.
Recommended next: F16 canonical public-link/callback configuration, then error
contracts. Remaining legacy/untyped money shapes still need review.
Historical coupon allocations and zero-total orders
with free shipping are not certified by checkpoint 9; see its explicit limits.

Updated 13 October 2026. Backend only. This queue comes from the completed static source/test review, not from the older completion claims. Repair batches 1 through 4 are implemented; later batches remain pending. See [detailed findings](BACKEND_DEEP_REVIEW.md), [batch-1 report](BACKEND_B1_REPORT.md), [batch-2 report](BACKEND_B2_REPORT.md), [batch-3 report](BACKEND_B3_REPORT.md), [batch-4 report](BACKEND_B4_REPORT.md) and [system walkthrough](BACKEND_WALKTHROUGH.md).

Review baseline: 602 tests passed, 1 skipped, 85.59% coverage with native PostgreSQL/Redis enabled. After batch 4, the final suite is 621 passed, 1 skipped with 85.88% coverage; the unchanged 85% gate passes. F01-F07 and F09 are resolved, while F08 and F10-F17 remain open. See the [review verification](audit/verification-2026-10-12.json), [batch-1 verification](audit/b1-verification-2026-10-12.json), [batch-2 verification](audit/b2-verification-2026-10-13.json), [batch-3 verification](audit/b3-verification-2026-10-13.json) and [batch-4 verification](audit/b4-verification-2026-10-13.json).

## 1. Completed — financial transaction integrity

Current pre-ship delta: F12/F14 are repaired; F15 API startup/dependency handling and
F10 proxy/rate-counter handling have regression coverage. The older baseline above
describes the B4 checkpoint. The [162-item audit](PRE_SHIP_AUDIT.md) is authoritative
for the broader ongoing checklist and explicitly records remaining gates.

- **F01 completed:** the legacy admin completion route delegates to the locked payout state machine, requires/persists its receipt, preserves Decimal amounts and reports the reference.
- **F02 completed:** return-linked refund creation is one caller-owned transaction; failure before its outer commit leaves no orphan refund.
- **F03 completed:** refund debit history records the actual combined post-transaction wallet balance from pre-update snapshots.

Acceptance evidence: eight new focused cases cover the compatibility route, invalid states, receipt replay/conflict, atomic failure/retry and four wallet-balance shapes. A native PostgreSQL race proves completion and rejection have one valid winner. Existing payout/refund and concurrent-confirmation regressions remain passing. Final verification also corrected and proves revision 009's isolation from same-named enums in unrelated schemas. See [batch-1 report](BACKEND_B1_REPORT.md).

## 2. Completed — refund allocation and settlement reconciliation

- **F04 completed:** the release scanner moves only the mature ledger's net entitlement, checks real return/dispute states and does not let one seller's refund freeze another seller's ledger.
- **F05 completed:** revision 016 persists refund accounting plus seller-order allocations. Return-linked refunds target only their seller; pre-settlement allocations become explicit offsets.
- **F06 completed:** original and net ledger values, commission/seller reversals, shipping, actual recovery, settlement offsets and platform shortfall are stored and exposed. Financial reporting uses net values while retaining original audit values.

Acceptance evidence: native PostgreSQL regressions cover partial/full/refund-before-settlement, multi-brand seller isolation, proportional cent allocation, shipping, open/resolved-seller disputes, matured remainder release, mixed pending/available recovery, already-paid-out shortfall, idempotency and exactly-once stock credit. Database constraints enforce the stored conservation equations. See [batch-2 report](BACKEND_B2_REPORT.md).

Policy retained: sellers bear only their net merchandise entitlement; the platform bears refunded shipping, reversed platform commission and seller-funds shortfall. No recoverable seller debt is created. Historical unallocated refunds remain quarantined until separately reconciled.

## 3. Completed — return/dispute outcomes

- **F07 completed:** a customer-won dispute atomically approves its rejected return only after revalidating quantities while holding the seller-order aggregate lock. Seller-won disputes leave the return rejected.

Acceptance evidence: the complete reject → dispute → customer-win → receipt → refund request → transfer confirmation journey passes. Resolution alone creates no refund, restock or transfer receipt. A native two-session race between customer-win activation and a new claim for the same purchased quantity permits exactly one active owner. See [batch-3 report](BACKEND_B3_REPORT.md).

## 4. Completed — notification delivery and preferences

- **F09 completed:** order creation/status, payout status and seller decisions write deterministic events to revision-017's transactional outbox in the same commit as the business change. The registered minute worker publishes them to ARQ with deterministic job IDs and retries queue failures.
- **F09 completed:** provider failures now persist on one keyed email-log row and propagate to ARQ. Retried in-app and email delivery is locally idempotent; successful delivery is not sent again.
- **F09 completed:** both customer preference APIs use the same database row. Registered routine order email/push and seller payout notices enforce their toggles. Placement confirmations, guest lifecycle messages and seller application decisions are required transactional notices; promotion/new-arrival email toggles remain optional and no marketing sender is introduced here.
- All interpolated order-item/status HTML is escaped. Guest email links contain a signed, order-scoped capability that the frontend must exchange for the existing `X-Guest-Token` header; forged or cross-order tokens remain denied.

Acceptance evidence starts at business service operations, inspects persisted events and published jobs, forces Redis and Resend failures/retries, proves opt-out and deduplication behavior, checks hostile HTML input, and exercises signed guest access. No real message was sent. See [batch-4 report](BACKEND_B4_REPORT.md).

## 5. Security and account lifecycle

- **F10 partially repaired:** shared socket-peer/trusted-chain resolution, explicit rule buckets and atomic expiry counters are implemented and native Redis-tested. Ingress configuration and rate-limit outage policy remain audit items. See [pre-ship audit](PRE_SHIP_AUDIT.md).
- **F11: Correct deletion eligibility and retention.** Include pending/confirmed-payment orders, define seller/admin offboarding and replace broken bulk hard deletion with an intentional retention/anonymization policy.
- Decide/administer mandatory admin MFA or step-up rules; existing role checks and optional TOTP enrolment do not establish mandatory MFA assurance.
- Validate mixed-operation lock ordering and stale ORM state with native concurrent tests before claiming races are fully covered.

Acceptance: spoofed/untrusted/trusted forwarding cases; existing accounts/orders/returns/reviews under migrated constraints; no loss of financial history; documented MFA policy. Concurrency/MFA items are validation/design work, not claims of a reproduced exploit.

## 6. API behaviour and operational correctness

- **F12 repaired:** malformed shape/types, invalid decimals, encoding, oversized cursors and timezone-less timestamps are rejected as client errors; regression tests added.
- **F13:** Persist inventory reorder thresholds or reject/remove the unsupported input.
- **F14 repaired:** suspension uses seller visibility rather than overwriting product moderation. Reinstatement preserves independently hidden products, with native regression coverage. Legacy ambiguous hidden flags require manual review rather than automatic unhiding.
- **F15 code repaired:** Sentry runtime dependency is declared and configuration tested without sending events; resource cleanup covers partial startup/application/shutdown failure. Real Sentry alert delivery remains external.
- **F16:** Consolidate canonical frontend/callback/link configuration, money precision, error envelopes and duplicated limits.
- Check compatibility aliases and public review visibility consistently. Preserve JWT/cookie/Redis compatibility identifiers unless an explicit migration is intended.

Acceptance: negative request tests, read-after-write checks, moderation-history preservation and production-like startup with optional features enabled using test doubles.

## 7. PayFast code guarantees versus provider verification

- **F08 code gap:** require authoritative amount and currency verification before marking reconciliation successful; define fail-closed/manual-review handling for absent information. Cover callback and reconciliation separately.
- **External gate:** validate the merchant-specific protocol, endpoint access and callback/retry/reconciliation journey in the real sandbox. Documentation retrieval alone or matching mocked fixtures is not provider certification.

Keep `PAYFAST_ENABLED=false` until the required checks pass. Adding keys is not the only remaining step. No live charges without a separately approved test/deployment scope.

## 8. Test quality and final backend handoff

- Replace smoke assertions that accept 500/501 or conflate authentication failures with validation failures; test the actual rule with authorized fixtures.
- Repair the unconditionally skipped legacy security module; retain the stronger active ownership/security cases.
- Correct stale Locust routes/filters, unverified/unapproved default accounts and missing advertised checkout activity before relying on load results.
- Avoid global settings leakage in provider tests and broad exception assertions that can mask unrelated failures.
- Compare migrated schema constraints/defaults/indexes with model metadata, not just column reads.
- Add regression tests for every confirmed finding; retain the unchanged 85% coverage gate. Run native PostgreSQL/Redis suites after fixes, not just mocks.
- Address risk-relevant lint/type issues. Full configured Ruff currently reports 1,018 findings; many are formatting/type-annotation issues rather than distinct application defects. Mypy is not installed in the reviewed environment. Dependency consistency passes, but this is not a fresh vulnerability scan.
- Refresh current verification, contract and known-limit documents without overwriting historical evidence as though it were current. Package only after review/fix validation.

## Separate pre-production gates

Live Google sign-in; Supabase bucket/policy/upload/delete checks; Resend sender/domain and delivery; PayFast sandbox approval; historical ledger reconciliation; secrets rotation where applicable; production DB/Redis isolation/backups/eviction policy; proxy/TLS/origin configuration; worker scheduling and recovery; monitoring; performance/load checks; final deployment review. Production publishing remains a separate action.

## Recommended execution rule

Complete one numbered repair batch, add targeted regression tests, run appropriate checks and report the result before choosing the next batch. Financial corrections should precede frontend integration because they change observable states, balances and receipts. Cosmetic lint cleanup should not be mixed into financial repairs.

# Backend repair queue before frontend implementation

12 October 2026. Backend only. This queue comes from the completed static source/test review, not from the older completion claims. Batch 1 has now been implemented; later batches remain pending. See [detailed findings](BACKEND_DEEP_REVIEW.md), [batch-1 report](BACKEND_B1_REPORT.md) and [system walkthrough](BACKEND_WALKTHROUGH.md).

Review baseline: 602 tests passed, 1 skipped, 85.59% coverage with native PostgreSQL/Redis enabled. After batch 1, the final suite is 611 passed, 1 skipped with 85.70% coverage; the unchanged 85% gate passes. F01-F03 are resolved, while F04-F17 remain open. See the [review verification](audit/verification-2026-10-12.json) and [batch-1 verification](audit/b1-verification-2026-10-12.json).

## 1. Completed — financial transaction integrity

- **F01 completed:** the legacy admin completion route delegates to the locked payout state machine, requires/persists its receipt, preserves Decimal amounts and reports the reference.
- **F02 completed:** return-linked refund creation is one caller-owned transaction; failure before its outer commit leaves no orphan refund.
- **F03 completed:** refund debit history records the actual combined post-transaction wallet balance from pre-update snapshots.

Acceptance evidence: eight new focused cases cover the compatibility route, invalid states, receipt replay/conflict, atomic failure/retry and four wallet-balance shapes. A native PostgreSQL race proves completion and rejection have one valid winner. Existing payout/refund and concurrent-confirmation regressions remain passing. Final verification also corrected and proves revision 009's isolation from same-named enums in unrelated schemas. See [batch-1 report](BACKEND_B1_REPORT.md).

## 2. Refund allocation and settlement reconciliation — next

- **F04: Implement finite hold/release behaviour.** Release legitimate remaining earnings after a partial refund; do not freeze another brand's earnings. Check real dispute/return holds, not just existence of any refund row.
- **F05: Preserve seller-specific allocation before/after settlement.** A return for brand A must not reduce a later settlement for brand B. Use the same persisted allocation regardless of delivery/collection timing.
- **F06: Complete net accounting.** Account for seller reversal, platform commission reversal, shipping allocation, rounding residuals and funds already paid out. Expose actual recovery separately from platform-funded shortfall and ensure reports reconcile.

Acceptance: partial/full/refund-before-settlement, staggered multi-brand delivery, open/resolved disputes, matured balances, mixed pending/available funds and already-paid-out cases, with conservation-of-money and exactly-once stock assertions. Both the mature partial-refund hold and an unrelated brand's reduced settlement were reproduced on native PostgreSQL.

Policy decisions before implementation: who bears shipping/refund shortfalls, and whether any seller debt is recoverable. Do not silently change the current platform-absorbs-shortfall policy. Historical revision-012 releases remain quarantined until separately reconciled.

## 3. Complete return/dispute outcomes

- **F07: Reconnect a customer-won dispute to a usable return workflow.** Define and implement reopening/approval, revalidate remaining quantities and permit receipt/refund through the existing manual confirmation flow.

Acceptance: reject → dispute → favourable resolution → receipt → refund request → transfer confirmation, including competing quantity claims. Resolving a dispute must not invent a transfer receipt.

## 4. Notification delivery and preferences

- **F09: Dispatch missing business events.** Order confirmations/status, payouts and seller approval/rejection must actually enqueue their registered workers.
- **F09: Preserve retry failures and deduplicate delivery.** A swallowed provider error must not look like a successful task. Coordinate DB changes and queue publishing reliably.
- **F09: Unify preference storage and enforce it.** Customer Redis preferences and DB notification preferences currently differ, and event delivery does not consistently consult them. Explicitly distinguish optional marketing from required transactional notices.
- Review template escaping and guest tracking-link access before enabling new delivery paths; interpolated product/customer content must not become unintended email markup.

Acceptance: begin tests at the business API/service operation, inspect the resulting job, exercise delivery failure/retry and opt-out behaviour, and verify guest access. Do not send real messages during tests.

## 5. Security and account lifecycle

- **F10: Centralize trusted-proxy/IP handling.** Rate limiting must not trust arbitrary forwarding headers; use explicit bucket scope and test the real Redis behaviour.
- **F11: Correct deletion eligibility and retention.** Include pending/confirmed-payment orders, define seller/admin offboarding and replace broken bulk hard deletion with an intentional retention/anonymization policy.
- Decide/administer mandatory admin MFA or step-up rules; existing role checks and optional TOTP enrolment do not establish mandatory MFA assurance.
- Validate mixed-operation lock ordering and stale ORM state with native concurrent tests before claiming races are fully covered.

Acceptance: spoofed/untrusted/trusted forwarding cases; existing accounts/orders/returns/reviews under migrated constraints; no loss of financial history; documented MFA policy. Concurrency/MFA items are validation/design work, not claims of a reproduced exploit.

## 6. API behaviour and operational correctness

- **F12:** Reject malformed catalogue cursors as client errors instead of 500s.
- **F13:** Persist inventory reorder thresholds or reject/remove the unsupported input.
- **F14:** Preserve independently hidden products when reinstating a seller.
- **F15:** Declare/test the Sentry runtime dependency and clean up resources after partial startup failure.
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

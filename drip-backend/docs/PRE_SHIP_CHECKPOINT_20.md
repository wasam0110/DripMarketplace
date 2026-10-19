# Backend pre-ship checkpoint 20: payment HTTP test quality

19 October 2026. Backend only. The 162-item audit remains **IN PROGRESS**.
Only tests/documentation change. Application behavior, API contracts, frontend,
configuration and migrations are unchanged. No local secrets, live provider calls,
production transactions, Git staging/commit/push or deployment were involved.
Earlier working-tree changes are preserved.

## Bounded repair

`tests/integration/test_payment_api.py` previously used a router-only application,
mocked database and suppressed server exceptions. Most assertions accepted either
401 or 422. Validation cases lacked valid authorization, and the retry example
used retired JazzCash. Its 11-test baseline passed without establishing successful
payment operations or the intended validation rules.

The replacement has **43 native HTTP cases**, replacing those 11 cases (32 net
additional cases). It uses the shared application client, generated test tokens,
real PostgreSQL rows and signed guest capabilities. The external COD scheduling
boundary is mocked; provider transport is blocked and PayFast stays disabled in
this module. No database or payment-service result is mocked.

The cases verify:

- Initiate/status/retry require an account identity or guest capability. Forged,
  cross-order and unrelated-account access returns precise 404 responses without
  changes across orders, items, seller orders, payments, callbacks, inventory,
  wallets, wallet transactions, commission ledgers or refunds.
- Valid guest COD initiation is idempotent and exposes the exact PKR 2600.50 amount.
  Authorized orders lacking a payment return 404. An account-owned order accepts
  its owner and rejects the former guest capability.
- Retired/invalid retry methods return field-specific 422 responses with valid
  access. A failed online payment retries as COD using the same payment row and
  amount, clearing failure/old attempt data and updating order/payment status.
- The retired Stripe callback remains 404 and leaves financial state unchanged.
- Admin gateway/list/refund routes reject anonymous and wrong-role callers.
  Actual admin controls verify gateway status, matching payment rows and filters.
  Invalid filters and refund fields require the specific validation field.
- A fractional refund request remains pending, records its requester, and is
  idempotent. Requesting/replaying it does not claim a transfer, credit stock or
  alter balances. Excess refunds and changed idempotent requests are rejected
  without additional financial effects.

Completed-payment fixtures seed that state for request/validation checks. They do
not claim to execute the complete COD collection/fulfilment process. Existing
refund-confirmation/accounting regressions are included separately below.

## Verification

Final combined run: **90 passed, zero failures/errors/skips**, 231 warnings,
169.80 seconds. Saved XML groups 43 replacement payment HTTP cases, 23 existing
native financial/retired-method/refund/callback/reconciliation cases and 24 payment
schema/adapter/evidence unit cases. The suites ran together to check fixture and
settings isolation. Source was not edited during this final run.

Configured Ruff passes for the rewritten file; backend `git diff --check` passes.
There are no application, migration, OpenAPI or endpoint-inventory edits in this
checkpoint. Repository-wide lint/type approval is not claimed.

Evidence under `docs/audit`:

- `preship-checkpoint-20-tests-2026-10-19.xml`: successful final verification.
- `preship-checkpoint-20-legacy-baseline-2026-10-19.xml`: original permissive suite,
  11 passed, 25 warnings, 1.30 seconds. This is historical baseline evidence.
- `preship-checkpoint-20-payment-tests-2026-10-19.xml`: initial development run,
  22 passed and 21 fixture errors. The new fixture incorrectly used the nonexistent
  `OrderStatus.confirmed`; it was corrected to `payment_confirmed`. These were test
  setup errors, not payment-service failures, and are absent from the final run.

```powershell
# TEST_DATABASE_URL must target a disposable PostgreSQL database ending in _test.
.\.venv\Scripts\python.exe -m pytest tests/integration/test_payment_api.py tests/integration/test_b1_financial_integrity.py tests/integration/test_historical_payment_methods.py tests/integration/test_marketplace_regressions.py::test_guest_checkout_payment_idempotence_and_access tests/integration/test_marketplace_regressions.py::test_refund_request_is_pending_capped_and_idempotent tests/integration/test_marketplace_regressions.py::test_admin_refund_queue_detail_history_and_balances tests/integration/test_marketplace_regressions.py::test_admin_refund_reads_validate_filters_and_missing_records tests/integration/test_marketplace_regressions.py::test_payment_callback_amount_signature_and_replay tests/integration/test_marketplace_regressions.py::test_payfast_status_reconciliation_is_verified_and_idempotent tests/unit/test_payments.py tests/unit/test_payfast_evidence.py --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-20-tests-2026-10-19.xml
.\.venv\Scripts\ruff.exe check tests/integration/test_payment_api.py
```

The rewritten file now requires the shared disposable TEST_DATABASE_URL fixture.
Without that configuration its execution skips explicitly; a skip is not native
verification. PostgreSQL 16 execution used only loopback and synthetic data. Redis
used fakeredis. Real Redis workers, live PayFast and actual transfers were not
revalidated. The checkpoint container and anonymous volume were removed, with
absence verified. Deleted test data is reproducible from fixtures. Development
`drip_redis` remains healthy and was not modified.

Full-suite coverage was not rerun for this test-only change. Latest historical full
evidence remains checkpoint 14: **1,104 passed, 1 skipped, 87.96% coverage**. Its skip
describes the former security module. The unchanged 85% gate is not a new scoped
coverage result; validation here explicitly used --no-cov.

## Next and remaining boundaries

Next: legacy wallet API smoke assertions. Other seller/order/return smoke files,
load journeys, dependency/static/type work and broader F16/F17 parity/coverage
remain open. This checkpoint does not certify financial race coverage, final
retention/offboarding, historical reconciliation or external release acceptance.
The broader backend audit is not complete.

# Backend pre-ship checkpoint 16: withdrawal-limit configuration

19 October 2026. Backend only. The 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, local secret reads, production configuration changes,
real payments/provider calls, staging, commit, push or deployment. Earlier dirty
changes are preserved.

## Finding and bounded repair

MIN_WITHDRAWAL_AMOUNT and MAX_WITHDRAWAL_AMOUNT existed in Settings and the sample
environment, but WithdrawalRequest hardcoded 500/200000 and WalletService used a
separate hardcoded 500 minimum without a maximum check. Changing the advertised
configuration therefore did not change the API's enforced policy.

Three runtime files change:

- `app/core/config.py`: validate positive, ordered whole-PKR withdrawal bounds
  at startup. Maximum cannot exceed 9999999999, the largest integer bound that fits
  existing wallet/payout NUMERIC(12,2) storage. Clarify that only supported business
  settings have database overrides; withdrawal bounds are startup-only.
- `app/schemas/wallet.py`: request validation and OpenAPI use the loaded configured
  minimum/maximum instead of duplicated literals. Decimal precision remains two
  places, max_digits remains 12, and defaults remain inclusive PKR 500–200,000.
- `app/services/wallet_service.py`: use configured minimum and maximum before any
  bank lookup/debit/payout/transaction write, including already-built direct-call
  payloads. Wallet lookup/lock and insufficient-balance precedence are preserved.

The sample environment and setup notes explain coordinated API/worker restarts.
This does not introduce a system_settings key, runtime admin control, fee, new
withdrawal policy, migration or financial-record rewrite. Existing row locking,
bank ownership, ledger entries, payout states and receipts are unchanged. Migration
head remains 020. Hot-mutating settings after schema import is unsupported.

## Verification

Before repair, the focused run had 11 failures and 7 passes: invalid startup bounds
were accepted, non-default schema ranges were ignored, and both service guard cases
fell through to bank lookup (their mocks then failed). Those mocks were tightened
to fail explicitly if an out-of-policy amount reaches bank lookup. After repair,
all 18 focused unit cases passed. Final saved runs:

| Run | Result | Evidence |
|---|---|---|
| All unit tests, default configuration | 632 passed; 200 warnings; 72.79s | `audit/preship-checkpoint-16-unit-tests-2026-10-19.xml` |
| Native withdrawal flows, MIN=750 / MAX=1000 | 15 passed; 27 warnings; 33.29s | `audit/preship-checkpoint-16-custom-limits-tests-2026-10-19.xml` |
| Native flows and existing regressions, MIN=500 / MAX=200000 | 36 passed; 122 warnings; 85.80s | `audit/preship-checkpoint-16-native-regressions-2026-10-19.xml` |

There are 33 new cases: 18 unit and 15 native. The 15 native cases run under both
custom and default settings; do not count these repeat executions as new tests.
Unit subprocesses independently boot with default, narrower, wider and equal-bound
configuration and verify schema rejection/acceptance plus generated OpenAPI bounds.
Other unit cases cover invalid startup ranges, non-finite/over-precision amounts
and service guards before side effects.

Native tests prove inclusive edges and fractional amounts debit once, exact payout/
ledger values and balance_after, rejected inputs and direct calls leave financial
snapshots unchanged, role rejection, missing bank accounts and insufficient balance.
The default regression run also includes the permission matrix, B1 financial tests,
existing withdrawal/rejection/receipt HTTP/service flows and independent-connection
competing-withdrawal and payout-complete/reject races.

All native execution used a disposable loopback-only PostgreSQL 16 database with
synthetic fixtures. Redis dependencies use fakeredis; real Redis-worker behavior
was not revalidated. No runtime/test source edits were made during the final runs.
Configured Ruff passes for the two new test files; syntax-critical checks pass for
the three runtime files. This is not repository-wide lint/type sign-off.

Offline export succeeds with 190 operations; default withdrawal OpenAPI bounds stay
500/200000. A custom deployment must export its own configured contract. No endpoint
or response shape was added. The configured 85% coverage gate remains unchanged;
these scoped runs use --no-cov. Latest full-suite evidence remains checkpoint 14:
**1,104 passed, 1 skipped, 87.96% coverage**, not a fresh checkpoint-16 measurement.

### Reproduction

Run from the backend with TEST_DATABASE_URL pointing to a disposable PostgreSQL
database ending in `_test`, never a development/production database.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-16-unit-tests-2026-10-19.xml
$env:MIN_WITHDRAWAL_AMOUNT='750'
$env:MAX_WITHDRAWAL_AMOUNT='1000'
.\.venv\Scripts\python.exe -m pytest tests/integration/test_withdrawal_limit_flows.py --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-16-custom-limits-tests-2026-10-19.xml
$env:MIN_WITHDRAWAL_AMOUNT='500'
$env:MAX_WITHDRAWAL_AMOUNT='200000'
.\.venv\Scripts\python.exe -m pytest tests/integration/test_withdrawal_limit_flows.py tests/integration/test_b1_financial_integrity.py tests/integration/test_permission_matrix.py tests/integration/test_marketplace_regressions.py::test_wallet_withdrawal_rejection_and_transfer_receipt tests/integration/test_marketplace_regressions.py::test_http_wallet_precision_roles_and_duplicate_payout_actions tests/integration/test_release_native.py::test_competing_withdrawals_cannot_spend_same_balance tests/integration/test_release_native.py::test_concurrent_payout_completion_and_rejection_have_one_winner --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-16-native-regressions-2026-10-19.xml
.\.venv\Scripts\python.exe scripts/export_contract.py
```

## Remaining boundaries

The checkpoint PostgreSQL container and its anonymous volume were removed, with
absence verified. Only disposable synthetic data was deleted; fixtures can recreate
it. Development `drip_redis` remains healthy and untouched. Backend diff whitespace
checks pass. Nothing was staged, committed or pushed.

Next bounded review: product/image policy-limit duplication. The six-image cap is
repeated in the route, service and reorder schema; product-entry bounds are also
repeated. These are drift risks, not evidence of differing current values. No image
upload/concurrency/storage behavior was changed or newly certified here.

F16 and the broader audit stay open: universal schema parity, ownership/input/race
coverage, dependency/static/type work, final retention and managed offboarding,
historical reconciliation and staging/provider/production acceptance are not closed
by this fix. No backend-complete or defect-free guarantee is made.

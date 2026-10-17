# Backend pre-ship checkpoint 10: slot and notification money presentation

17 October 2026. Backend only. The broader 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, real provider send, production mutation, deployment,
commit or push. Earlier checkpoint 9 working-tree changes were preserved.

## Repairs and scope

- Order-placement notices and emails no longer truncate stored PKR amounts.
  Unit prices, line subtotals, shipping fees and totals use grouped two-place
  formatting. For example 1,000.25, 2,000.50, 200.35 and 2,200.85 remain exact.
- Approved/completed payout notices preserve paisa: 5,000.01 and 5,000.75 are no
  longer both displayed as 5,000. Notification delivery does not change the payout
  amount or create a second financial transaction.
- Legacy queued order email rendering accepts Decimal, decimal strings and old
  numeric payloads. It formats two places explicitly instead of failing on string
  amounts or displaying inconsistent precision. Display rounding uses ROUND_HALF_UP;
  this helper is not used for ledger calculations. Non-finite/invalid values fail
  before an email is sent. Lost precision in an old truncated/float payload cannot
  be reconstructed by formatting.
- Insufficient slot balance errors preserve the exact available balance, e.g.
  `Need PKR 261.00, have PKR 260.99`. Three slot-limit messages no longer assert a
  fixed PKR 50 price when runtime configuration may differ.
- Slot pricing/purchase response amounts use Decimal internally and two-place
  strings in JSON. Whole-rupee configuration policy, zero-priced slots, quantity
  limits, registration flow, wallet charge arithmetic and slot counts are unchanged.

There is no migration or accounting-schema change; head remains 020. This does
not enable fractional admin pricing settings. Existing notification identity,
preferences, recipient privacy checks, guest capabilities, retries and send-log
deduplication are retained. Previously stored notifications/sent emails are not
rewritten or resent; old queue payloads are not purged or retroactively repriced.

## Intentional API compatibility change

Clients must handle these five fields as decimal strings in **PKR major units**,
not integer paisa. Slot counts remain JSON integers. Other pricing-setting fields
are unchanged. No frontend code was inspected or edited.

| Endpoint | Fields now serialized as two-place decimal strings |
|---|---|
| GET /api/v1/seller/register/slot-price | registration_fee, extra_slot_price, extra_cost, total_cost |
| POST /api/v1/seller/slots/purchase | amount_charged |

Examples: `"0.00"`, `"87.00"`, `"261.00"`. The schemas reject non-finite, negative
or nonzero beyond-two-place response amounts instead of truncating them. The API
still contains 190 operations; the exported contract documents the type change.

## Verification

Before repair, the native selection had **11 failures and 1 pass**: nine failures
reproduced truncated notification/error amounts, while two asserted the intentional
new slot response contract. The existing payout opt-out control passed.

New native module `tests/integration/test_notification_slot_money.py` has 12 cases.
Tests cover customer/guest order money, retry deduplication, signed guest
links, payout fractions and opt-out, zero/custom slot pricing, persisted wallet
transaction amounts, and exact insufficient-balance errors with no financial/slot
mutation. Native tests use disposable PostgreSQL; providers are mocked.

New unit module `tests/unit/test_money_presentation.py` has 37 cases. Tests cover
grouped two-place formatting, explicit half-up rounding under
different ambient modes, large amounts, invalid values, legacy email payload forms,
slot JSON money types, unchanged count types, response validation and slot-limit
messages that do not advertise a stale price. There are **49 new tests** in total.

The focused selection passed **133 tests** (55 warnings, 214.77 seconds), including
the new modules and existing slot, seller API, notification recovery and queued-email
privacy tests. A test-only refresh-order error was corrected: refreshing the seller
expired its linked wallet, so the wallet must be refreshed last for async assertions.
The runtime API/formatting assertions were already passing in that intermediate run.

Configured Ruff checks pass on both new modules and the money helper; syntax-critical
checks pass on all changed runtime modules. This is not a repository-wide lint/type-
clean claim. Offline contract export succeeded with 190 operations and no application
.env credentials. Existing slot HTTP tests now assert the intentional string contract;
their count, quantity and other behavioral checks were retained.

Full suite: **942 passed, 1 skipped, zero failures/errors; 87.52% coverage**
(8,381/9,576 statements), exit 0 in 930.76 seconds. The unchanged 85% gate passes.
There were 687 warnings, including existing deprecations; this is not warning-free
or release-ready. The inherited obsolete security module remains skipped. Native
financial/concurrency, migration and Redis-worker tests ran. All 12 checkpoint 10
runtime/test file fingerprints match the snapshot captured before the full run.

Saved evidence: [JUnit XML](audit/preship-checkpoint-10-tests-2026-10-17.xml) and
[coverage JSON](audit/preship-checkpoint-10-coverage-2026-10-17.json).

Full-run command, only against disposable local test services:

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://audit:local-audit-only@127.0.0.1:15432/wearhowz_preship_test'
$env:TEST_REDIS_URL='redis://127.0.0.1:16379/15'
.\.venv\Scripts\python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-10-tests-2026-10-17.xml --cov-report=json:docs/audit/preship-checkpoint-10-coverage-2026-10-17.json
```

The test services were loopback-only PostgreSQL 16 and Redis 7 containers with
synthetic credentials/data, separate from development Redis. Recreate disposable
services before rerunning after cleanup.
Both labeled checkpoint 10 containers and their anonymous synthetic-data volumes
were removed after verification; absence was checked. Development `drip_redis`
remains healthy and unchanged. Removed data is reproducible from test fixtures,
not retained as a backup.

## Remaining audit work

F16 remains **partially repaired**. Source inspection still finds integer money
casts in catalogue/seller-product responses and wishlist responses, plus legacy
schema shapes. Recommended next: trace and test those catalogue/wishlist money
paths before canonical public-link configuration and error-envelope consolidation.
They were not repaired or certified by this checkpoint.

Broader ownership/input checks, mixed-operation races, dependency reproducibility,
static/type debt, final consent/retention and managed offboarding, historical
reconciliation, provider acceptance and staging/deployment gates remain open.
Checkpoint 9's historical allocation and zero-total/free-shipping boundaries remain.
Local tests are not delivery acceptance, production approval or a defect-free guarantee.

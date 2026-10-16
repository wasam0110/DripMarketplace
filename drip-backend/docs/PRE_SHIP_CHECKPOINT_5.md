# Backend pre-ship checkpoint 5: queued-email privacy

Implemented/tested 15 October 2026; handoff finalized 16 October 2026. Backend only.
This continues the owner-approved limited privacy
implementation; the 162-item review remains **IN PROGRESS**, not production approval.
No frontend changes, real provider calls, production cleanup, commit or push.

## Implemented

- Kept all six legacy email-task names and argument signatures, but added send-time
  identity checks. Raw queue recipient data is no longer sufficient authorization.
- Verification/reset messages validate token signature, audience, expiry and UUID
  subject; require the matching current, undeleted account; and suppress verified
  accounts/consumed reset links. Case matching follows the existing account lookup.
- Order messages resolve the current owner by order number. Deleted accounts and
  reassigned addresses cannot redirect the old order's messages to a new account.
  Guest messages remain supported only for the matching guest order address.
- Seller approval requires a matching active, undeleted seller/account. Dashboard
  links come from configured FRONTEND_URL rather than an arbitrary legacy queue URL.
- Read names from current DB records, not stale queued profile data. Shipping/COD
  updates honor DB/legacy email opt-outs. Mandatory confirmation/auth notice policy
  is unchanged. Infrastructure/provider failures retry; obsolete jobs are no-ops.
- Hold the user lock through provider handoff to serialize with customer deletion.
  Both orderings have real two-session PostgreSQL tests. Provider requests already
  in flight, including SDK threads surviving cancellation, cannot be recalled.
- Disable worker result retention, including ARQ exhausted-retry/pre-execution
  failure results that otherwise duplicate sensitive original arguments. Durable
  outbox/EmailLog state remains authoritative for its supported delivery flows.

No API or model/schema change was needed; migration head remains 020.
See [customer privacy](CUSTOMER_PRIVACY.md) and [worker recovery](NOTIFICATION_RECOVERY.md)
for rollout, result-polling changes and retained-data boundaries.

## Verification

- Focused run: **84 passed**, including 20 new native queued-email privacy cases and
  four native Redis retry/result-retention cases (two added to the previous pair).
- Provider sends are mocked. PostgreSQL/Redis run in disposable local containers;
  the existing development Redis is untouched. No real messages were sent.
- Targeted Ruff checks pass for the new guard, email tasks and three affected test
  modules. Backend `git diff --check` passes. No repository-wide lint/type claim.
- Full suite: **775 passed, 1 skipped, zero failures/errors; 86.76% coverage**
  (8,286/9,550 statements). The unchanged 85% gate passes. Saved test duration:
  489.622 seconds. The obsolete inherited security module remains skipped.
- Saved evidence: [JUnit XML](audit/preship-checkpoint-5-tests-2026-10-15.xml) and
  [coverage JSON](audit/preship-checkpoint-5-coverage-2026-10-15.json). The original
  session ended before handoff; on 16 October the saved results and SHA-256 hashes
  of all six changed runtime/test files were checked against the running snapshot.
  No runtime/test changes followed validation; only documentation was finalized.
- Offline API export succeeds: **190 operations**, with unchanged migration head 020.

Reproduce the full run from `drip-backend` with disposable test services:

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://audit:local-audit-only@127.0.0.1:15432/wearhowz_preship_test'
$env:TEST_REDIS_URL='redis://127.0.0.1:16379/15'
.\.venv\Scripts\python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-5-tests-2026-10-15.xml --cov-report=json:docs/audit/preship-checkpoint-5-coverage-2026-10-15.json
```

These credentials are synthetic test values, not application settings. Never point
these tests at production. Disposable services are removed after verification.
On 16 October, the two labeled preship5 containers and their anonymous synthetic-data
volumes were removed; development `drip_redis` was left running. Recreate disposable
services to rerun the tests; their removed test data is reproducible, not restored.

## Remaining boundaries and next evidence

- Pending/deferred jobs still contain legacy sensitive arguments until execution/
  expiry. Existing result keys retain their old TTLs. No Redis history/backups or
  provider logs were purged. Operational retention acceptance remains outstanding.
- Authentication jobs retain bounded ARQ retries rather than durable outbox recovery;
  exhausted delivery needs user resend. Ambiguous provider outcomes remain at-least-once.
- No timed financial/dispute/log deletion, historical bulk cleanup, policy-version
  consent storage or new seller/admin offboarding was enabled.
- Next ownership evidence: real two-seller HTTP assertions for all four seller
  analytics routes (overview, revenue, top-products, inventory-health), seller
  low-stock lists, and remaining bulk/filter/input combinations. Existing analytics
  tests cover anonymous/validation contracts and query execution, not all those
  cross-seller combinations. Source contains seller filters; lack of exhaustive
  tests is not evidence of a proven data leak.
- A separate consistency follow-up is visible in source: analytics inventory-health
  uses the constant threshold 5; inventory alerts use per-variant reorder_point.
  Align/test the intended dashboard definition in the next scoped repair.
- The wider audit, monetary presentation/configuration consistency, static/type
  backlog, reproducible dependencies and staging/provider/deployment gates remain open.

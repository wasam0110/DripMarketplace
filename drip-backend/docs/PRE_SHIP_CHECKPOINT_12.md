# Backend pre-ship checkpoint 12: canonical public links and callbacks

18 October 2026. Backend only. The broader 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, real provider call, production mutation, deployment,
commit or push. Local secrets and deployment configuration were not read or changed.

## Repairs

- Verification/reset emails now use `FRONTEND_URL`, not `ALLOWED_ORIGINS[0]`.
  Empty or reordered CORS lists no longer break or redirect these emails. Tokens
  are query-encoded, and generated auth-email URLs are HTML-escaped.
- Shared public URL builders normalize origins and join explicit local paths.
  Order-placement/status links, the legacy seller-approval email and COD cancellation
  site link use the canonical frontend. Existing guest capability generation,
  scoped access, notification preferences, retries and deduplication are unchanged.
- Google authorization and token exchange use the same canonical API callback URI;
  the final browser redirect uses the canonical frontend. State, nonce, PKCE,
  identity verification, account-linking policy and auth cookies are unchanged.
- PayFast hosted form success/failure URLs use the frontend origin; its callback
  URL uses the API origin. Merchant token/hosted/status endpoints, request signing,
  amount verification and reconciliation are not changed or newly provider-certified.
- URL destinations are never selected from request Host/forwarding headers or the
  CORS allowlist. No frontend route was renamed or presumed implemented.

## Configuration compatibility and boundaries

`FRONTEND_URL` and `API_BASE_URL` now accept HTTP(S) **root origins**, optionally
ending in one slash. Scheme/host/default-port normalization is applied. Credentials,
subpaths, query strings, fragments, unsafe characters and invalid ports fail
validation. Both public origins must use HTTPS in production, even when PayFast is
disabled. Development/test HTTP remains supported.

`ALLOWED_ORIGINS` remains a separate browser-access allowlist, normalized and
deduplicated. Credentialed CORS requires explicit origins, not `*`, `null` or paths.
An empty list is valid but does not permit cross-origin browser access. Local defaults
include ports 3000 and 5173; the canonical frontend default remains port 3000.
Operators still need to include their actual browser origins: startup does not
assume every deployment serves browser traffic from the canonical customer origin.

`API_PREFIX` now explicitly requires `/api/v1`: existing auth-cookie scopes and
provider callbacks depend on it. Previously accepting another prefix did not make
those flows work. Custom prefixes/subpath hosting are not implemented here; do not
deploy such a configuration without a separate routing/cookie design and verification.

| Link | Canonical destination |
|---|---|
| Email verification/reset | FRONTEND_URL + /verify-email or /reset-password, encoded token query |
| Order tracking | FRONTEND_URL + /orders/{id}, scoped guest token only for guests |
| Legacy seller approval | FRONTEND_URL + /seller/dashboard |
| Google callback to API | API_BASE_URL + /api/v1/auth/google/callback |
| Google final browser redirect | FRONTEND_URL + /auth/callback |
| PayFast success/failure | FRONTEND_URL + /order/success/{id} or /checkout?payment=failed |
| PayFast callback | API_BASE_URL + /api/v1/payments/callback/payfast |

This is a startup/configuration compatibility tightening, not an API response-type
change or database migration. Restart API and workers with consistent configuration.
Previously sent emails and persisted old notification HTML are not rewritten or
resent. Raw legacy caller-supplied template URLs and other template escaping concerns
are not universally repaired by this change. Real DNS/TLS, frontend routing, Google
console registration, PayFast merchant configuration and email delivery remain
staging/production acceptance gates. Settings cannot prove domain ownership.

## Verification

Before repair, four mocked auth-email cases reproduced two empty-CORS IndexErrors
and two wrong-origin links. After repair, 45 new unit cases cover those links,
reserved token characters, invalid origins, normalization, production HTTPS with
PayFast disabled, CORS handling, unsupported prefixes and path safety.

Six new native cases cover account/guest placement/status links, signed guest
capability scope, repeat-send deduplication and PayFast form URLs with/without a
trailing slash. The existing signed Google new/returning-user and replay-rejection
journey now runs both slash variants and asserts authorization/token-exchange URI
equality and the final canonical redirect. This adds one case, for **52 net new cases**.
Provider HTTP/email calls are mocked; database flows use disposable PostgreSQL.

The final focused run passed **145 tests** (49 warnings, 111.32 seconds), including
the new modules, both signed Google variants, connected-service/task-dispatch tests,
queued-email privacy checks and notification/slot money regressions.

The full suite passed **1,029 tests, 1 skipped, 87.68% coverage** (706 warnings,
989.63 seconds). The unchanged **85%** coverage gate passes. Exact coverage is
8,434/9,619 statements, 87.68063208233704%. Saved XML contains 1,030 cases with zero
failures/errors and the inherited skipped legacy security module
`tests.security.test_auth`. All four real Redis-worker tests ran; the new modules
contributed 45 and six cases, and both signed Google variants passed.

Evidence:

- `docs/audit/preship-checkpoint-12-tests-2026-10-18.xml`
- `docs/audit/preship-checkpoint-12-coverage-2026-10-18.json`

Full-suite command, with synthetic TEST_DATABASE_URL/TEST_REDIS_URL pointing to
loopback-only disposable services, not development/production databases:

```powershell
.\.venv\Scripts\python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-12-tests-2026-10-18.xml --cov-report=json:docs/audit/preship-checkpoint-12-coverage-2026-10-18.json
```

Configured Ruff passed for the new helper/tests; syntax-critical checks passed for
the six modified existing runtime files and two modified existing tests. This is
not a repository-wide lint/type-cleanliness claim. Offline contract export succeeded
with 190 operations and no endpoint/response-schema change. Migration head remains
020. SHA-256 fingerprints for all seven affected runtime files and four affected
test files matched before/after full verification.

Both labeled checkpoint 12 containers and their anonymous synthetic-data volumes
were removed after verification; absence was checked. Development `drip_redis`
remains healthy and unchanged. Removed test data can be regenerated from fixtures;
it was not retained as a backup. No real provider was contacted or enabled.

## Remaining audit work

F16 remains **partially repaired**. Recommended next: consolidate error-response
envelopes. Remaining legacy/untyped money contracts and duplicated policy limits
still require review. Wider ownership/input coverage, mixed-operation races,
dependency reproducibility, static/type debt, final consent/retention, managed
offboarding, historical reconciliation and live acceptance/deployment gates remain.
Earlier zero-total/free-shipping and historical-allocation limits remain unchanged.
Local test success is not production approval or a defect-free guarantee.

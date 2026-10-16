# Backend pre-ship checkpoint 2

14 October 2026. **IN PROGRESS — not backend-complete or production-ready.**
Backend only; no frontend changes, production cleanup, real provider calls, commit or push.

## Implemented

- Upgraded affected dependencies; replaced python-jose/ecdsa with PyJWT and fixed
  RS256 verification, required claims, guest capabilities and Google JWK parsing.
  Existing issuer/audience/cookie compatibility identifiers remain unchanged.
- PayFast success callbacks require an authenticated status lookup. Basket,
  transaction, explicit amount/currency and local order total must match; conflicting
  aliases, missing evidence, provider errors and unrelated transactions cannot credit
  payment. Replay and concurrent-callback regressions pass. Status API configuration
  is required before enabling PayFast. The gateway remains disabled by default.
- Persisted inventory reorder points with bounds and seller scoping, migration 018,
  and per-item low-stock queries. Fixed known notification model/migration mismatches
  (JSONB, UUID default, pending index and named delivery-key uniqueness).
- `/health` returns 503 for a failed bounded database/Redis probe and closes its DB
  generator. Worker partial-startup and shutdown failures now release resources.
- Recursive log redaction, exception stack coordinates without messages/locals, and
  outbound Sentry redaction. No real Sentry event was sent.
- Customer deletion blocks privileged accounts, absent password reauthentication,
  active orders and open financial cases. It removes profile credentials, sessions
  and saved addresses, retains financial identity/history, and serializes with
  authenticated checkout. The old bulk hard-delete job is a non-destructive no-op.
- Updated route introspection for FastAPI's lazy routers; regenerated OpenAPI and
  the inventory of **188 HTTP operations**, with an export completeness assertion.

## Verification

- Full native PostgreSQL 16 / Redis 7 suite: **708 passed, 1 skipped, 580 warnings**;
  **85.93698898942549%** line coverage (7,883 / 9,173 statements). Unchanged 85% gate
  passed. Includes fresh migrations, round trip and all-model-column reads.
- After the final PayFast configuration guard and log-key tightening: **414 unit
  tests passed**. The saved full-suite report precedes that final configuration guard;
  the full native suite was not rerun after it.
- Newly added source/test files pass focused Ruff checks. This is not a repository-
  wide lint/type pass; existing static/type debt remains.
- `pip check` passed. Installed-environment dependency audit reports **zero known
  vulnerabilities**. No complete hashed transitive lock or clean Linux image
  verification is claimed.
- Provider transports were mocked; native concurrency uses controlled synthetic
  contenders, not production traffic or exhaustive crash/interleaving coverage.

Evidence: [test results](audit/preship-checkpoint-2-tests-2026-10-14.xml),
[coverage](audit/preship-checkpoint-2-coverage-2026-10-14.json),
[dependency audit](audit/preship2-dependency-audit-2026-10-14.json).

Full-suite command (with isolated `TEST_DATABASE_URL` and `TEST_REDIS_URL`):

```powershell
.venv/Scripts/python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-2-tests-2026-10-14.xml --cov-report=json:docs/audit/preship-checkpoint-2-coverage-2026-10-14.json
.venv/Scripts/python.exe -m pytest tests/unit -o addopts= -q --disable-warnings
.venv/Scripts/python.exe scripts/export_contract.py
```

## Remaining work — not just production credentials

1. Durable failed-notification recovery/dead-letter handling after publication,
   Redis loss or exhausted worker attempts; legacy notification-preference migration.
2. Complete route-permission/ownership matrix, full schema-drift comparison, and
   mixed-operation races (including deletion versus return/dispute creation).
3. Money-display precision and canonical URL/configuration consistency (F16),
   remaining static/type/test-quality work (F17), reproducible dependency locking
   and clean Linux release-image verification.
4. Complete evidence for the rest of the 162-item checklist; untouched rows remain
   unverified. Historical definition indexes are not a current line-by-line sign-off.
5. Retention policy and cross-table/third-party/backup erasure, legacy deleted data,
   seller/admin offboarding and a fresh OAuth-only deletion reauthentication flow.
   Do not infer legal retention periods or run production purges from these changes.
6. Merchant PayFast response mapping/UAT, connected-service acceptance, historical
   settlement reconciliation, deployment/restore/load/monitoring and independent sign-off.

The next code batch should start with notification recovery and legacy preferences.
See [the exhaustive audit](PRE_SHIP_AUDIT.md) and [known limits](../KNOWN_LIMITS.md).

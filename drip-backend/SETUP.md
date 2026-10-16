# WearHowZ backend setup and release checks

Backend review candidate, refreshed 16 October 2026. Not approved for production; see
[known limits](KNOWN_LIMITS.md) and [latest verification](docs/PRE_SHIP_CHECKPOINT_8.md).
Run commands from `drip-backend`. Never replace an existing local `.env`.

Customer deletion now records retryable external cleanup. Review the
[customer privacy runbook](docs/CUSTOMER_PRIVACY.md), deploy API/workers together and
monitor failed cleanup events. Financial retention expiry and managed seller/admin
offboarding remain disabled pending final policy/design approval.

Checkpoint 5 also adds send-time checks for legacy email jobs and disables ARQ
result retention (including exhausted retries). Restart all workers together;
do not use ARQ result polling as delivery evidence. Consult the
[notification recovery runbook](docs/NOTIFICATION_RECOVERY.md) for the distinction
between durable outbox deliveries and legacy auth jobs that require manual resend.
Old result keys and pending-job payloads are not retroactively purged.

## Local development

Use Python 3.13, PostgreSQL 15+ and Redis 7. On Windows:

```powershell
py -3.13 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
```

For a new installation only, copy `.env.example` to `.env`. Configure your own
database/Redis URLs and RS256 private/public keys. Do not commit keys or credentials.
The database driver URL is `postgresql+asyncpg://...`. Keep `PAYFAST_ENABLED=false`.
Do not reuse the historical sample database password; its owner must rotate it if active.

Configure `FRONTEND_URL`, allowed origins and Google callback URLs consistently.
For reverse-proxy deployments, configure `TRUSTED_PROXY_IPS` with only the actual
trusted proxy addresses/CIDRs (JSON list, default `[]`). Run Uvicorn with
`--no-proxy-headers`, as the Docker command now does, so application validation
receives the socket peer. Proxies must append or replace `X-Forwarded-For`.
The PayFast-specific list overrides the global list when nonempty; do not place
PayFast callback-source addresses in the proxy list. Review ingress topology in
staging: guessing broad trusted networks defeats this protection.
For storage, provision the configured product, brand and avatar buckets; keep the
service-role key server-side. Follow [connected-services setup](docs/CONNECTED_SERVICES_SETUP.md)
for opt-in upload/delete and email checks. Follow [PayFast setup](docs/PAYFAST_SETUP.md)
before enabling the gateway. Live provider accounts are not validated by local tests.

Back up an existing database and inspect the migration state before applying anything:

```powershell
.venv/Scripts/python.exe fix_migration.py --check
.venv/Scripts/python.exe fix_migration.py --upgrade
.venv/Scripts/python.exe -m uvicorn main:app --reload --no-proxy-headers
```

Head revision is `020`. Revisions 019–020 add notification recovery/import bookkeeping
and schema-alignment indexes/checks; review [recovery and migration precautions](docs/NOTIFICATION_RECOVERY.md).
Stop/drain old workers before upgrading. Revision 020 refuses negative review helpful/
unhelpful counts or image sort positions; review existing data before deployment.
Historical payment methods remain readable but cannot be selected for new checkout.
Revision 016 adds refund accounting/allocation records;
revision 017 adds durable notification delivery and preference fields. Review their
batch reports before upgrading an existing database. Revision 018 persists inventory
reorder thresholds (default 5, range 0–999999). Export customized thresholds before
downgrading 018: its downgrade removes that column and its values. Revision 014 adds
the refund requester audit field and queue
indexes. Revision 015 makes return ownership nullable for capability-authorized guest
returns; downgrading it requires reconciling any guest-return rows first.
Existing refund rows copy their latest recorded admin actor into `requested_by`; for an
already-completed historical refund, that is the best recoverable value and may be the
confirmer rather than the original requester. Revision 013 adds notification read/archive
fields. Test rollback only on a disposable copy: downgrading removes the affected fields
and data. Never delete/stamp Alembic's version table to bypass migrations. See the
legacy-settlement restriction below.

The Linux worker entrypoint is `python -m arq app.tasks.worker.WorkerSettings`.
`/health` returns HTTP 503 when its bounded database or Redis probe fails; use it for
readiness, not as a dependency-independent process-liveness probe. The legacy
`cleanup_soft_deleted_users` worker is intentionally non-destructive pending an
approved retention policy. Customer self-deletion removes credentials/profile fields
and saved addresses while retaining the user key and financial records. Seller/admin
offboarding is not supported by that customer endpoint. Google-only customers must
set a password before requesting deletion; a fresh OAuth reauthentication deletion
flow is not implemented.

PayFast success callbacks now require a successful authenticated status lookup that
explicitly matches basket, transaction, amount and currency. Missing provider evidence
does not default to the local amount or PKR. Confirm merchant status-API access and
actual response field mapping in UAT before enabling PayFast; credentials alone are
not proof of compatibility.

Orphan-image deletion is disabled by default and must remain disabled until its storage
smoke test passes. For local review, use disposable services and fake provider transports.
ARQ 0.26.1 has Unix-signal assumptions on Windows;
the Redis tests explicitly control worker lifecycle rather than calling its Unix close path.

Create an admin explicitly with `python seed_users.py --email YOUR_EMAIL --role admin --verified`.
The utility prompts for a password. Use an address you control. Seller registration
must use the API to create the linked brand and wallet. Two-factor policy is admin-only.

## Reproducible isolated verification

The dedicated Compose project binds only loopback ports 55432 and 56379, has no
development volumes, and uses disposable PostgreSQL storage. These credentials are
test-only. Do not change the commands to target production.

```powershell
docker compose -p wearhowz-task6 -f compose.test.yml up -d --wait
$env:TEST_DATABASE_URL='postgresql+asyncpg://test:test@127.0.0.1:55432/wearhowz_test'
$env:TEST_REDIS_URL='redis://127.0.0.1:56379/15'
.venv/Scripts/python.exe -m pytest --tb=short --disable-warnings --cov-report=json:coverage.json --cov-report=term:skip-covered --junitxml=docs/test-results.xml
```

The unchanged full-suite gate is 85%. Database tests create and remove only their
random test schemas; the database name must end in `_test` and must not match
`DATABASE_URL`. Most Redis dependencies use fakeredis; the dedicated worker tests use
real Redis DB 15 with unique job/queue keys. Never run them on a shared Redis deployment.
Without the explicit test URLs, environment-dependent tests skip; that is not release evidence.

Useful focused runs (not substitutes for the full coverage gate):

```powershell
.venv/Scripts/python.exe -m pytest tests/integration/test_release_native.py tests/integration/test_worker_redis.py --no-cov
.venv/Scripts/python.exe -m ruff check app tests scripts
.venv/Scripts/python.exe -m compileall -q app scripts tests
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m pip_audit --format json --output docs/dependency-audit.json
.venv/Scripts/python.exe scripts/export_contract.py
docker build -t wearhowz-task6-api:review .
docker build -f Dockerfile.worker -t wearhowz-task6-worker:review .
```

The dependency audit queries package advisory services and is expected to exit nonzero
until its findings are resolved. Do not suppress findings to make the gate pass.
The contract exporter is offline and ignores `.env`. Inventory includes hidden routes
as well as public OpenAPI operations. It lists route dependencies, not every resource
ownership/business rule. Money is in PKR and may serialize as decimal strings.
Guest-order access requires `X-Guest-Token`; manual receipt endpoints record an
external transfer rather than initiating one.

To stop and remove only these disposable test containers and their test data:
`docker compose -p wearhowz-task6 -f compose.test.yml down`.
Do not use the development Compose file for this cleanup.

## Historical settlement reconciliation gate

Revision 012 marked historical `commission_ledger.released_at = settled_at` because
old release transactions lacked a reliable ledger reference. Preserve that protection.
No historical ledger has been reopened or reconciled in this review.

Before reopening any legacy pending amount, the accounting owner must provide a
read-only snapshot of commission ledgers, seller wallets, wallet transactions,
refunds, payouts and corresponding bank/provider receipts. Reconcile each seller and
seller order: original net entitlement, prior hold releases, confirmed refunds,
pending/completed payouts, adjustments and any already-paid-out refund shortfall.
Document unmatched entries and approve a per-entry correction plan. Do not infer that
every marked ledger actually paid out, or bulk-clear `released_at`. Test any approved
correction on a restored copy with before/after totals and duplicate-run assertions.
An authorized, audited reconciliation is a separate prerequisite to enabling old balances.

## Review package

`python scripts/package_review.py` creates a source ZIP and a SHA-256 manifest in
`dist/`. It does not install, migrate, deploy, commit or push. Extract to a new folder
for review; do not overwrite a working installation. Configuration, Git history,
virtual environments, private keys and caches are excluded. Resolve all release
blockers and rerun verification before calling any artifact production-ready.

# WearHowZ backend setup and release checks

Task 6 review candidate, 7 October 2026. Not approved for production; see
[known limits](KNOWN_LIMITS.md) and [verification report](docs/TASK_6_REPORT.md).
Run commands from `drip-backend`. Never replace an existing local `.env`.

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
For storage, provision the configured product, brand and avatar buckets; the new
`SUPABASE_STORAGE_BUCKET_AVATARS` defaults to `avatars`. Keep the service-role key
server-side. Live Google, Supabase and Resend credentials are not validated by local tests.

Back up an existing database and inspect the migration state before applying anything:

```powershell
.venv/Scripts/python.exe fix_migration.py --check
.venv/Scripts/python.exe fix_migration.py --upgrade
.venv/Scripts/python.exe -m uvicorn main:app --reload
```

Head revision is `013`. It adds notification read timestamps and archive flags;
existing read notifications are backfilled. Test rollback only on a disposable copy:
downgrading 013 removes these columns and their data. Never delete/stamp Alembic's
version table to bypass migrations. See the legacy-settlement restriction below.

The Linux worker entrypoint is `python -m arq app.tasks.worker.WorkerSettings`.
Do not start the scheduled worker against valuable storage until the orphan-image
cleanup limitation in KNOWN_LIMITS.md is resolved. For local review, use disposable
services and fake provider transports. ARQ 0.26.1 has Unix-signal assumptions on Windows;
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

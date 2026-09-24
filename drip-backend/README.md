# WearHowZ backend

This is the full backend source with the accumulated marketplace repairs and Task 1 verification. It can be committed to your existing repository. It is still a development build: refund accounting, the PayFast merchant integration and production release checks remain open. PayFast stays disabled by default.

## Applying the supplied terminal update

The separate WearHowZ update bundle applies these changes to the original uploaded backend. It checks each affected file, preserves local environment files and Git metadata, and backs up affected files outside the repository before applying updates. Follow the bundle's APPLY_UPDATE.md instructions. If it reports a local-file conflict, resolve that file before retrying; there is no forced-overwrite mode.

## Local setup

Use Python 3.12 or 3.13, PostgreSQL 15+ and Redis 7. The verified application tests used Python 3.12. Existing Dockerfiles target Python 3.13 and were not container-built in this environment.

1. Create/activate a virtual environment and run `python -m pip install -r requirements-dev.txt`.
2. Copy `.env.example` to `.env` only if you do not already have a local environment file. Fill in your own database, Redis, RS256 signing keys and provider settings. Keep `.env` and private keys out of Git. For a fresh local database, `docker compose up -d postgres redis` uses the development database settings in the example.
3. Use a backed-up development database to inspect `python fix_migration.py --check`, then apply pending migrations with `python fix_migration.py --upgrade`. This performs normal Alembic upgrades. Do not use an old script that deletes/stamps the migration version table. For an existing populated database, inspect and reconcile historical wallet settlements before upgrading a live environment; revision 012 intentionally prevents automatic duplicate release of legacy ledger entries.
4. Start the API: `python -m uvicorn main:app --reload`.
5. Start the background worker separately: `arq app.tasks.worker.WorkerSettings`.

The original configuration included an embedded database credential. Rotate it if active, including copies in repository history or old deployments. The source update removes embedded credentials from the sample and legacy utilities; it does not rotate a provider password for you.

## Bootstrap account

`python seed_users.py --email your-address@example.com --role admin --verified`

The utility reads DATABASE_URL from your environment/local `.env`, prompts for a password without displaying it, and creates only the explicitly requested account. Use `--verified` only for an address you control. Repeating it for an existing email leaves that account unchanged, including its role and password. It has no built-in usernames or passwords. Create sellers through `/api/v1/seller/register` so their brand profile and wallet are created together.

## Validation and API notes

Before the packaging utility changes, Task 1 completed with 412 tests passing, one security test skipped and 71.16% coverage. The existing 85% coverage gate remains a release blocker. Database verification used PGlite PostgreSQL/WASM and isolated in-memory Redis, not native PostgreSQL concurrency or live providers. See `UPDATE_NOTES.md` for the current delivery checks.

For native tests, set TEST_DATABASE_URL to a dedicated PostgreSQL database ending in `_test`, separate from DATABASE_URL, then run `python -m pytest`. Tests create disposable schemas; never point them at a production database.

Wallet, payout, order and dashboard money fields may be decimal strings in JSON and are in PKR units, not cents/paisa integers. Guest-order read/payment requests require X-Guest-Token. Completed manual payout/refund/registration/COD receipts record transfers made outside the app; these endpoints do not initiate a bank transfer. Refund ledger reconciliation and provider verification remain unfinished.

The terminal updater does not run database migrations, install dependencies, change your local `.env`, or push to Git. Committing and pushing source is separate from deploying it. If your branch auto-deploys on push, use a development branch while the remaining tasks are open.

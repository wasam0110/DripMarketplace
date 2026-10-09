# WearHowZ backend

This checkout contains the backend marketplace repairs, Task 3/4 provider hardening and Task 6 release-check work. The full suite passes the unchanged 85% coverage gate, but release approval remains blocked. PayFast stays disabled by default. See [SETUP.md](SETUP.md), [PayFast setup](docs/PAYFAST_SETUP.md), [connected-services setup](docs/CONNECTED_SERVICES_SETUP.md), [KNOWN_LIMITS.md](KNOWN_LIMITS.md), and the [Task 6 report](docs/TASK_6_REPORT.md).

## Applying the supplied terminal update

The separate WearHowZ update bundle applies these changes to the original uploaded backend. It checks each affected file, preserves local environment files and Git metadata, and backs up affected files outside the repository before applying updates. Follow the bundle's APPLY_UPDATE.md instructions. If it reports a local-file conflict, resolve that file before retrying; there is no forced-overwrite mode.

## Local setup

Use Python 3.13, PostgreSQL 15+ and Redis 7. Task 6 tests use Python 3.13.14 and native PostgreSQL/Redis in isolated local containers. Follow SETUP.md for reproducible test and build checks.

1. Create/activate a virtual environment and run `python -m pip install -r requirements-dev.txt`.
2. Copy `.env.example` to `.env` only if you do not already have a local environment file. Fill in your own database, Redis, RS256 signing keys and provider settings. Keep `.env` and private keys out of Git. For a fresh local database, `docker compose up -d postgres redis` uses the development database settings in the example.
3. Use a backed-up development database to inspect `python fix_migration.py --check`, then apply pending migrations with `python fix_migration.py --upgrade`. This performs normal Alembic upgrades. Do not use an old script that deletes/stamps the migration version table. For an existing populated database, inspect and reconcile historical wallet settlements before upgrading a live environment; revision 012 intentionally prevents automatic duplicate release of legacy ledger entries.
4. Start the API: `python -m uvicorn main:app --reload`.
5. Review KNOWN_LIMITS.md before starting the worker: `arq app.tasks.worker.WorkerSettings`. Orphan-image deletion remains disabled until `SUPABASE_ORPHAN_CLEANUP_ENABLED=true` is explicitly set after the documented storage smoke test.

The original configuration included an embedded database credential. Rotate it if active, including copies in repository history or old deployments. The source update removes embedded credentials from the sample and legacy utilities; it does not rotate a provider password for you.

## Bootstrap account

`python seed_users.py --email your-address@example.com --role admin --verified`

The utility reads DATABASE_URL from your environment/local `.env`, prompts for a password without displaying it, and creates only the explicitly requested account. Use `--verified` only for an address you control. Repeating it for an existing email leaves that account unchanged, including its role and password. It has no built-in usernames or passwords. Create sellers through `/api/v1/seller/register` so their brand profile and wallet are created together.

## Validation and API notes

Historical Task 1 verification used PGlite PostgreSQL/WASM with 412 passing tests and 71.16% coverage. Task 6 superseded that evidence with 570 passing tests, one skipped security module and 85.62% coverage, using native PostgreSQL and dedicated Redis worker tests. See `docs/TASK_6_REPORT.md`; `UPDATE_NOTES.md` describes the historical terminal bundle, not this review package.

The user-approved Task 7 backend follow-ups fix dispute-message ownership, add authoritative guest quotes, add durable admin refund reads, and complete B4 with enriched admin return detail, seller-owned return decisions, admin dispute detail/replies, and signed-capability guest cancellation/returns. Revision 014 preserves separate refund requester/confirmer identities; revision 015 permits guest returns without inventing user ownership. The fresh 10 October suite passed **602 tests, 1 skipped, 85.59% coverage**. See [the Task 7 review](docs/TASK_7_DESIGN_REVIEW.md) for verification and remaining design work. Older review ZIPs do not include these follow-ups; the frontend remains untouched.

For native tests, set TEST_DATABASE_URL to a dedicated PostgreSQL database ending in `_test`, separate from DATABASE_URL, then run `python -m pytest`. Tests create disposable schemas; never point them at a production database.

Wallet, payout, order and dashboard money fields may be decimal strings in JSON and are in PKR units, not cents/paisa integers. Guest-order read/payment requests require X-Guest-Token. Completed manual payout/refund/registration/COD receipts record transfers made outside the app; these endpoints do not initiate a bank transfer. Synthetic refund accounting is tested; historical ledger reconciliation and live provider verification remain unfinished.

The terminal updater does not run database migrations, install dependencies, change your local `.env`, or push to Git. Committing and pushing source is separate from deploying it. If your branch auto-deploys on push, use a development branch while the remaining tasks are open.

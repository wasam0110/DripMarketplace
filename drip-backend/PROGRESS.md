# WearHowZ implementation status

Updated 8 October 2026. Backend-only work now includes Task 3/4 provider hardening and the Task 6 release checks. No frontend work was performed.

The refreshed full suite passes the unchanged coverage gate: **570 passed, 1 skipped, 85.62%**. Native PostgreSQL payment/accounting races and Redis retry checks pass. OpenAPI, endpoint inventory, setup and known limits are current. See [the verification report](docs/TASK_6_REPORT.md).

Task 3 is implementation-ready against PayFast's published hosted-checkout protocol, including callback validation and status reconciliation. Task 4's Google, Supabase, Resend and worker paths are hardened, and destructive storage cleanup is safe-by-default and opt-in. Both tasks still require controlled live acceptance with the user's provider credentials; PayFast remains disabled.

Task 6 is **not release-complete** because dependency advisories, historical settlement reconciliation and other documented limits remain. No historical balance was reopened, live migration applied, repository pushed or deployment published.

The two original utility filenames are retained with safe implementations: seed_users.py prompts for explicitly configured credentials, and fix_migration.py delegates to normal Alembic commands. Neither embeds a database password.

See [SETUP.md](SETUP.md), [KNOWN_LIMITS.md](KNOWN_LIMITS.md), [PayFast setup](docs/PAYFAST_SETUP.md), [connected-services setup](docs/CONNECTED_SERVICES_SETUP.md) and [the Task 6 report](docs/TASK_6_REPORT.md). UPDATE_NOTES.md describes the historical terminal bundle. Tasks 7-12 remain pending user selection.

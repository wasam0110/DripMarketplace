# WearHowZ implementation status

Updated 10 October 2026. Backend-only work includes Task 3/4 provider hardening, Task 6 release checks and the user-approved B1–B4 backend fixes found during Task 7. No frontend implementation was performed.

The fresh 10 October full suite passes the unchanged coverage gate: **602 passed, 1 skipped, 85.59%**, using native PostgreSQL and dedicated Redis tests. B1 passed **53 focused tests**, including 18 new ownership cases. B2 added four guest-quote regressions. B3 adds three admin-only refund reads, two regressions and revision 014. B4 now includes enriched admin return detail, seller-owned return decisions, admin dispute detail/replies, signed-capability guest cancellation/returns, conflict-safe return transitions and revision 015. Its five workflow regressions and native two-session decision race pass. The OpenAPI and endpoint exports now contain 188 operations. See [the Task 7 verification](docs/TASK_7_DESIGN_REVIEW.md) and [the historical Task 6 verification report](docs/TASK_6_REPORT.md), which retains the earlier 570-pass result.

Task 3 is implementation-ready against PayFast's published hosted-checkout protocol, including callback validation and status reconciliation. Task 4's Google, Supabase, Resend and worker paths are hardened, and destructive storage cleanup is safe-by-default and opt-in. Both tasks still require controlled live acceptance with the user's provider credentials; PayFast remains disabled.

Task 6 is **not release-complete** because dependency advisories, historical settlement reconciliation and other documented limits remain. No historical balance was reopened, live migration applied, repository pushed or deployment published.

The two original utility filenames are retained with safe implementations: seed_users.py prompts for explicitly configured credentials, and fix_migration.py delegates to normal Alembic commands. Neither embeds a database password.

Task 7 started with a read-only Canva/API alignment review. The first pass covers the text of 135 static design pages and four visual thumbnails; it is not complete visual QA or frontend implementation. The identified B1–B4 backend gaps are fixed under the user's explicit approval. Asset extraction, complete visual/interaction review and design-state alignment remain outstanding. See [the Task 7 design review](docs/TASK_7_DESIGN_REVIEW.md). The old frontend remains untouched; a replacement is intended for a separate folder. Task 7 is in progress; Tasks 8-12 have not started.

See [SETUP.md](SETUP.md), [KNOWN_LIMITS.md](KNOWN_LIMITS.md), [PayFast setup](docs/PAYFAST_SETUP.md), [connected-services setup](docs/CONNECTED_SERVICES_SETUP.md) and [the Task 6 report](docs/TASK_6_REPORT.md). UPDATE_NOTES.md describes the historical terminal bundle.

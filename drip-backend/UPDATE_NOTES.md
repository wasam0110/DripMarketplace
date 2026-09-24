# WearHowZ source update — 24 September 2026

This delivery applies all accumulated backend repairs through Task 1 to the original uploaded backend, with safe repository utilities restored. It is suitable for committing to a development branch. The remaining marketplace/release tasks have not been completed.

## Included changes

- Authentication/session validation, password-reset token handling, guest-order capability tokens and Google OAuth scaffolding.
- Catalogue/storefront routes, variant and image controls, real review moderation and analytics routes/data.
- Checkout prices/coupons/stock reservations, order fulfilment transitions, COD collection records, pending/manual refund receipt flow, payment validation and disabled-until-verified PayFast support.
- Seller registration payments, configurable pricing/shipping/commission, zero-fee onboarding, slots, payout receipts and precise wallet/dashboard money fields.
- Migration 012 and the historical migration 009 enum-creation correction; regression tests and isolated test configuration.
- Safe replacements for the original seed_users.py and fix_migration.py utilities; no hardcoded database credentials or built-in account passwords.
- Corrected .gitignore, added .dockerignore, development database values aligned between .env.example and docker-compose.yml, and current setup/progress documentation.

## Verification

The latest complete pytest run: **415 passed, 1 skipped**. The existing 85% coverage gate still fails: **70.48% measured in this run**. The skipped security test requires its integration environment. The prior Task 1 run measured 71.16%; the latest run is the current report, and neither meets the release gate.

The three new repository-utility checks passed, including persisted proof that the seed utility cannot overwrite an existing account's password or elevate its role. The terminal updater's nine offline tests passed: read-only check, backups, idempotency, local conflict refusal, local environment/Git preservation, line-ending compatibility, tamper checks, protected paths/symlinks and rollback on a handled write failure.

The updated migration was previously verified on a fresh database, then through 012 → 011 → 012; all 39 model tables were readable. Database execution used PGlite PostgreSQL/WASM with a test adapter, and Redis was substituted with isolated in-memory test storage. Native PostgreSQL concurrency, live services and Docker image builds were not verified here.

## API/deployment limits

Money fields are PKR units and may serialize as decimal strings. Guest-order read/payment calls require X-Guest-Token. Manual receipt endpoints record transfers made outside the app. Refund ledger reconciliation remains task 2; PayFast remains disabled until task 3; provider setup and production release checks remain later tasks.

Source replacement does not migrate an existing database. Back it up, review the new migration, and test the upgrade against a copy before using it with live data. Historical wallet settlements need reconciliation because the new release marker deliberately avoids automatically releasing old earnings twice.

Your local .env and Git configuration are preserved by the updater. Rotate the database credential embedded in the original upload if still active; removing it from revised files does not remove it from old commits or deployments.

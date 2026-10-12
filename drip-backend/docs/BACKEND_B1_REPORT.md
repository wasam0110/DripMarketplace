# Backend repair batch 1 report

Completed 12 October 2026. Scope: post-review findings F01-F03 plus the migration-isolation defect exposed by final verification. This batch is separate from the earlier Canva/API task labels. No frontend source, provider configuration, live data, deployment, commit or push was included.

## Result

### F01 — payout completion integrity

The compatibility endpoint `POST /api/v1/admin/payouts/{payout_id}/complete` now requires `payment_reference` and delegates to `WalletService.admin_complete_payout`, the same locked state machine used by the newer wallet endpoint. Requested and rejected payouts cannot be completed; same-reference replay is idempotent; a conflicting reference is rejected. The compatibility payout list preserves Decimal amounts and includes the stored transfer reference.

The compatibility URL and `payment_reference` JSON name remain available. Its stricter requirement is intentional: the former optional field was ignored and permitted receipt-less completion. The offline OpenAPI export records this requirement.

### F02 — atomic return-linked refund request

`PaymentService.refund` now accepts an optional `return_id` and explicit commit ownership. `ReturnService.process_refund` creates the pending refund with its return association while its return/payment locks remain held, then commits once at the outer boundary. Idempotent retries keep one linked request; an older unlinked request with the same return idempotency key can be linked within the caller's transaction.

Failure injection immediately after the inner flush, followed by rollback, leaves no refund row. A pending request still does not claim the external transfer occurred; confirmation remains a separate receipt-bearing action.

### F03 — accurate wallet audit balance

Refund reversal now captures pending and available balances before the SQL update. The transaction's `balance_after` is the actual combined post-transaction wallet balance, independent of SQLAlchemy identity-map synchronization. The intended debit amount remains recorded even where the platform absorbs a seller-funds shortfall, preserving the existing policy for later reconciliation.

## Files

Application:

- `app/api/v1/admin/payouts.py`
- `app/services/wallet_service.py`
- `app/services/payment_service.py`
- `app/services/return_service.py`
- `app/services/commission_service.py`

Regression/contract documentation:

- `alembic/versions/009_create_returns.py`
- `tests/integration/test_b1_financial_integrity.py`
- `tests/integration/test_release_native.py`
- `scripts/export_contract.py`
- `docs/openapi.json`
- the backend review/progress/limit documents and [source supplement](audit/b1-changes.md)

No schema change or new Alembic revision was required. Revision 009's existing enum-presence check is now scoped to `current_schema()`, so an identically named enum in an unrelated PostgreSQL schema cannot break a fresh migration. The native migration test creates that conflict deliberately before exercising the fresh upgrade and 015 -> 012 -> 015 round trip.

## Verification

- 8/8 new focused PostgreSQL cases pass: compatibility payout state/receipt/precision, linked refund success/replay, failure rollback, and pending-only/available-only/mixed/shortfall balances.
- 10/10 affected existing payout/refund/return/concurrent-confirmation regressions pass.
- The native completion-versus-rejection race passes: exactly one transition succeeds and the final balance matches that state.
- Fatal-error Ruff selection passes for all changed application/test files. Full configured Ruff still has inherited findings documented by the review.
- Unit suite: 347 passed, 27 warnings.
- Native migration isolation regression: 1 passed, 24 warnings.
- Final full suite: **611 passed, 1 skipped, 596 warnings in 896.20 seconds**.
- Coverage: **85.70%** (7,356/8,583 statements), so the unchanged 85% gate passes.

All database tests use disposable schemas in the dedicated `wearhowz_test` database. Provider APIs and development/production data are not used.

## Remaining backend work

Batch 1 does not resolve F04-F17. Next is [repair batch 2](BACKEND_REPAIR_QUEUE.md): seller-specific refund allocation, finite holds/releases and complete net accounting. Shipping allocation, shortfall/debt policy and historical ledger reconciliation require explicit policy/evidence. Live PayFast/Google/Supabase/Resend acceptance and deployment checks remain separate pre-production gates.

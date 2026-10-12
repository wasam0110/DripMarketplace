# Backend batch-1 source supplement

Generated 12 October 2026. This supplement supersedes the original review-index entries for the files below and adds the new regression module. It records the batch-1 snapshot, not a claim that later repair batches are complete.

## Application changes

- `app/api/v1/admin/payouts.py`: 98 lines; SHA-256 `c69453c88496e714dfda56192e42a8eae62e59264258838747ce8fa9e11679f7`. `PayoutCompletionRequest` is lines 22-26; the precision-preserving list is lines 30-53; the compatibility completion route is lines 71-82.
- `app/services/wallet_service.py`: 314 lines; SHA-256 `32f9d099386f84b5fa8cf41b002d1660c46ba36503d4b1c7f1eb9a2822961839`. `admin_complete_payout` is lines 290-314 and owns the locked approval/status/receipt/idempotency transition.
- `app/services/payment_service.py`: 685 lines; SHA-256 `e2c096413b7acef3b92808b712360b8c29c604850f016003ae6b7cd4271638ba`. `refund` is lines 365-426 and accepts an optional return link plus explicit caller-owned commit behavior.
- `app/services/return_service.py`: 690 lines; SHA-256 `922d8848517dd65fe262cfcab4007ba5d3c14b3ab39d89e71cc0ede52f3ad5cf`. `process_refund` is lines 444-480 and commits refund creation with its return association once.
- `app/services/commission_service.py`: 403 lines; SHA-256 `73d4e4c693a2d2afe40b8dd7f09631c32b59b3904ebb0c7898db850bbd433f31`. `_apply_debit` is lines 314-385 and calculates combined `balance_after` from pre-update wallet snapshots.

## Regression changes

- `tests/integration/test_b1_financial_integrity.py`: 245 lines; SHA-256 `ac330d1c52329fa44fcbd01fbadd17a96aee1ce7d47edb85020d9a5f02a99e06`. Eight collected cases cover legacy payout behavior, atomic return-refund persistence/failure and pending/available/mixed/shortfall audit balances.
- `tests/integration/test_release_native.py`: 418 lines; SHA-256 `a81d218d92fd376e47fcab5546fb1bfb41b3b1e214d6aba43987034675c58b06`. `test_concurrent_payout_completion_and_rejection_have_one_winner` is lines 103-163; `test_fresh_migrations_round_trip_and_all_model_columns` is lines 361-394 and deliberately places same-named enums in another schema.

## Migration correction

- `alembic/versions/009_create_returns.py`: 139 lines; SHA-256 `495d0aa80753dc26d14b00c28c54b1e66a2a75690490fb7fb7e365a3d313bc43`. `upgrade` is lines 23-129; its enum lookup is scoped to `current_schema()` so unrelated schemas cannot suppress local type creation. No new revision or schema shape was introduced.

## Contract tooling

- `scripts/export_contract.py`: 104 lines; SHA-256 `4367c4aea5b8f81a302a560c11043038f20f922da74e606f1e3e06017133e882`. Required test-only settings use explicit non-secret placeholders so offline OpenAPI/endpoint export remains reproducible without reading `.env`.

All paths are backend-relative. See [batch-1 report](../BACKEND_B1_REPORT.md) for behavior and verification, and the [repair queue](../BACKEND_REPAIR_QUEUE.md) for remaining work.

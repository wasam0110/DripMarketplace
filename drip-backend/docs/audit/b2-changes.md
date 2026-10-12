# Backend batch-2 source supplement

Generated 13 October 2026. This supplement supersedes the original review-index entries for the files below and adds revision 016. It records the batch-2 snapshot, not a claim that later repair batches are complete.

## Core accounting and migration

- `app/models/wallet.py`: 283 lines; SHA-256 `962083333dc472a43283c258c53f46a08fe8c36831603e1c1053f2e1989304e9`. `CommissionLedger` starts at line 37, `RefundAccounting` at line 123 and `RefundAllocation` at line 176.
- `app/models/payment.py`: 116 lines; SHA-256 `f04d6b7b512e2d276b423cba4202614d56249114f36561372277faf572e8beee`. The refund-to-accounting relationship is at line 109.
- `app/services/commission_service.py`: 809 lines; SHA-256 `eff71169253cbfd22b2e25e27495404aa58dc40ea05b1488c27d0e6a305bcc14`. Settlement starts at line 37, allocation creation at line 151, allocation application at line 307, mature release at line 442 and refund reversal at line 538.
- `app/tasks/wallet_tasks.py`: 39 lines; SHA-256 `53748951499766be4338b2d3df29441a7a5986a8ae61145ac42a81ae18347088`. The release task delegates to the service-level release implementation.
- `alembic/versions/016_refund_accounting.py`: 176 lines; SHA-256 `d35ed941e6b57a990ea961e6f1e6198a0b8e86081835ef0139e2a59a1da9eb99`. Upgrade starts at line 27 and adds the ledger rollups, refund accounting/allocation tables and conservation constraints.

## API and reporting

- `app/repositories/payment_repo.py`: 176 lines; SHA-256 `0b21d0537ffff8a754ff158e6c13884ab1fad31e0fc18171e91eb771d331ad6c`.
- `app/repositories/wallet_repo.py`: 184 lines; SHA-256 `2c214d40b367b5fddbceece2cf41e96a05a9cd9ba960aa31d0722144edd4edbd`.
- `app/schemas/payment.py`: 188 lines; SHA-256 `62d029b2e910e662d1d08c94a81e2c120ab9294aa283b8424d172132bf0ad27a`. Refund allocation and accounting responses start at lines 73 and 86.
- `app/schemas/wallet.py`: 121 lines; SHA-256 `d9ee4ee9516f14d16bc92c5758a185de8d5451f34f73b4acb6841d363f6ab3fa`.
- `app/services/payment_service.py`: 717 lines; SHA-256 `9368ce5469834072130b7de869ea5414ac6e19bee203ac623ad1466d968d0c3d`.
- `app/services/admin_service.py`: 472 lines; SHA-256 `2fd981ea9fcabfaf2d27dddd3ff8eb6920ec4adc935d0baf75bc2941ef86536f`.
- `app/services/wallet_service.py`: 324 lines; SHA-256 `3f7f875b35c3b89de798e3500ac9296e478d5674fce6f0b808e53ece625b69e3`.
- `app/services/seller_service.py`: 244 lines; SHA-256 `e35b29cd11663b116d5bc32a696c38bdd3fc6c11fa054707b995a3780b1f56e3`.
- `app/services/analytics_service.py`: 601 lines; SHA-256 `f6bb48b7f691f3bcb3b937b206922db3bc7b3299268ce45ed3e7f509e261a571`.

These repository, schema and service changes eager-load accounting for async responses, expose original/reversal/net fields, and aggregate net ledger values in wallet, seller and analytics reporting.

## Regression changes

- `tests/integration/test_marketplace_regressions.py`: 1,967 lines; SHA-256 `750c41e3284ea63b46e80cafe862ff21e8944b369f83f273a4604afaff3b503f`. Added cases cover persisted pending/settled accounting, multi-brand isolation and rounding, shipping, recovery/shortfall, partial release, real return/dispute holds, admin response shape, idempotency and stock-credit protection.
- `tests/unit/test_commission_service.py`: 253 lines; SHA-256 `60fba2f9d03bbef574fb52c35ab9ad34207863cc97ff9b60d90d2cfbe6d3e3ef`. The test repository double returns real ledger entities so hybrid net calculations and new rollups are exercised.

All paths are backend-relative. `app/services/customer_service.py` had a separate pre-existing local edit and is intentionally excluded. See the [batch-2 report](../BACKEND_B2_REPORT.md) for behavior and verification, and the [repair queue](../BACKEND_REPAIR_QUEUE.md) for remaining work.

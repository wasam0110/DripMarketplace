# Backend batch-3 source supplement

Generated 13 October 2026. This supplement supersedes the original review-index and earlier supplement entries for the files below. It records the batch-3 snapshot, not a claim that later repair batches are complete.

## Application change

- `app/services/return_service.py`: 743 lines; SHA-256 `c3f757e8d58254bc60638a607c48f264e05825be7debcd94d3f57af2949fe8fa`. Return creation starts at line 101, dispute resolution at line 509 and shared locked quantity validation at line 568. Customer-win resolution revalidates and approves atomically; seller-win remains rejected.

## Regression changes

- `tests/integration/test_b3_dispute_resolution.py`: 159 lines; SHA-256 `1b60454dfebfb45372ea6ba615e2c36bf7de0d22ea2151fd091c9d8aa77b0dd4`. The complete customer-win/manual-refund journey starts at line 49 and seller-win behavior at line 126.
- `tests/integration/test_release_native.py`: 514 lines; SHA-256 `d93a6ba50d84a94f628f6ca4238829265d4fa21ec9937d222f9076ea8b246c12`. The two-session customer-win versus competing-quantity race starts at line 280.

All paths are backend-relative. See the [batch-3 report](../BACKEND_B3_REPORT.md) for behavior and verification, and the [repair queue](../BACKEND_REPAIR_QUEUE.md) for remaining work.

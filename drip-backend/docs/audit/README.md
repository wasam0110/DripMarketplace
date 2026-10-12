# Backend definition index

Validated 13 October 2026: the original review index covers all 163 pre-repair Python files and 1,953 class/function definitions. Backend repair batches changed indexed files and added regression/migration source; the [batch-1](b1-changes.md), [batch-2](b2-changes.md) and [batch-3](b3-changes.md) supplements supersede the affected entries. Hashes in each supplement describe that batch's verified snapshot.

This generated index lists source ranges, annotated field names, backend imports and selected syntactic calls. It is not a resolved call graph, an independently authored explanation of every statement, or proof that a function works. Use the [walkthrough](../BACKEND_WALKTHROUGH.md) for system flow and the [findings](../BACKEND_DEEP_REVIEW.md) for correctness issues.

- [Entry points, dependencies and core](entry-core.md)
- [HTTP routes](routes.md)
- [Services A–M](services-a.md)
- [Services N–Z](services-b.md)
- [Repositories](repositories.md)
- [Models](models.md)
- [Schemas](schemas.md)
- [Workers and integrations](workers-integrations.md)
- [Migrations and scripts](migrations-scripts.md)
- [Unit tests](tests-unit.md)
- [Integration, security, load and shared test fixtures](tests-other.md)

Frontend files, local secrets, virtual environments, caches and third-party dependency source are outside this backend source index. Source docstrings are quoted as navigation context and may describe intent rather than current behaviour.

Runtime evidence for this review: [verification summary](verification-2026-10-12.json) and [native financial reproductions](native-probes-2026-10-12.json). Passing the existing suite does not clear the recorded findings.

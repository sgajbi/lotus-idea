# Refactor Decisions

Record architecture, API, security, observability, testing, CI, and documentation decisions that
change the repository's bank-buyable posture.

Do not use this file for aspirational claims. Every entry should name code, tests, and validation
evidence or explicitly mark the item as planned.

## 2026-07-04: Review Workflow API Operation Boundary

The review-action and feedback API routes now share
`src/app/api/review_workflow_operations.py` for caller-header parsing, mutating
review capability checks, body authorized-scope subset validation, idempotency
validation, durable-write blocking, product-safe persistence problem mapping,
and operation-event mapping.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate service, a queue boundary,
or independent scaling. The runtime split remains unjustified until workload,
failure-isolation, ownership, or operability evidence shows that a separate
boundary would reduce total system risk.

Evidence:

1. Code: `src/app/api/review_workflow.py`,
   `src/app/api/review_workflow_operations.py`.
2. Tests: `tests/unit/test_review_workflow_api_operations.py` plus existing
   review workflow API and application tests.
3. Gates: run focused unit/integration tests, `make maintainability-gate`,
   `make architecture-boundary-gate`, and `make duplicate-implementation-gate`
   before committing the slice.

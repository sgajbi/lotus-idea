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

## 2026-07-04: Conversion Governance API Operation Boundary

The conversion-intent and conversion-outcome API routes now share
`src/app/api/conversion_governance_operations.py` for caller-header parsing,
mutating conversion capability checks, idempotency validation, durable-write
blocking, product-safe persistence problem mapping, and operation-event
mapping.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate service, queue boundary, or
independent scaling. Conversion intent/outcome posture stays in the same API
process because it shares repository, audit, idempotency, and operation-event
ownership with the existing opportunity lifecycle.

Private-banking boundary preserved:

1. Conversion intent remains local and review-gated.
2. Conversion outcome records downstream source posture only.
3. The routes still do not grant execution, suitability, compliance,
   rebalance, report-render, archive, or client-communication authority.

Evidence:

1. Code: `src/app/api/conversion_governance.py`,
   `src/app/api/conversion_governance_operations.py`.
2. Tests: `tests/unit/test_conversion_governance_api_operations.py` plus
   existing conversion domain and review workflow API integration tests.
3. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_api_error_mappings.py tests\unit\test_conversion_governance_api_operations.py tests\unit\test_review_workflow_api_operations.py tests\unit\test_conversion_governance.py tests\integration\test_review_workflow_api.py -q`
   (`49 passed`).
4. Aggregate validation passed: `make lint`, `make typecheck`,
   `make duplicate-implementation-gate`, and `make test-unit` (`2376 passed`).
5. Documentation/context decision: README, repository context, quality
   scorecard, review ledger, refactor decision log, and wiki source were
   updated. No supported-feature promotion or seed/automation change is
   justified by this internal modularity slice. No platform skill update is
   required because the existing backend-delivery and codebase-review skills
   already require design-vs-runtime modularity, same-pattern scans, and
   evidence-backed ledger entries.

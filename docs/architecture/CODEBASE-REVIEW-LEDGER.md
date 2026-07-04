# Codebase Review Ledger

This ledger records implementation-backed cleanup and modularity slices for
lotus-idea. It is not an aspirational backlog; entries must carry evidence or
remain explicitly open.

| Review ID | Scope / Pattern | Status | Finding | Action Taken | Evidence | Follow-up |
| --- | --- | --- | --- | --- | --- | --- |
| `LI-CR-0001` | Review workflow API route orchestration | `Hardened` | `src/app/api/review_workflow.py` duplicated caller parsing, review capability checks, caller entitlement scope validation, idempotency validation, durable-write guarding, persistence problem mapping, and operation-event emission across review-action and feedback routes. This increased design-time complexity inside a single runtime deployable. | Added `src/app/api/review_workflow_operations.py` as an API-internal bounded module for shared mutation preparation, actor-context construction, durable-write blocking, product-safe persistence problem mapping, and operation-event mapping. The route handlers now delegate shared setup while keeping domain workflow logic in `app.application.review_workflow` and runtime composition in `app.api.runtime_dependencies`. | Unit coverage in `tests/unit/test_review_workflow_api_operations.py`; existing review workflow API/application tests remain the behavior proof. Local validation for this entry must include focused review workflow tests, `make maintainability-gate`, `make architecture-boundary-gate`, and `make duplicate-implementation-gate`. | Design modularity improved only. No runtime service split: review workflow remains part of the lotus-idea API process because this slice has no workload, failure-isolation, ownership, or operability evidence for a separate deployable boundary. |

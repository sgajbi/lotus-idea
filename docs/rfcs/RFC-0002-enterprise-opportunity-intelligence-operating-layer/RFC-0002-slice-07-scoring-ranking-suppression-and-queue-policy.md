# RFC-0002 Slice 07: Scoring, Ranking, Suppression, And Queue Policy

Status: Partially implemented - deterministic scoring plus certified scope-aware advisor queue API and readiness diagnostic foundations only

## Outcome

Create deterministic, explainable scoring and ranking for review queues.

## Required Work

1. Implement score inputs for urgency, materiality, confidence, evidence
   quality, freshness, relevance, conflict flags, and downstream fit.
2. Version score policies and expose score reason codes.
3. Implement deduplication, suppression, snooze, expiry, and priority queues.
4. Add rank stability and fairness-of-ordering tests.

## Acceptance Gate

1. Ranking is reproducible and explainable.
2. Suppressed or duplicate ideas do not appear in active queues.
3. Score version appears in evidence and API output.
4. Golden examples prove expected ordering and edge cases.

## Current Implementation Evidence

Implemented on the Slice 07 foundation branch:

1. `src/app/domain/scoring.py` defines framework-free scoring inputs for
   materiality, urgency, confidence, evidence quality, freshness, advisor
   relevance, downstream fit, and conflict flags.
2. `IdeaScoringPolicy` versions deterministic scoring and priority thresholds
   with bounded numeric validation.
3. `score_inputs` returns a `ScoreBreakdown` with score contributions, final
   score, conflict penalty posture, policy version, and typed score reason
   codes.
4. `score_candidate` attaches the policy-versioned `IdeaScore` to an immutable
   candidate without mutating lifecycle authority.
5. `build_review_queue` creates a deterministic review queue projection,
   excludes suppressed, duplicate, expired, closed, rejected, blocked,
   snoozed, unscored, non-reviewable, and access-scope-mismatched candidates,
   and ranks by score, creation time, and candidate identity for stable
   ordering.
6. `tests/unit/test_scoring_queue_policy.py` provides golden examples for
   deterministic scoring, conflict penalty behavior, score attachment, stable
   ranking, priority buckets, suppression, snooze, expiry, unsupported evidence,
   unscored candidates, and deduplication.
7. `src/app/application/review_queue.py` now adds a thin application
   projection over candidate repository snapshots. It reads persisted candidate
   records from the Slice 06 repository contract, delegates ranking and
   exclusions to `build_review_queue`, and applies snooze state without adding a
   parallel queue implementation.
8. `tests/unit/test_review_queue_application.py` proves snapshot-backed queue
   projection, expired-record exclusion, snooze exclusion, access-scope
   filtering, and timezone-aware evaluation validation.
9. `src/app/api/review_queues.py` exposes the certified internal
   `GET /api/v1/review-queues/advisor` API foundation over persisted candidate
   snapshots.
10. The advisor queue API requires `idea.review.queue.read` capability or
    advisor role, requires timezone-aware `evaluatedAtUtc`, accepts optional
    tenant/book/portfolio/client scope query filters, returns ranked queue
    items plus exclusions, and explicitly reports `durableStorageBacked=false`
    and `supportedFeaturePromoted=false`.
11. `tests/integration/test_review_queue_api.py` covers persisted-candidate
    queue projection, scope-filtered queue reads, empty queues, permission
    denial, and product-safe validation for timestamps and blank scope filters.
12. `src/app/domain/access_scope.py`, `src/app/domain/ideas.py`,
    `src/app/domain/signal_evaluation.py`, `src/app/api/idea_signals.py`, and
    `src/app/infrastructure/postgres_repository.py` now carry optional
    tenant/book/portfolio/client access scope onto created and persisted
    candidates so explicit queue scope filters are evaluated against durable
    candidate truth.
13. `src/app/application/review_queue.py` now exposes
    `build_review_queue_readiness_snapshot`, which reuses the same repository
    snapshot and deterministic queue projection path to produce source-safe
    aggregate queue counts, exclusion counts, durable-storage posture, and
    certification blockers without creating a parallel queue implementation.
14. `GET /api/v1/review-queues/advisor/readiness` exposes that posture as a
    certified internal operator diagnostic requiring
    `idea.review.queue.readiness.read` plus the `operator` role. It returns
    `supportabilityStatus=not_certified`, `supportedFeaturePromoted=false`, and
    no candidate identifiers or access-scope identifiers.
15. `tests/unit/test_review_queue_application.py` and
    `tests/integration/test_review_queue_api.py` prove aggregate readiness
    counts, non-storage blockers, product-safe payloads, permission-denied
    behavior, and timezone validation for the queue readiness diagnostic.
16. `src/app/security/caller_context.py` and `src/app/api/caller_headers.py`
    now carry platform caller-context entitlement scope headers for tenant,
    book, portfolio, and client identifiers.
17. `GET /api/v1/review-queues/advisor` now applies caller entitlement scope
    automatically, rejects query filters outside the caller's entitled scope
    with product-safe `403` responses, and still supports narrower explicit
    query filters for internal callers.
18. `lotus-gateway` forwards `X-Caller-Tenant-Ids`, `X-Caller-Book-Ids`,
    `X-Caller-Portfolio-Ids`, and `X-Caller-Client-Ids` on the bounded
    advisor review queue route, so the first Gateway publication path preserves
    queue entitlement scope instead of relying on query-only filters.

## Remaining Gaps

This slice is not complete as a supported product capability. The following
work remains planned:

1. persisted queue state and database-backed ranking projections,
2. source-adapter input orchestration that creates and updates persisted
   candidates before queue projection,
3. broader Gateway contract beyond the first bounded read-only queue/detail
   routes,
4. Workbench review queue UI proof and broader product-surface entitlement
   proof; the first bounded Gateway route now forwards platform caller-context
   scope headers and the internal queue API enforces them, but Workbench panel
   proof remains planned,
5. data-product certification and trust telemetry for queue products,
6. broader supportability metrics, dashboards, alerts, and runtime diagnostics
   for queue health beyond the certified aggregate readiness diagnostic,
7. supported-feature promotion after live proof.

## Validation

Targeted validation:

1. `.venv\Scripts\python.exe -m pytest tests\unit\test_review_queue_application.py tests\unit\test_scoring_queue_policy.py tests\unit\test_high_cash_application.py -q`
   passed with `29 passed`.
2. `.venv\Scripts\python.exe -m ruff check src\app\application\review_queue.py tests\unit\test_review_queue_application.py`
   passed.
3. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini` passed.
4. `make check` passed with lint, format, CI contract, monetary/no-sensitive
   guards, data-mesh contract gate, supported-feature gate,
   endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
   `178` unit tests.
5. `make ci` passed with `13` integration tests, `2` e2e tests, `178` unit
   tests under coverage, coverage gate at `99.38%`, and dependency audit
   reporting no known vulnerabilities.
6. `.venv\Scripts\python.exe -m pytest tests\integration\test_review_queue_api.py -q`
   passed with `4 passed` after adding the advisor review queue API foundation.
7. `.venv\Scripts\python.exe scripts\openapi_quality_gate.py` passed after
   adding the advisor review queue route.
8. `.venv\Scripts\python.exe -m pytest tests/unit/test_review_queue_application.py tests/integration/test_review_queue_api.py tests/unit/test_postgres_repository.py`
   passed with `16 passed` after adding scope-aware queue filtering, blank
   scope validation, and PostgreSQL candidate scope serialization evidence.
9. `.venv\Scripts\python.exe -m pytest tests\unit\test_review_queue_application.py tests\integration\test_review_queue_api.py tests\integration\test_api_operation_events.py tests\unit\test_service_contract.py -q`
   passed after adding the advisor queue readiness diagnostic, before full
   documentation and ledger gates were rerun.
10. `.venv\Scripts\python.exe -m pytest tests\unit\test_security_caller_context.py tests\unit\test_review_queue_application.py tests\integration\test_review_queue_api.py -q`
    passed with `28 passed` after adding caller-context entitlement scope
    parsing, multi-portfolio queue filtering, automatic scope application, and
    product-safe scope denial behavior.
11. `python -m pytest tests\integration\test_ideas_router.py tests\contract\test_ideas_contract.py -q`
    passed with `5 passed` in `lotus-gateway` after adding entitlement-scope
    header forwarding proof for the advisor queue route.

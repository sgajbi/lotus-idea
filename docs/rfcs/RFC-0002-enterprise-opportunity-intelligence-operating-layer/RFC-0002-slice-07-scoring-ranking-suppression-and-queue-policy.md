# RFC-0002 Slice 07: Scoring, Ranking, Suppression, And Queue Policy

Status: Partially implemented - deterministic scoring plus certified advisor queue API foundation only

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
   snoozed, unscored, and non-reviewable candidates, and ranks by score,
   creation time, and candidate identity for stable ordering.
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
   projection, expired-record exclusion, snooze exclusion, and timezone-aware
   evaluation validation.
9. `src/app/api/review_queues.py` exposes the certified internal
   `GET /api/v1/review-queues/advisor` API foundation over persisted candidate
   snapshots.
10. The advisor queue API requires `idea.review.queue.read` capability or
    advisor role, requires timezone-aware `evaluatedAtUtc`, returns ranked queue
    items plus exclusions, and explicitly reports `durableStorageBacked=false`
    and `supportedFeaturePromoted=false`.
11. `tests/integration/test_review_queue_api.py` covers persisted-candidate
    queue projection, empty queues, permission denial, and product-safe
    timezone validation.

## Remaining Gaps

This slice is not complete as a supported product capability. The following
work remains planned:

1. persisted queue state and database-backed ranking projections,
2. source-adapter input orchestration that creates and updates persisted
   candidates before queue projection,
3. Gateway contract,
4. Workbench review queue UI proof and entitlement-backed scope filtering,
5. data-product certification and trust telemetry for queue products,
6. supportability metrics and runtime diagnostics for queue health,
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

# RFC-0002 Slice 07: Scoring, Ranking, Suppression, And Queue Policy

Status: Implemented on `main` - PR `#383` merged at `4f4e0985`; exact-main validation and authored wiki closure are complete; no supported-feature promotion

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

Implemented on the Slice 07 branch:

1. `src/app/domain/scoring.py` defines framework-free scoring inputs for
   materiality, urgency, confidence, evidence quality, freshness, advisor
   relevance, downstream fit, and conflict flags.
2. `IdeaScoringPolicy` versions deterministic candidate scoring with bounded
   numeric validation. It does not own queue ordering or priority thresholds.
3. `score_inputs` returns a `ScoreBreakdown` with score contributions, final
   score, conflict penalty posture, policy version, and typed score reason
   codes.
4. `score_candidate` attaches the policy-versioned `IdeaScore` to an immutable
   candidate without mutating lifecycle authority.
5. `src/app/domain/review_queue/policy.py` owns the separate, versioned
   `ReviewQueuePolicy`: accepted candidate score-policy versions, priority
   thresholds, exclusions, deduplication, and deterministic ordering.
   `build_review_queue` creates a deterministic review queue projection,
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
9. `src/app/api/review_queue/routes.py` exposes the certified internal
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
    `build_review_queue_readiness_snapshot`, which produces source-safe
    aggregate queue counts, exclusion counts, durable-storage posture, and
    certification blockers without creating a parallel queue implementation.
    Durable repositories can satisfy the diagnostic through the
    `ReviewQueueReadinessProjectionRepository` aggregate contract; process-local
    and snooze-aware evaluations retain the deterministic snapshot fallback.
14. `GET /api/v1/review-queues/advisor/readiness` exposes that posture as a
    certified internal operator diagnostic requiring
    `idea.review.queue.readiness.read` plus the `operator` role. It returns
    `supportabilityStatus=not_certified`, `supportedFeaturePromoted=false`, and
    no candidate identifiers or access-scope identifiers.
15. `tests/unit/test_review_queue_application.py`,
    `tests/unit/test_postgres_review_queue.py`, and
    `tests/integration/test_review_queue_api.py` prove aggregate readiness
    counts, PostgreSQL bounded aggregate query shape, non-storage blockers,
    product-safe payloads, permission-denied behavior, and timezone validation
    for the queue readiness diagnostic.
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
19. The durable PostgreSQL advisor queue projection now has narrow expression
    indexes for the exact tenant/book/portfolio/client `access_scope` JSONB
    predicates used by scoped queue reads. The existing repository-side page
    projection stays inside the same deployable service boundary, applies
    eligibility and scope predicates before stable score/created-time ordering,
    count, and `LIMIT`/`OFFSET` bounds, and is guarded by migration contract
    and adapter tests.

### Temporal Snapshot Contract

GitHub issue `#332` closes the queue paging race without adding a queue service:

| Concern | Governed behavior |
| --- | --- |
| Visibility boundary | `evaluatedAtUtc` includes candidates whose `createdAtUtc` is equal to or earlier than the evaluation instant and excludes later candidates. Source `asOfDate` and evidence `generatedAtUtc` remain source-authority facts; queue paging does not reinterpret them. |
| Snapshot identity | Page metadata returns opaque `rqs1_*` identity bound to evaluation time, effective scope, queue policy, accepted candidate score-policy set, snoozes, and the visible candidate-state fingerprint. It contains no database key, offset, portfolio id, or raw evidence. |
| Continuation | `offset > 0` requires the page-1 `snapshotToken`. Missing and malformed tokens return stable `400` ProblemDetails. A valid token against changed visible state returns `409 review_queue_snapshot_conflict`. |
| Concurrent change | PostgreSQL fingerprints before and after the bounded page query. Backdated inserts and lifecycle, suppression, score, or evidence mutations invalidate the snapshot; inserts created after the as-of boundary do not. |
| Adapter parity | In-memory and PostgreSQL paths share token construction and conflict policy. Unit, API integration, and real PostgreSQL tests prove equality, future exclusion, stale conflict, and future-insert stability. |
| Modularity | Snapshot policy is a pure domain module; PostgreSQL queue operations are a cohesive adapter mixin. No runtime split is justified by current workload, isolation, ownership, or operability evidence. |

20. `CandidateScorePolicyVersion` is the closed current registry for score
    provenance across signal families. Missing or unknown policies fail closed
    as `unrankable_score_policy` in both process-local and PostgreSQL paths.
21. Readiness reports the source-safe
    `review_queue_score_policy_coverage_incomplete` blocker when unknown score
    policies exist. PostgreSQL applies the accepted set before count, ordering,
    and page bounds.
22. Queue `policyVersion` now consistently means the active ranking policy;
    candidate `scorePolicyVersion` retains the policy that produced its score.
23. Snapshot identity binds the accepted score-policy set, so policy coverage
    changes invalidate continuation even when candidate rows are unchanged.
24. Queue policy and snapshot logic live in the cohesive internal
    `app.domain.review_queue` package. This is design modularity inside the
    existing deployable; no workload, ownership, isolation, or operability
    evidence justifies a queue microservice.

## Remaining Gaps

Slice 07 implementation is complete as a backend foundation, but it is not a
supported product capability. Workbench realization, broader review audiences,
data-product certification, live operational evidence, and supported-feature
promotion belong to later RFC slices and remain independently gated. Those
downstream gates do not weaken or reopen the scoring/queue policy acceptance
criteria in this slice.

## Validation

Current branch evidence:

1. Focused score registry, queue policy, application, PostgreSQL, API, snapshot
   mutation, and repository-hygiene suites pass with `89 passed`.
2. Ruff passes for every changed Python module and focused test.
3. `make typecheck` passes across `766` source files.
4. Architecture, repository-hygiene, maintainability, review-queue snapshot,
   GitHub issue closure, endpoint certification, OpenAPI, documentation, and
   supported-features gates pass.
5. Exact-main `make check` passes with `3,633` unit tests.
6. PR Merge Gate run `29290924654` passed workflow lint, static/security,
   unit, integration, E2E, combined coverage, PostgreSQL runtime, Docker build,
   and CI-signal evidence for the final branch SHA.
7. Main Releasability run `29291215703` passed the same release lanes for exact
   main SHA `4f4e09854a076392e5cbbd0c413a2e433de04224`.

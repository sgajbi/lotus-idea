# RFC-0002 Slice 07: Scoring, Ranking, Suppression, And Queue Policy

Status: Partially implemented - internal deterministic scoring and queue
projection foundation only

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

## Remaining Gaps

This slice is not complete as a supported product capability. The following
work remains planned:

1. persisted queue state and database-backed ranking projections,
2. application orchestration over repository snapshots and source-adapter
   inputs,
3. API DTOs, OpenAPI examples, endpoint certification, and Gateway contract,
4. Workbench review queue UI proof and entitlement-backed access control,
5. data-product certification and trust telemetry for queue products,
6. supportability metrics and runtime diagnostics for queue health,
7. supported-feature promotion after live proof.

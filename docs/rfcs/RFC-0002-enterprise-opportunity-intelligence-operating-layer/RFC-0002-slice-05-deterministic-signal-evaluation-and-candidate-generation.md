# RFC-0002 Slice 05: Deterministic Signal Evaluation And Candidate Generation

Status: Partially implemented - high-cash domain policy only

## Outcome

Implement the first source-backed opportunity signal family and candidate
generation flow without AI dependency.

## Required Work

1. Select the first signal family from Slice 0.
2. Implement eligibility policy, reason codes, freshness checks, source refs,
   unsupported-evidence handling, and candidate construction.
3. Add golden scenarios for positive, negative, stale-source, missing-source,
   duplicate-source, and entitlement-blocked cases.
4. Keep signal policy versioned and deterministic.

## Acceptance Gate

1. Candidate generation is reproducible from source evidence.
2. Missing or stale source evidence blocks positive claims.
3. Unit and integration tests cover every reason code.
4. Candidate creation does not duplicate source calculations.

## Implementation Evidence

Implemented first-wave scope:

1. First signal family selected from Slice 00: high cash / idle liquidity.
2. `src/app/domain/signal_evaluation.py` defines a pure domain
   `HighCashSignalPolicy`, `HighCashSignalInput`, `SignalEvaluationResult`,
   `SignalEvaluationOutcome`, and `evaluate_high_cash_signal`.
3. The evaluator consumes source-owned `source_reported_cash_weight` plus Core
   source refs for `PortfolioStateSnapshot:v1`, `HoldingsAsOf:v1`,
   `PortfolioCashMovementSummary:v1`, and `PortfolioCashflowProjection:v1`.
   It does not calculate holdings, cash balances, market values, cashflow, or
   portfolio accounting facts.
4. Positive evaluation creates deterministic `OpportunitySignal`,
   `IdeaEvidencePacket`, and `IdeaCandidate` domain objects with stable IDs,
   lineage, source refs, review-required posture, and policy-versioned score.
5. Missing source, stale source, missing source-reported cash weight,
   duplicate candidate, and entitlement-denied cases return blocked or
   suppressed outcomes without candidate creation.
6. Reason-code vocabulary now includes `cash_source_ready` and
   `below_materiality`.

Not implemented yet:

1. source adapters,
2. application orchestration,
3. persistence/replay,
4. API routes,
5. integration tests against live Core,
6. supported-feature promotion,
7. data-product certification.

## Golden Scenarios

`tests/unit/test_high_cash_signal_evaluation.py` covers:

1. positive high-cash candidate creation,
2. below-threshold not-eligible result,
3. stale source blocking,
4. missing source blocking,
5. missing source-reported cash weight blocking,
6. duplicate suppression,
7. entitlement-denied blocking,
8. invalid source-reported weight rejection,
9. invalid policy threshold rejection.

## Validation

Targeted validation:

1. `.venv\Scripts\python.exe -m pytest tests\unit\test_high_cash_signal_evaluation.py tests\unit\test_idea_domain_model.py -q`
   passed with `26 passed`.
2. `.venv\Scripts\python.exe -m ruff check src\app\domain\signal_evaluation.py src\app\domain\ideas.py src\app\domain\__init__.py tests\unit\test_high_cash_signal_evaluation.py`
   passed.
3. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini` passed.

Full repository validation must pass before committing and PR closure.

# RFC-0002 Slice 05: Deterministic Signal Evaluation And Candidate Generation

Status: Partially implemented - high-cash domain policy plus Core source-port foundation

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

Additional implemented source-adapter foundation:

1. `src/app/ports/core_sources.py` defines the `CoreOpportunitySourcePort`,
   `CoreHighCashEvidenceRequest`, and `CoreHighCashEvidence` boundary for
   high-cash evidence sourced from `lotus-core`.
2. `src/app/application/high_cash_signal.py` now includes
   `evaluate_high_cash_signal_from_core`, which fetches Core evidence through
   the port and maps Core entitlement denial or source unavailability into
   blocked domain posture.
3. `src/app/infrastructure/lotus_core_sources.py` adds a conservative HTTP
   adapter over Core's declared `PortfolioStateSnapshot:v1`, `HoldingsAsOf:v1`,
   `PortfolioCashMovementSummary:v1`, and `PortfolioCashflowProjection:v1`
   routes. It preserves source refs, propagates correlation/trace headers, and
   consumes a source-reported cash-weight field only when Core provides it.
4. The adapter deliberately does not derive cash weight from cash totals,
   invested market value, portfolio totals, or any other Core-owned portfolio
   facts. When Core omits a source-reported cash-weight field, evaluation stays
   blocked with missing-source posture.
5. The upstream Core contract gap for explicit source-reported cash weight is
   tracked in `sgajbi/lotus-core#430`.
6. `src/app/application/source_ingestion.py` now adds the first internal
   high-cash source-ingestion orchestration wrapper and bounded run-once batch
   worker foundation over the Core source port and repository port. It
   generates source-ingestion idempotency keys when a caller does not provide
   one, enforces a bounded batch item count, exposes batch decision counts, and
   returns explicit accepted, replayed, conflict, blocked, suppressed, and
   skipped-not-eligible decisions without adding API, Gateway, Workbench, or
   supported-feature claims.

Not implemented yet:

1. live Core integration proof against a running Core service,
2. scheduled daemon/deploy source-ingestion worker and live-service recovery proof,
3. new API routes beyond the existing caller-supplied foundation endpoint,
4. Gateway/Workbench proof,
5. supported-feature promotion,
6. data-product certification.

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

Current source-port validation:

1. `.venv\Scripts\python.exe -m pytest tests\unit\test_high_cash_application.py tests\unit\test_lotus_core_sources.py tests\unit\test_downstream_client.py -q`
   passed with `33 passed`.
2. `.venv\Scripts\python.exe -m ruff check src\app\application\high_cash_signal.py src\app\ports\core_sources.py src\app\infrastructure\lotus_core_sources.py src\app\infrastructure\downstream_client.py tests\unit\test_high_cash_application.py tests\unit\test_lotus_core_sources.py tests\unit\test_downstream_client.py`
   passed.
3. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini` passed.
4. `make check` passed with lint, CI contract, monetary/no-sensitive guards,
   data-mesh contract gate, supported-features gate, endpoint-certification
   gate, typecheck, architecture boundary, OpenAPI, and `160` unit tests.
5. `make ci` passed with integration tests, e2e tests, coverage gate at
   `99.41%`, and dependency audit reporting no known vulnerabilities.

GitHub PR validation and post-merge main releasability remain required before
mainline closure.

Current source-ingestion orchestration validation:

1. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion.py tests\unit\test_high_cash_application.py -q`
   passed with `24 passed`.
2. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion.py -q`
   passed with `11 passed` after adding bounded run-once batch worker coverage
   for duplicate replay, changed-source conflict, batch decision counts,
   timezone validation, and maximum item enforcement.

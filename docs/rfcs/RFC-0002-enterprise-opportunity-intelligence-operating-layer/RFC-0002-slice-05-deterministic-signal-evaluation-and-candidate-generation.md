# RFC-0002 Slice 05: Deterministic Signal Evaluation And Candidate Generation

Status: Partially implemented - high-cash domain policy plus Core source-port, concentration-risk policy plus Risk source-port/adapter foundation, underperformance policy plus Performance source-port/adapter foundation, allocation-drift mandate-review policy plus Manage action-register posture source-port/adapter foundation, run-once worker, and scheduled-worker deploy-contract foundation

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
   consumes Core's `HoldingsAsOf:v1` cash-weight field from
   `totals.source_reported_cash_weight` only when Core reports supported
   cash-weight posture.
4. The adapter deliberately does not derive cash weight from cash totals,
   invested market value, portfolio totals, or any other Core-owned portfolio
   facts. When Core omits a source-reported cash-weight field, evaluation stays
   blocked with missing-source posture.
5. The upstream Core contract gap for explicit source-reported cash weight is
   closed in `sgajbi/lotus-core#430` / Core PR #431. `lotus-idea` issue #22
   tracks the downstream adapter-consumption slice.
6. `src/app/application/source_ingestion.py` now adds the first internal
   high-cash source-ingestion orchestration wrapper and bounded run-once batch
   worker foundation over the Core source port and repository port. It
   generates source-ingestion idempotency keys when a caller does not provide
   one, enforces a bounded batch item count, exposes batch decision counts, and
   returns explicit accepted, replayed, conflict, blocked, suppressed, and
   skipped-not-eligible decisions without adding API, Gateway, Workbench, or
   supported-feature claims.
7. `src/app/application/source_ingestion_worker.py` and
   `scripts/run_source_ingestion_worker.py` now add the versioned
   manifest-backed run-once worker entrypoint. Check-only mode validates
   `docs/examples/source-ingestion/high-cash-worker-manifest.example.json`
   without calling Core or writing repository state, and both check-only and
   run mode emit product-safe summaries without source payloads, portfolio ids,
   raw idempotency keys, or supported-feature promotion.
8. `scripts/source_ingestion_worker_contract_gate.py` and
   `make source-ingestion-worker-check` now lock the check-only summary shape,
   schema version, source authority, item indexes, and sensitive-field
   exclusions so future worker changes cannot downgrade CI to manifest parsing
   only.
9. `src/app/application/source_ingestion_scheduled_worker.py`,
   `scripts/run_scheduled_source_ingestion_worker.py`,
   `scripts/generate_scheduled_source_ingestion_worker_proof.py`,
   `scripts/source_ingestion_scheduled_worker_contract_gate.py`, and the
   `lotus-idea-source-ingestion-worker` Compose profile now add the first
   deploy-contract foundation for scheduled high-cash source ingestion. The
   scheduled worker runs the existing run-once worker on a bounded interval,
   supports a source-safe `--check-only` mode, fails closed when Core runtime
   configuration is missing in run mode, and emits a proof artifact that can
   clear only the scheduled-worker deploy-proof blocker.
10. `make source-ingestion-scheduled-worker-check` now locks the scheduled
    worker schema, entrypoints, Compose service, proof artifact, and
    sensitive-field exclusions so future changes cannot replace deployment
    proof with route-existence or manifest-only claims.

Additional implemented concentration-risk foundation:

1. `src/app/domain/signal_evaluation.py` now defines
   `ConcentrationRiskSignalPolicy`, `ConcentrationRiskSignalInput`, and
   `evaluate_concentration_risk_signal` for source-owned concentration
   attention candidates.
2. The evaluator consumes only Lotus Risk-owned concentration weights,
   issuer-coverage status, freshness, entitlement posture, and source refs. It
   does not recalculate HHI, issuer grouping, position weights, risk
   supportability, or any `lotus-risk` methodology.
3. `src/app/ports/risk_sources.py`,
   `src/app/application/concentration_risk_signal.py`, and
   `src/app/infrastructure/lotus_risk_sources.py` add the source port,
   application wrapper, and fail-closed HTTP adapter over
   `POST /analytics/risk/concentration`.
4. The adapter preserves correlation and trace headers, requires source
   lineage metadata, maps 401/403 to entitlement denial, and fails closed when
   generated-at, as-of-date, request fingerprint, concentration blocks, or
   parseable weights are missing.
5. `tests/unit/test_concentration_risk_signal_evaluation.py`,
   `tests/unit/test_concentration_risk_application.py`, and
   `tests/unit/test_lotus_risk_sources.py` cover positive, below-materiality,
   stale, partial-coverage, missing-source, duplicate, entitlement-denied,
   source-unavailable, malformed-measure, trace-header, and persistence cases.
6. `src/app/application/risk_concentration_live_proof.py`,
   `scripts/generate_risk_concentration_live_proof.py`,
   `scripts/risk_concentration_live_proof_contract_gate.py`, and
   `make risk-concentration-live-proof-contract-gate` define a source-safe live
   Risk concentration proof artifact. A valid artifact proves a live
   `lotus-risk:ConcentrationRiskReport:v1` source call, current source
   evidence, and deterministic concentration candidate generation, then clears
   only the namespaced opportunity-archetype live Risk source blocker when
   consumed by aggregate readiness.

Additional implemented underperformance foundation:

1. `src/app/domain/signal_evaluation.py` now defines
   `UnderperformanceSignalPolicy`, `UnderperformanceSignalInput`, and
   `evaluate_underperformance_signal` for source-owned active-return
   underperformance candidates.
2. The evaluator consumes only `lotus-performance` source-reported active
   return, benchmark-context availability, freshness, entitlement posture, and
   source refs. It does not calculate portfolio return, benchmark return,
   active return, attribution, benchmark assignment, or performance
   supportability locally.
3. `src/app/ports/performance_sources.py`,
   `src/app/application/underperformance_signal.py`, and
   `src/app/infrastructure/lotus_performance_sources.py` add the source port,
   application wrapper, and fail-closed HTTP adapter over
   `POST /integration/returns/series`.
4. The adapter requests a stateful `ReturnsSeriesBundle` with benchmark series
   included, preserves correlation and trace headers, consumes only the final
   source-reported cumulative active-return point, requires source lineage
   metadata, maps 401/403 to entitlement denial, and fails closed when async
   execution is still pending or required response metadata is missing.
5. `tests/unit/test_underperformance_signal_evaluation.py`,
   `tests/unit/test_underperformance_application.py`, and
   `tests/unit/test_lotus_performance_sources.py` cover positive,
   below-materiality, missing benchmark context, stale source, missing source,
   duplicate, entitlement-denied, source-unavailable, pending async response,
   malformed active-return, and trace-header cases.
6. `src/app/application/performance_underperformance_live_proof.py`,
   `scripts/generate_performance_underperformance_live_proof.py`,
   `scripts/performance_underperformance_live_proof_contract_gate.py`, and
   `make performance-underperformance-live-proof-contract-gate` define a
   source-safe live Performance underperformance proof artifact. A valid
   artifact proves a live `lotus-performance:ReturnsSeriesBundle:v1` source
   call, current source evidence, benchmark context availability, and
   deterministic underperformance candidate generation, then clears only the
   namespaced opportunity-archetype live Performance source blocker when
   consumed by aggregate readiness.

Additional implemented allocation-drift / mandate-review foundation:

1. `src/app/domain/signal_evaluation.py` now defines
   `MandateHealthSignalPolicy`, `MandateHealthSignalInput`, and
   `evaluate_mandate_health_signal` for portfolio-manager review candidates
   that require source-owned Manage action-register posture.
2. The evaluator consumes only Manage-owned workflow decision count, lineage
   edge count, supportability state, freshness, entitlement posture,
   portfolio-scope confirmation, and source refs. It does not calculate drift,
   mandate compliance, model-portfolio deviations, rebalance actions, orders,
   execution, or settlement.
3. `src/app/ports/manage_sources.py`,
   `src/app/application/mandate_health_signal.py`, and
   `src/app/infrastructure/lotus_manage_sources.py` add the source port,
   application wrapper, and fail-closed HTTP adapter over
   `GET /api/v1/rebalance/supportability/summary`.
4. The current Manage route is store-wide supportability evidence. The adapter
   records this as source posture and source-response lineage, but the domain
   policy blocks candidate creation unless future evidence confirms
   portfolio-scoped action-register posture for the requested portfolio.
5. `tests/unit/test_mandate_health_signal_evaluation.py`,
   `tests/unit/test_mandate_health_application.py`, and
   `tests/unit/test_lotus_manage_sources.py` cover positive future
   portfolio-scoped evidence, current store-wide-source blocking,
   non-ready/stale/missing Manage evidence, duplicate suppression,
   entitlement denial, source unavailability, malformed counts, trace headers,
   and request validation.

Not implemented yet:

1. live Risk concentration source proof captured from an actual canonical
   runtime and merged as release evidence,
2. live Performance returns-series source proof captured from an actual
   canonical runtime and merged as release evidence,
3. benchmark-assignment source-ref proof from the governed source authority,
4. portfolio-scoped Manage action-register proof beyond the current
   store-wide supportability route foundation,
5. mandate performance-health source refs from the governed Performance source
   authority,
6. mandate risk-health source refs from the governed Risk source authority,
7. Core portfolio-state source refs for allocation-drift / mandate-review
   candidates,
8. source-worker certification beyond bounded live Core source-ingestion proof,
9. certified long-running scheduled daemon runtime and live-service recovery proof,
10. new API routes beyond the existing caller-supplied foundation endpoint,
11. Gateway/Workbench proof,
12. supported-feature promotion,
13. data-product certification.

Upstream Risk consumer approval for
`lotus-risk:ConcentrationRiskReport:v1` is source-approved. That clears only the
approval blocker. The new Risk live-proof artifact contract can clear the live
Risk source blocker only when valid source-safe evidence is supplied; data-product
certification, Gateway/Workbench proof, client-publication, and supported-feature
promotion remain blocked.

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
3. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion_worker.py tests\unit\test_source_ingestion.py tests\unit\test_ci_enforcement_contract.py -q`
   passed with `30 passed` after adding the manifest-backed worker CLI and CI
   gate coverage.
4. `make source-ingestion-worker-check` passed, proving the example manifest
   and source-safe check-only output contract validate without Core or
   repository writes.
5. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion_scheduled_worker.py tests\unit\test_source_ingestion_scheduled_worker_contract_gate.py -q`
   passed after adding scheduled worker check-only, proof artifact, missing
   Core runtime guard, and sensitive-output contract coverage.
6. `.venv\Scripts\python.exe scripts\source_ingestion_scheduled_worker_contract_gate.py`
   passed, proving the scheduled worker deploy-contract artifact remains
   source-safe and wired to the Compose worker profile.

Current Core cash-weight adapter validation:

1. `.venv\Scripts\python.exe -m pytest tests\unit\test_lotus_core_sources.py -q`
   covers Core's nested `totals.source_reported_cash_weight` response shape,
   blocked supportability states, malformed cash-weight values, source refs,
   and trace/correlation propagation.
2. This closes the adapter-shape gap only. It does not certify live Core
   source ingestion, certified scheduled daemon runtime, data-product certification,
   Gateway/Workbench support, or supported-feature promotion.

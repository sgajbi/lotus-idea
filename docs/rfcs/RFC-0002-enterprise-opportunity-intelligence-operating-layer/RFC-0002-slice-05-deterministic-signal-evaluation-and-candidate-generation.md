# RFC-0002 Slice 05: Deterministic Signal Evaluation And Candidate Generation

Status: Partially implemented - high-cash domain policy plus Core source-port, bounded Core-backed `evaluate-from-source` API foundation, concentration-risk policy plus Risk source-port/adapter/live-proof and caller-supplied plus bounded Risk-backed `evaluate-from-source` API foundations, high-volatility policy plus narrowed Risk volatility source-port/adapter/live-proof and caller-supplied plus bounded Risk-backed `evaluate-from-source` API foundations, drawdown-review policy plus narrowed Risk drawdown source-port/adapter/live-proof and caller-supplied plus bounded Risk-backed `evaluate-from-source` API foundations, underperformance policy plus Performance source-port/adapter/live-proof foundation, allocation-drift mandate-review policy plus Manage action-register posture source-port/adapter/live-proof and caller-supplied API foundation, bond-maturity / reinvestment deterministic policy plus Core `PortfolioMaturitySummary:v1` source-adapter consumption and caller-supplied plus bounded Core-backed `evaluate-from-source` API foundations, missing suitability context policy plus Advise policy-evaluation workflow source-port/adapter/live-proof and caller-supplied API foundation, missing risk-profile evidence-gap policy plus caller-supplied API foundation, mandate/restriction review policy plus caller-supplied API foundation, low-income / liquidity-shortfall policy plus Core cashflow source-port/adapter/live-proof and caller-supplied plus bounded Core-backed `evaluate-from-source` API foundations, missing-benchmark review policy plus Core benchmark-assignment source-port/live-proof and caller-supplied plus bounded Core-backed `evaluate-from-source` API foundations, route-level caller-supplied source-ref contract validation before candidate creation, run-once worker, and scheduled-worker deploy-contract foundation

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
7. Caller-supplied signal API routes validate present source refs against the
   route's governed source-system and source-product contract before domain
   evaluation, candidate creation, or high-cash persistence. Contract mismatch
   requests return product-safe `400 invalid_request` responses and emit
   invalid-request telemetry under the expected route source authority, not the
   caller-supplied mismatched authority.

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
11. `POST /api/v1/idea-signals/high-cash/evaluate-from-source` now exposes the
    existing Core high-cash source-port through a bounded advisor API. It
    enforces `idea.signal.evaluate`, advisor role, and portfolio entitlement
    before constructing source runtime dependencies; returns product-safe 503
    posture when Core query runtime configuration is absent; closes the Core
    runtime client after each request; and redacts source routes, content
    hashes, portfolio identifiers, and raw source payloads from responses.
12. The source-fetching API remains an internal design-module foundation inside
    the existing `lotus-idea` service. It does not add a separately scalable
    process, certify live source support, persist candidates, promote a data
    product, prove Gateway/Workbench behavior, or promote a supported feature.
13. `POST /api/v1/idea-signals/low-income/evaluate-from-source` now exposes the
    existing Core low-income cashflow source-port through the same bounded
    advisor API pattern. It enforces `idea.signal.evaluate`, advisor role, and
    portfolio entitlement before constructing source runtime dependencies;
    returns product-safe 503 posture when Core query runtime configuration is
    absent; closes the Core runtime client after each request; and redacts
    source routes, content hashes, portfolio identifiers, and raw source
    payloads from responses.
14. The shared Core source-runtime builder keeps source-backed evaluation as an
    internal design-module boundary inside the existing `lotus-idea` process.
    There is still no workload, failure-isolation, ownership, or operability
    evidence justifying a separate runtime service boundary.

Additional implemented bond-maturity / reinvestment foundation:

1. `src/app/domain/bond_maturity_signal.py` defines
   `BondMaturitySignalPolicy`, `BondMaturitySignalInput`, and
   `evaluate_bond_maturity_signal` for source-owned maturity-window review
   candidates.
2. The evaluator consumes only source-reported next maturity date, maturing
   holding count, source freshness, entitlement posture, and Core source refs.
   It does not recommend a replacement product, calculate reinvestment advice,
   infer suitability, construct orders, or perform portfolio-management
   actions.
3. `src/app/application/bond_maturity_signal.py`,
   `src/app/infrastructure/lotus_core_sources.py`, and
   `src/app/ports/core_sources.py` add the application command, Core source
   port, and fail-closed Core maturity-summary adapter. The live adapter
   consumes Core-owned `PortfolioMaturitySummary:v1` from
   `/portfolios/{portfolio_id}/maturity-summary`, requires upstream
   `HoldingsAsOf:v1` lineage, accepts explicit maturity summary fields only,
   and no longer derives maturity dates or maturing-position counts from raw
   positions.
4. `src/app/application/bond_maturity_live_proof.py`,
   `scripts/generate_bond_maturity_live_proof.py`, and
   `make bond-maturity-live-proof-contract-gate` define a source-safe live
   proof artifact that can clear only the live Core maturity source blocker.
   It does not certify data mesh, Workbench behavior, client publication,
   product recommendations, reinvestment advice, or supported-feature status.
5. `src/app/api/bond_maturity_signals.py` exposes
   `POST /api/v1/idea-signals/bond-maturity/evaluate` as a bounded
   caller-supplied API foundation over Core maturity-summary evidence. It
   requires advisor role and `idea.signal.evaluate` capability, emits bounded operation
   events, redacts source route/hash fields from candidate responses, and does
   not fetch Core sources, recommend replacement products, calculate
   reinvestment advice, own maturity schedules, approve planning suitability,
   create orders, publish client communication, certify data products, prove
   Workbench behavior, or promote support.
6. `POST /api/v1/idea-signals/bond-maturity/evaluate-from-source` exposes a
   bounded Core-backed API foundation that fetches Core maturity evidence
   through the configured source adapter only after advisor role,
   `idea.signal.evaluate`, and portfolio entitlement checks pass. It closes
   route-owned runtime clients after each request, returns product-safe
   dependency posture when Core runtime is missing, does not persist
   candidates, and does not certify live source support, maturity schedule
   authority, replacement product recommendation, reinvestment advice,
   planning suitability, orders/execution, Gateway/Workbench support,
   data-product certification, client publication, or supported-feature
   promotion.
7. `tests/unit/test_bond_maturity_signal_evaluation.py` and
   `tests/unit/test_bond_maturity_application.py` cover positive,
   outside-window, zero-count, missing-source, missing-maturity-date, stale,
   duplicate, entitlement-denied, source-unavailable, and invalid-policy cases.
8. `tests/integration/test_bond_maturity_signal_api.py` and
   `tests/integration/test_api_operation_events.py` cover route success,
   outside-window not-eligible posture, stale-source blocking, permission
   denial, source-redacted response projection, no-authority promotion, and
   bounded operation-event proof.
9. The opportunity archetype contract now removes only the
   `maturity_signal_policy_missing` blocker. Live maturity source certification
   remains blocked until a valid canonical Core maturity-summary live proof is
   captured and merged; data-mesh, Workbench, client-publication, and
   supported-feature blockers remain.

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
6. `src/app/api/concentration_risk_signals.py` exposes
   `POST /api/v1/idea-signals/concentration-risk/evaluate` over
   caller-supplied Lotus Risk `ConcentrationRiskReport:v1` evidence. The route
   uses shared signal API support for permission, source-authority, operation
   event, and RFC-7807 problem-detail behavior, creates only advisor-review
   concentration candidates or blocked/not-eligible/suppressed posture, and
   does not calculate concentration, approve risk methodology, recommend
   trades, create rebalance actions, certify data mesh, prove Workbench
   behavior, authorize client publication, or promote support.
7. `src/app/application/risk_concentration_live_proof.py`,
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
6. `src/app/api/underperformance_signals.py` exposes
   `POST /api/v1/idea-signals/underperformance/evaluate` as a bounded
   caller-supplied API foundation over Lotus Performance active-return and
   benchmark-context evidence. It requires advisor role and
   `idea.signal.evaluate` capability, emits bounded operation events, redacts source route/hash fields from
   candidate responses, and does not fetch Performance sources, calculate
   returns, assign benchmarks, certify benchmark methodology, recommend trades,
   create rebalance actions, publish client communication, certify data
   products, prove Workbench behavior, or promote support.
7. `src/app/application/performance_underperformance_live_proof.py`,
   `scripts/generate_performance_underperformance_live_proof.py`,
   `scripts/performance_underperformance_live_proof_contract_gate.py`, and
   `make performance-underperformance-live-proof-contract-gate` define a
   source-safe live Performance underperformance proof artifact. A valid
   artifact proves a live `lotus-performance:ReturnsSeriesBundle:v1` source
   call, current source evidence, benchmark context availability, and
   deterministic underperformance candidate generation, then clears only the
   namespaced opportunity-archetype live Performance source blocker when
   consumed by aggregate readiness.
8. `src/app/application/core_benchmark_assignment_live_proof.py`,
   `scripts/generate_core_benchmark_assignment_live_proof.py`,
   `scripts/core_benchmark_assignment_live_proof_contract_gate.py`, and
   `make core-benchmark-assignment-live-proof-contract-gate` define a
   source-safe live Core benchmark assignment proof artifact. A valid artifact
   proves a live `lotus-core:BenchmarkAssignment:v1` source call, current source
   evidence, effective assignment posture, benchmark identity resolution, and
   assignment version presence, then clears only the namespaced
   opportunity-archetype benchmark-assignment source-ref blocker when consumed
   by aggregate readiness. It does not assign benchmarks, calculate benchmark
   returns, certify benchmark methodology, or promote underperformance support.

Additional implemented source-freshness hardening:

1. Risk, Performance, and Manage source adapters now align with the Core source
   adapter's fail-closed freshness posture. Explicit source freshness values
   such as current, same-day, stale, expired, unavailable, or missing are
   mapped into `EvidenceFreshness`; adjacent readiness, supportability,
   coverage, health-state, and data-quality fields no longer imply current
   freshness.
2. Unit coverage in `tests/unit/test_lotus_risk_sources.py`,
   `tests/unit/test_lotus_risk_volatility_sources.py`,
   `tests/unit/test_lotus_risk_drawdown_sources.py`,
   `tests/unit/test_lotus_performance_sources.py`, and
   `tests/unit/test_lotus_manage_sources.py` locks the issue-ledger learning:
   missing freshness remains unavailable/unproven even when the source reports
   ready supportability or ready data-quality posture.
3. `make source-observability-contract-gate` now also blocks future
   `lotus_*_sources.py` adapters from returning `EvidenceFreshness.CURRENT`
   from readiness, supportability, coverage, health-state, or data-quality
   predicates.
4. This closes only the source-authority hardening gap. It does not certify
   live source ingestion, data mesh, Workbench, client publication, downstream
   action, or supported-feature promotion.

Additional implemented missing-benchmark foundation:

1. `src/app/domain/missing_benchmark_signal.py` defines
   `MissingBenchmarkSignalPolicy`, `MissingBenchmarkSignalInput`, and
   `evaluate_missing_benchmark_signal` for advisor-review evidence-gap
   candidates when Core-owned benchmark assignment evidence is missing,
   inactive, ineffective for the as-of date, or missing a version.
2. The evaluator consumes only `lotus-core:BenchmarkAssignment:v1` source refs,
   freshness, entitlement posture, benchmark identity resolution, effective
   assignment posture, active status, and assignment version presence. It does
   not assign benchmarks, calculate benchmark returns, certify methodology, or
   infer suitability.
3. `src/app/application/missing_benchmark_signal.py` adds direct command and
   Core source-port wrappers over the existing
   `CoreBenchmarkAssignmentSourcePort`, mapping source unavailable and
   entitlement-denied states to blocked outcomes without candidate creation.
4. `src/app/api/missing_benchmark_signals.py` exposes
    `POST /api/v1/idea-signals/missing-benchmark/evaluate` as a bounded
    caller-supplied API foundation over Core benchmark-assignment posture. It
    requires advisor role and `idea.signal.evaluate` capability, emits bounded operation
    events, redacts source route/hash fields from candidate responses, and does
    not assign benchmarks, calculate performance, certify methodology, publish
    client communication, or promote support.
5. `POST /api/v1/idea-signals/missing-benchmark/evaluate-from-source` exposes
   the existing Core benchmark-assignment source-port through the bounded
   advisor API pattern. It enforces advisor role, `idea.signal.evaluate`, and
   portfolio entitlement before constructing source runtime dependencies;
   returns product-safe 503 posture when Core runtime configuration is absent;
   closes the Core runtime client after each request; and redacts source
   routes, content hashes, portfolio identifiers, and raw source payloads from
   responses.
6. `tests/unit/test_missing_benchmark_signal_evaluation.py` and
   `tests/unit/test_missing_benchmark_application.py` cover positive
   evidence-gap creation, ready-assignment suppression, inactive or missing
   assignment posture, stale/missing source, entitlement denial, duplicate
   suppression, source-unavailable handling, and source request mapping.
7. `tests/integration/test_missing_benchmark_signal_api.py` and
   `tests/integration/test_api_operation_events.py` cover route success,
   ready-assignment not-eligible posture, stale-source blocking, source-backed
   Core evaluation, portfolio entitlement denial before runtime construction,
   missing Core runtime configuration, Core source unavailability,
   cleanup-failure suppression, permission denial, and operation-event proof.
8. `src/app/application/missing_benchmark_live_proof.py`,
   `scripts/generate_missing_benchmark_live_proof.py`, and
   `make missing-benchmark-live-proof-contract-gate` define a source-safe live
   Core proof artifact that can clear only the missing-benchmark live Core
   source blocker when it proves a current Core source attempt produced an
   advisor-review missing-benchmark candidate.
9. `src/app/application/missing_benchmark_performance_readiness_proof.py`,
   `scripts/generate_missing_benchmark_performance_readiness_proof.py`, and
   `make missing-benchmark-performance-readiness-proof-contract-gate` define a
   source-safe Lotus Performance benchmark-readiness proof artifact that can
   clear only the missing-benchmark Performance source-ref blocker when
   `ReturnsSeriesBundle:v1` evidence proves benchmark readiness was evaluated.
10. The opportunity archetype contract records `missing-benchmark-review` as a
   non-promoted bounded foundation. Remaining blockers include Performance
   benchmark-readiness source ref when no valid proof is supplied, data-mesh
   certification, Workbench proof, client publication, and supported-feature
   promotion.

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
5. `src/app/api/allocation_drift_signals.py` exposes
   `POST /api/v1/idea-signals/allocation-drift/evaluate` as a bounded
   caller-supplied API foundation over source-owned Manage action-register and
   mandate-health source-ref posture. It requires advisor role and
   `idea.signal.evaluate` capability, emits bounded operation events, redacts source route/hash
   fields from candidate responses, returns portfolio-manager review
   candidates or blocked/not-eligible/suppressed posture, and does not fetch
   Manage sources, calculate allocation drift, approve mandate compliance,
   create rebalance actions, create orders, publish client communication,
   certify data products, prove Workbench behavior, or promote support.
6. `tests/unit/test_mandate_health_signal_evaluation.py`,
   `tests/unit/test_mandate_health_application.py`, and
   `tests/unit/test_lotus_manage_sources.py` cover positive future
   portfolio-scoped evidence, current store-wide-source blocking,
   non-ready/stale/missing Manage evidence, duplicate suppression,
   entitlement denial, source unavailability, malformed counts, trace headers,
   and request validation.
7. `tests/integration/test_allocation_drift_signal_api.py` and
   `tests/integration/test_api_operation_events.py` cover route success,
   below-threshold posture, store-wide Manage supportability blocking,
   non-ready and stale source blockers, permission denial, source-redacted
   response projection, no-authority promotion, and bounded operation-event
   proof.
   `contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`
   and `make opportunity-archetype-contract-gate` now pin this API module,
   route, and integration test as allocation-drift evidence so the archetype
   proof contract cannot drift back to policy-only evidence.
8. `src/app/application/manage_mandate_live_proof.py`,
   `scripts/generate_manage_mandate_live_proof.py`, and
   `make manage-mandate-live-proof-contract-gate` define the source-safe
   live-proof artifact contract for portfolio-scoped
   `lotus-manage:PortfolioActionRegister:v1` posture. A valid artifact clears
   only `opportunity_archetype_portfolio_scoped_manage_source_proof_missing`,
   `opportunity_archetype_mandate_performance_health_source_ref_missing`, and
   `opportunity_archetype_mandate_risk_health_source_ref_missing` in aggregate
   readiness. It does not certify Core portfolio state, data mesh, Workbench
   behavior, client publication, supported-feature promotion, rebalance
   authority, action authority, order creation, execution, or settlement.

Additional implemented high-volatility foundation:

1. `src/app/domain/signal_evaluation.py` now defines
   `HighVolatilitySignalPolicy`, `HighVolatilitySignalInput`, and
   `evaluate_high_volatility_signal` for source-owned volatility attention
   candidates.
2. The evaluator consumes only Lotus Risk-owned volatility, supportability
   state, freshness, entitlement posture, and source refs. It does not
   calculate volatility, drawdown, tracking error, VaR, risk profile,
   suitability, or mandate risk locally.
3. `src/app/ports/risk_sources.py`,
   `src/app/application/high_volatility_signal.py`, and
   `src/app/infrastructure/lotus_risk_sources.py` add the source port,
   application wrapper, and fail-closed HTTP adapter over
   `POST /analytics/risk/calculate` for `RiskMetricsReport:v1` volatility
   evidence.
4. The adapter preserves correlation and trace headers, requests source-owned
   stateful `VOLATILITY` metrics, requires source lineage metadata, maps
   401/403 to entitlement denial, and fails closed when generated-at,
   as-of-date, request fingerprint, period results, metric blocks, or parseable
   volatility are missing or malformed.
5. `tests/unit/test_high_volatility_signal_evaluation.py`,
   `tests/unit/test_high_volatility_application.py`, and
   `tests/unit/test_lotus_risk_volatility_sources.py` cover positive,
   below-materiality, stale, non-ready, missing-source, duplicate,
   entitlement-denied, source-unavailable, malformed-measure, trace-header, and
   request-validation cases.
6. `src/app/application/high_volatility_live_proof.py`,
   `scripts/generate_high_volatility_live_proof.py`,
   `scripts/high_volatility_live_proof_contract_gate.py`, and
   `make high-volatility-live-proof-contract-gate` define a source-safe live
   Risk high-volatility proof artifact. A valid artifact proves a live
   `lotus-risk:RiskMetricsReport:v1` source call, current source evidence,
   ready Risk supportability, and deterministic high-volatility candidate
   generation, then clears only the namespaced opportunity-archetype live Risk
   volatility blocker when consumed by aggregate readiness.
7. This high-volatility foundation does not include drawdown-specific source
   proof, data-mesh certification, Workbench proof, or supported-feature
   promotion.
8. `src/app/api/high_volatility_signals.py` exposes
   `POST /api/v1/idea-signals/high-volatility/evaluate` as a bounded
   caller-supplied API foundation over Lotus Risk `RiskMetricsReport:v1`
   volatility evidence. It requires advisor role and `idea.signal.evaluate` capability,
   emits bounded operation events, redacts source route/hash fields from
   candidate responses, and does not fetch Risk sources, calculate volatility,
   approve Risk methodology, recommend trades, create rebalance actions,
   publish client communication, certify data products, prove Workbench
   behavior, or promote support.
9. The opportunity archetype contract gate now requires the high-volatility
   API module, route, and integration test as implementation evidence for the
   high-volatility / drawdown review archetype, so proof-readiness evidence
   cannot regress to policy-only high-volatility proof.

Additional implemented drawdown-review foundation:

1. `src/app/domain/signal_evaluation.py` now defines
   `DrawdownReviewSignalPolicy`, `DrawdownReviewSignalInput`, and
   `evaluate_drawdown_review_signal` for source-owned drawdown attention
   candidates under the high-volatility / drawdown review archetype.
2. The evaluator consumes only Lotus Risk-owned maximum drawdown,
   supportability state, freshness, entitlement posture, and source refs. It
   does not calculate drawdown, volatility, tracking error, VaR, risk profile,
   suitability, or mandate risk locally.
3. `src/app/ports/risk_sources.py`,
   `src/app/application/drawdown_review_signal.py`, and
   `src/app/infrastructure/lotus_risk_sources.py` add the source port,
   application wrapper, and fail-closed HTTP adapter over
   `POST /analytics/risk/drawdown` for `DrawdownAnalyticsReport:v1` drawdown
   evidence.
4. The adapter preserves correlation and trace headers, requests source-owned
   stateful drawdown analytics, requires source lineage metadata, maps 401/403
   to entitlement denial, and fails closed when generated-at, as-of-date,
   request fingerprint, period results, summary blocks, or parseable maximum
   drawdown are missing or malformed.
5. `tests/unit/test_drawdown_review_signal_evaluation.py`,
   `tests/unit/test_drawdown_review_application.py`, and
   `tests/unit/test_lotus_risk_drawdown_sources.py` cover positive,
   below-materiality, stale, non-ready, missing-source, duplicate,
   entitlement-denied, source-unavailable, malformed-measure, trace-header, and
   request-validation cases.
6. `src/app/api/drawdown_review_signals.py` exposes
   `POST /api/v1/idea-signals/drawdown-review/evaluate` as a bounded
   caller-supplied API foundation over Lotus Risk
   `DrawdownAnalyticsReport:v1` maximum-drawdown evidence. It requires
   advisor role and `idea.signal.evaluate` capability, emits bounded operation events,
   redacts source route/hash fields from candidate responses, and does not
   fetch Risk sources, calculate drawdown, approve risk methodology,
   recommend trades, create rebalance actions, publish client communication,
   certify data products, prove Workbench behavior, or promote support.
7. The opportunity archetype contract gate now requires the drawdown-review
   API module, route, and integration test as implementation evidence for the
   high-volatility / drawdown review archetype, so proof-readiness evidence
   cannot regress to policy-only drawdown proof.
8. `make opportunity-archetype-contract-gate` now enforces API evidence parity
   for every implemented caller-supplied signal API recorded in the archetype
   contract. Concentration, underperformance, allocation drift, bond maturity,
   high volatility, drawdown, missing suitability, missing risk profile,
   mandate/restriction, low-income, and missing-benchmark foundations must keep
   their API module, route, and integration-test evidence refs aligned with the
   governed archetype contract.
9. `src/app/application/risk_drawdown_live_proof.py`,
   `scripts/generate_risk_drawdown_live_proof.py`,
   `scripts/risk_drawdown_live_proof_contract_gate.py`, and
   `make risk-drawdown-live-proof-contract-gate` define a source-safe live Risk
   drawdown proof artifact. A valid artifact proves a live
   `lotus-risk:DrawdownAnalyticsReport:v1` source call, current source
   evidence, ready Risk supportability, and deterministic drawdown-review
   candidate generation, then clears only the namespaced opportunity-archetype
   drawdown source blocker when consumed by aggregate readiness.
10. This foundation does not include data-mesh certification, Workbench proof,
   client-publication approval, or supported-feature promotion.

Additional implemented missing suitability context foundation:

1. `src/app/domain/signal_evaluation.py` now defines
   `MissingSuitabilityContextSignalPolicy`,
   `MissingSuitabilityContextSignalInput`, and
   `evaluate_missing_suitability_context_signal` for governance-gap review
   candidates under the missing suitability context archetype.
2. The evaluator consumes only Lotus Advise-owned policy evaluation workflow
   posture: evaluation status, open/blocked approval, disclosure, consent, and
   sign-off requirements, client-publication boundary, freshness, entitlement
   posture, and source refs. It does not calculate suitability, approve policy,
   approve proposals, complete sign-off, release client-ready publication, or
   create external client communication.
3. `src/app/ports/advise_sources.py`,
   `src/app/application/missing_suitability_signal.py`, and
   `src/app/infrastructure/lotus_advise_sources.py` add the source port,
   application wrapper, and fail-closed HTTP adapter over
   `GET /advisory/policy-evaluations/{evaluation_id}/workflow` for
   `AdvisoryPolicyEvaluationRecord:v1` workflow posture.
4. The adapter preserves correlation and trace headers, requires source
   lineage metadata for generated-at and content hash, maps 401/403 to
   entitlement denial, and fails closed when requirement lists, sign-off
   blockers, source timestamps, freshness, or hashes are malformed or missing.
5. `tests/unit/test_missing_suitability_signal_evaluation.py`,
   `tests/unit/test_missing_suitability_application.py`, and
   `tests/unit/test_lotus_advise_sources.py` cover positive, clear-context,
   stale, missing-source, missing-status/count, duplicate, entitlement-denied,
   source-unavailable, malformed-source, trace-header, and request-validation
   cases.
6. `src/app/application/missing_suitability_live_proof.py`,
   `scripts/generate_missing_suitability_live_proof.py`, and
   `make missing-suitability-live-proof-contract-gate` define a source-safe
   live Advise proof artifact. A valid artifact can clear only
   `opportunity_archetype_advise_policy_live_source_proof_missing`; it does not
   approve suitability, policy, proposal, sign-off, client publication, or
   external communication.
7. `src/app/api/missing_suitability_signals.py` exposes the bounded
   `POST /api/v1/idea-signals/missing-suitability/evaluate` API over
   caller-supplied Advise policy-evaluation evidence. The endpoint returns
   source-safe candidate or blocked posture only and redacts raw route and
   content-hash details from candidate source refs.
8. `tests/integration/test_missing_suitability_signal_api.py` covers
   candidate creation, blocked client-publication posture, permission denial,
   and source-redaction behavior for the certified API contract.
9. This foundation does not include data-mesh certification, Workbench proof,
   client-publication approval, or supported-feature promotion.

Additional implemented missing risk profile foundation:

1. `src/app/domain/missing_risk_profile_signal.py` now defines
   `MissingRiskProfileSignalPolicy`, `MissingRiskProfileSignalInput`, and
   `evaluate_missing_risk_profile_signal` for advisor-review evidence-gap
   candidates under the missing or stale risk-profile archetype.
2. The evaluator consumes only Lotus Advise-owned risk-profile posture supplied
   as source-backed evidence: missing, stale, expired, review-due, current,
   source freshness, entitlement posture, and source refs. It does not approve
   risk profiling, determine client suitability, approve policy, approve
   proposals, release client-ready publication, or create external client
   communication.
3. `src/app/application/missing_risk_profile_signal.py` adds the application
   command wrapper and a bounded Advise policy-evaluation adapter path over the
   existing `AdvisePolicyEvaluationEvidence` source port. The adapter creates a
   candidate only when `advise_diagnostic` carries explicit risk-profile
   diagnostic codes such as `risk_profile_missing`,
   `risk_profile_stale`, `risk_profile_expired`, or
   `risk_profile_review_due`.
4. Generic open suitability or policy requirements remain owned by the existing
   missing suitability context path; they do not create missing-risk-profile
   candidates unless Advise emits explicit risk-profile diagnostic posture.
5. `tests/unit/test_missing_risk_profile_signal_evaluation.py` and
   `tests/unit/test_missing_risk_profile_application.py` cover positive,
   current/not-eligible, stale, expired, review-due, missing-source,
   missing-posture, duplicate, entitlement-denied, source-unavailable, generic
   suitability diagnostic suppression, and request-routing cases.
6. `src/app/application/missing_risk_profile_source_product_proof.py`,
   `scripts/generate_missing_risk_profile_source_product_proof.py`, and
   `make missing-risk-profile-source-product-proof-contract-gate` define a
   source-safe typed Advise risk-profile source-product proof artifact. A
   valid artifact can clear only
   `opportunity_archetype_typed_advise_risk_profile_source_product_missing`
   in aggregate readiness.
7. `src/app/application/missing_risk_profile_live_proof.py`,
   `scripts/generate_missing_risk_profile_live_proof.py`, and
   `make missing-risk-profile-live-proof-contract-gate` define a source-safe
   Advise risk-profile diagnostic proof artifact. A valid artifact can clear
   only `opportunity_archetype_advise_risk_profile_live_source_proof_missing`
   in aggregate readiness.
8. `src/app/api/idea_signals.py` exposes the bounded
   `POST /api/v1/idea-signals/missing-risk-profile/evaluate` API over
   caller-supplied Advise evidence refs. The endpoint returns source-safe
   candidate or blocked posture only and redacts raw route and content-hash
   details from candidate source refs.
9. `tests/integration/test_missing_risk_profile_signal_api.py` covers
   candidate creation, stale-source blocking, permission denial, and
   source-redaction behavior for the certified API contract.
10. This foundation does not include data-mesh certification, Workbench proof,
    client-publication approval, or supported-feature promotion.

Additional implemented mandate/restriction review foundation:

1. `src/app/domain/mandate_restriction_signal.py` defines
   `MandateRestrictionSignalPolicy`, `MandateRestrictionSignalInput`, and
   `evaluate_mandate_restriction_signal` for compliance-review candidates under
   the mandate or restriction review archetype.
2. The evaluator consumes only source-owned restriction posture supplied as
   evidence: restriction status, changed-since-last-review flag,
   actionability-blocked flag, source freshness, entitlement posture, and
   source refs. It does not approve suitability, change mandate state, clear
   restrictions, create orders, create product recommendations, publish client
   communication, or execute downstream actions.
3. `src/app/application/mandate_restriction_signal.py` provides the framework-
   free command wrapper, and `src/app/api/idea_signals.py` exposes the bounded
   `POST /api/v1/idea-signals/mandate-restriction/evaluate` API over
   caller-supplied Core, Manage, or Advise evidence refs.
4. `tests/unit/test_mandate_restriction_signal_evaluation.py`,
   `tests/unit/test_mandate_restriction_application.py`, and
   `tests/integration/test_mandate_restriction_signal_api.py` cover positive,
   not-eligible, stale-source, missing-source, missing-posture, duplicate,
   entitlement-denied, permission-denied, and source-redaction cases.
5. `src/app/application/mandate_restriction_source_product_proof.py`,
   `scripts/generate_mandate_restriction_source_product_proof.py`, and
   `make mandate-restriction-source-product-proof-contract-gate` define a
   source-safe typed Advise mandate/restriction source-product proof artifact.
   A valid artifact can clear only
   `opportunity_archetype_typed_restriction_source_product_missing` in
   aggregate readiness.
6. `src/app/application/mandate_restriction_live_proof.py`,
   `scripts/generate_mandate_restriction_live_proof.py`, and
   `make mandate-restriction-live-proof-contract-gate` define a separate
   source-safe live Advise mandate/restriction diagnostic proof. A valid
   artifact can clear only
   `opportunity_archetype_live_restriction_source_proof_missing` in aggregate
   readiness.
7. This foundation does not include restriction clearance, mandate-state
   authority, data-mesh certification, Workbench proof, client-publication
   approval, or supported-feature promotion.

Additional implemented low-income / liquidity-shortfall foundation:

1. `src/app/domain/signal_evaluation.py` now defines
   `LowIncomeSignalPolicy`, `LowIncomeSignalInput`, and
   `evaluate_low_income_signal` for source-backed cashflow pressure review
   candidates.
2. The evaluator consumes only Core-owned `PortfolioCashflowProjection:v1` and
   `PortfolioCashMovementSummary:v1` source refs, current source freshness,
   Core-reported cashflow count, and a source-reported minimum projected
   cumulative cashflow value. It does not infer client income needs, funding
   advice, treasury instruction, suitability, or planning objectives.
3. `src/app/ports/core_sources.py`,
   `src/app/application/low_income_signal.py`, and
   `src/app/infrastructure/lotus_core_sources.py` add the Core source-port,
   application wrapper, and fail-closed adapter over
   `/portfolios/{portfolio_id}/cash-movement-summary` and
   `/portfolios/{portfolio_id}/cashflow-projection`.
4. Positive evaluation creates only an advisor-review candidate with
   deterministic IDs and policy-versioned score when projected cumulative
   cashflow breaches the threshold. Missing, stale, malformed, duplicate, or
   entitlement-blocked source evidence does not create a candidate.
5. `tests/unit/test_low_income_signal_evaluation.py`,
    `tests/unit/test_low_income_application.py`, and
    `tests/unit/test_lotus_core_sources.py` cover positive, not-eligible,
    stale, missing-source, duplicate, entitlement-denied, source-unavailable,
    malformed-projection, and request-validation cases.
6. `src/app/api/low_income_signals.py` exposes
   `POST /api/v1/idea-signals/low-income/evaluate` as a bounded
   caller-supplied API foundation over Core cashflow projection and cash
   movement evidence. It requires advisor role and `idea.signal.evaluate` capability,
   emits source-authority-preserving operation events, redacts source routes and
   content hashes from response candidates, and does not fetch Core sources,
   infer client income needs, approve planning suitability, provide funding
   advice, issue treasury instructions, publish client communication, certify a
   data product, or promote a supported feature.
7. `tests/integration/test_low_income_signal_api.py` and
   `tests/integration/test_api_operation_events.py` cover candidate creation,
   not-eligible posture, stale-source blocker, permission denial,
   source-redacted response projection, and bounded signal-evaluation operation
   events for the caller-supplied API foundation.
8. `src/app/application/low_income_core_cashflow_live_proof.py`,
    `scripts/generate_low_income_core_cashflow_live_proof.py`, and
    `make low-income-core-cashflow-live-proof-contract-gate` define a
   source-safe live Core cashflow proof artifact. A valid artifact proves live
   `lotus-core:PortfolioCashflowProjection:v1` and
   `lotus-core:PortfolioCashMovementSummary:v1` source calls, current source
   evidence, and deterministic low-income / liquidity-shortfall candidate
   posture, then clears only the namespaced opportunity-archetype live Core
   cashflow source blocker when consumed by aggregate readiness.
9. This foundation does not include data-mesh certification, Workbench proof,
    client-publication approval, supported-feature promotion, income-needs
    certification, funding advice, treasury instruction, suitability, or
    planning objective proof.

Additional implemented mandate health source-product ref foundation:

1. `src/app/ports/performance_sources.py` now defines a direct
   `PerformanceMandateHealthSourcePort` for
   `lotus-performance:MandatePerformanceHealthContext:v1` source refs when
   supplied source-owned period-return facts are available.
2. `src/app/infrastructure/lotus_performance_sources.py` calls
   `POST /performance/mandate-health-context`, validates the Performance source
   product identity, preserves the source-owned request fingerprint as lineage
   content hash, and does not calculate active return or performance health
   locally.
3. `src/app/ports/risk_sources.py` now defines a direct
   `RiskMandateHealthSourcePort` for
   `lotus-risk:MandateRiskHealthContext:v1` source refs when supplied
   source-owned return observations and benchmark-return observations are
   available.
4. `src/app/infrastructure/lotus_risk_sources.py` calls
   `POST /analytics/risk/mandate-health-context`, validates the Risk source
   product identity, preserves the source-owned request fingerprint as lineage
   content hash, and does not calculate tracking error, risk health, or risk
   methodology locally.
5. These are internal design-module foundations inside the existing
   `lotus-idea` deployable. They do not introduce a runtime service, worker,
   queue, scheduled fetch, or separately scalable process boundary.
6. Because the upstream stateless source-product responses do not publish
   freshness metadata, the preserved direct source refs remain explicit
   `UNAVAILABLE` freshness refs until live source proof or richer source
   telemetry supplies current freshness evidence.
7. This clears only the direct Performance/Risk mandate-health source-port and
   adapter-ref blocker for supplied source facts. It does not certify live
   source fetching, Manage portfolio-scoped live proof, Gateway/Workbench
   proof, data-product certification, client-publication readiness, or
   supported-feature promotion.

Not implemented yet:

1. live Risk concentration source proof captured from an actual canonical
   runtime and merged as release evidence,
2. live Performance returns-series source proof captured from an actual
   canonical runtime and merged as release evidence,
3. live Performance benchmark-readiness proof captured from an actual canonical
   runtime and merged as release evidence,
4. portfolio-scoped Manage, mandate performance-health, and mandate risk-health
   live proof beyond the source-safe Manage mandate proof contract and Core
   portfolio-state source-ref proof,
5. source-worker certification beyond bounded live Core source-ingestion proof,
6. certified long-running scheduled daemon runtime and live-service recovery proof,
7. source-fetching APIs beyond bounded high-cash, low-income, bond-maturity,
   missing-benchmark, concentration-risk, high-volatility, and drawdown-review `evaluate-from-source`
   evaluation,
8. Gateway/Workbench proof,
9. supported-feature promotion,
10. data-product certification.

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

Current source-fetching API validation:

1. `python -m pytest tests\integration\test_high_cash_signal_api.py tests\unit\test_source_ingestion_state.py -q`
   passed with `47 passed`, covering Core-backed evaluation, portfolio
   entitlement denial before runtime construction, missing Core runtime
   configuration, Core source unavailability, runtime cleanup-failure
   suppression, and manifest-free Core source runtime construction.
2. `python -m ruff check src\app\api\idea_signals.py src\app\api\idea_signal_models.py src\app\api\runtime_dependencies.py src\app\runtime\source_ingestion_state.py tests\integration\test_high_cash_signal_api.py tests\unit\test_source_ingestion_state.py`
   passed.
3. `python -m pytest tests\integration\test_low_income_signal_api.py tests\unit\test_source_ingestion_state.py tests\unit\test_service_contract.py -q`
   passed with `44 passed`, covering low-income Core-backed evaluation,
   portfolio entitlement denial before runtime construction, missing Core
   runtime configuration, Core source unavailability, runtime cleanup-failure
   suppression, endpoint-ledger registration, and manifest-free Core source
   runtime construction.
4. `python -m pytest tests\integration\test_missing_benchmark_signal_api.py tests\unit\test_source_ingestion_state.py tests\unit\test_service_contract.py -q`
   passed with `47 passed`, covering missing-benchmark Core-backed evaluation, reporting-currency
   normalization, portfolio entitlement denial before runtime construction,
   missing Core runtime configuration, Core source unavailability,
   cleanup-failure suppression, endpoint-ledger registration, and
   manifest-free Core source runtime construction.
5. `python -m pytest tests\integration\test_bond_maturity_signal_api.py tests\unit\test_source_ingestion_state.py tests\unit\test_service_contract.py -q`
   passed, covering bond-maturity Core-backed evaluation, portfolio entitlement
   denial before runtime construction, missing Core runtime configuration,
   Core source unavailability, cleanup-failure suppression,
   endpoint-ledger registration, and manifest-free Core source runtime
   construction.
6. `python -m pytest tests\integration\test_concentration_risk_signal_api.py tests\unit\test_source_ingestion_state.py tests\unit\test_lotus_risk_sources.py -q`
   passed with `71 passed`, covering concentration-risk Lotus Risk-backed
   evaluation, portfolio entitlement denial before runtime construction,
   missing Risk runtime configuration, Risk source unavailability, route-owned
   runtime cleanup, manifest-free Risk source runtime construction, and adapter
   close delegation.
7. `python -m ruff check src\app\api\concentration_risk_signals.py src\app\api\caller_context_openapi.py src\app\api\runtime_dependencies.py src\app\runtime\source_ingestion_state.py src\app\infrastructure\lotus_risk_sources.py tests\integration\test_concentration_risk_signal_api.py tests\unit\test_source_ingestion_state.py tests\unit\test_lotus_risk_sources.py`
   passed.
8. `python -m pytest tests\integration\test_high_volatility_signal_api.py tests\integration\test_signal_source_operation_events.py::test_high_volatility_source_api_emits_blocked_operation_event tests\unit\test_source_ingestion_state.py tests\unit\test_lotus_risk_sources.py tests\unit\test_service_contract.py -q`
   covers high-volatility Lotus Risk-backed evaluation, portfolio entitlement
   denial before runtime construction, missing Risk runtime configuration, Risk
   source unavailability, route-owned runtime cleanup, manifest-free Risk
   source runtime construction, adapter request-shape/source-ref preservation,
   endpoint-ledger registration, and bounded operation-event proof.
9. `python -m pytest tests\integration\test_drawdown_review_signal_api.py tests\integration\test_signal_source_operation_events.py::test_drawdown_review_source_api_emits_blocked_operation_event tests\unit\test_source_ingestion_state.py tests\unit\test_lotus_risk_drawdown_sources.py tests\unit\test_service_contract.py -q`
   covers drawdown-review Lotus Risk-backed evaluation, portfolio entitlement
   denial before runtime construction, missing Risk runtime configuration, Risk
   source unavailability, route-owned runtime cleanup, manifest-free Risk
   source runtime construction, adapter close delegation, endpoint-ledger
   registration, and bounded operation-event proof.
10. This closes only the bounded high-cash, low-income, bond-maturity,
   missing-benchmark, concentration-risk, high-volatility, and drawdown-review source-fetching API foundations.
   It does not certify live Core or Risk source support, source-worker operation,
   Gateway/Workbench support, data-product certification, benchmark assignment,
   benchmark methodology authority, performance calculation, maturity schedule
   authority, replacement product recommendation, reinvestment advice,
   income-needs assessment, funding advice, treasury instruction, planning
   suitability, risk methodology approval, concentration calculation, trade
   recommendation, rebalance action, volatility calculation, VaR calculation,
   tracking-error calculation, drawdown calculation, client publication, or
   supported-feature promotion.

Current mandate health source-product ref validation:

1. `.venv\Scripts\python.exe -m pytest tests\unit\test_lotus_performance_sources.py tests\unit\test_lotus_risk_mandate_health_sources.py -q`
   passed with `36 passed`, covering direct Performance and Risk mandate-health
   source-product request payloads, trace/correlation propagation, source
   product identity validation, source-owned request-fingerprint lineage,
   explicit unavailable freshness posture, and entitlement-denied fail-closed
   behavior.
2. This closes only the supplied-source-fact source-port and adapter-ref
   foundation. It does not certify live source fetching, live canonical runtime
   proof, source-worker operation, Gateway/Workbench support, data-product
   certification, or supported-feature promotion.

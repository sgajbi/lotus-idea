# RFC-0002 Slice 17: Implementation Proof And Live Validation

Status: Partially implemented - aggregate proof-readiness diagnostic, bounded source-ingestion runtime-execution receipt contract, scheduled-worker deploy-contract proof, durable repository proof artifact, runtime telemetry test-execution artifact, Workbench read-path source-contract proof artifact, Gateway/Workbench contract proof artifact, Gateway/Workbench discovery contract proof artifact, digest-bound Advise and Manage route source contracts, closed v2 Manage mandate runtime evidence, receipt-bound Core portfolio-state, bond-maturity, low-income cashflow, missing-benchmark Core, and Performance benchmark-readiness runtime evidence, Report intake route and materialization source-contract artifacts, bounded outbox broker source-contract proof artifact, bounded downstream consumer source-contract proof artifact, bounded outbox platform-mesh event source-contract proof, digest-bound mesh policy source-contract artifact, platform catalog source contract artifact, AI lineage store proof artifact, AI workflow-pack registration proof artifact, AI workflow-pack runtime execution proof artifact, high-volatility and drawdown live Risk proof artifact contracts, and opportunity archetype scenario readiness with source/policy foundations available. Historical canonical Risk concentration and Performance artifacts exist for `PB_SG_GLOBAL_BAL_001`, but retired flat-v1 Performance evidence no longer qualifies under current v2 contracts and fresh runtime capture is required. Core portfolio-state, bond-maturity, and low-income cashflow live qualification remain fail-closed pending lotus-core #790, #792, and #796, and Manage mandate-health qualification remains fail-closed pending lotus-manage #620. Observed Advise/Manage route serving and acceptance, policy certification, Report intake and materialization execution, rendered output, archive creation, external broker publication, platform-mesh event publication, downstream consumer execution, full live opportunity-journey proof, data-mesh certification, Workbench product proof, client-publication approval, and supported-feature promotion remain pending.

## Outcome

Prove the complete supported opportunity journey end to end.

## Current Implementation Evidence

1. `src/app/application/implementation_proof_readiness.py` builds a
   machine-readable RFC-0002 proof-readiness snapshot over current internal
   implementation foundations and known proof blockers.
2. `GET /api/v1/implementation-proof/readiness` exposes the snapshot as a
   certified internal operator endpoint with
   `idea.implementation-proof.readiness.read` capability enforcement.
3. `scripts/generate_implementation_proof_readiness.py` accepts explicit
   source-ingestion manifest, live-proof, scheduled-worker proof, and durable
   repository proof paths. `make implementation-proof-readiness-check` now
   generates the scheduled source-ingestion worker deploy-proof artifact and
   durable repository proof artifact before producing the same source-safe
   readiness snapshot as repo-native automation evidence without requiring the
   HTTP service to run.
4. `docs/operations/endpoint-certification-ledger.json` certifies the endpoint
   as an internal operator diagnostic and preserves the no-full-live-journey,
   no-Gateway-product-support, no-Workbench-product-support,
   no-client-ready-publication, and no-supported-feature-promotion boundary.
5. Unit and integration tests prove blocked posture, source-safe output,
   permission denial, timezone validation, unavailable-contract handling, and
   bounded `implementation_proof_readiness_read` operation events.
6. `make endpoint-certification-gate` now requires every certified
   business/operator endpoint to cite both a non-operation-event integration
   API behavior test and negative or degraded-path test evidence, in addition
   to existing OpenAPI, product-safe error, capability, boundary, and
   operation-event evidence. This prevents API certification from relying only
   on schema examples, unit-only assertions, or telemetry-only tests.
7. `GET /api/v1/downstream-realization/readiness` now supplies the downstream
   realization proof family used by the aggregate diagnostic. It reports
   Advise, Manage, Report, Render, and Archive blockers with current
   conversion/report workflow counts, while preserving the no-downstream-call
   and no-supported-feature boundary.
8. `GET /api/v1/outbox-delivery/readiness` and
   `POST /api/v1/outbox-delivery/run-once` now supply the outbox-delivery
   proof family used by the aggregate diagnostic. Readiness reports broker,
   downstream-consumer, platform mesh-event, Gateway/Workbench, and
   supported-feature blockers. Run-once proves the bounded internal publisher
   orchestration surface and fail-closed broker configuration behavior without
   exposing event identifiers, exposing raw idempotency keys, exposing broker
   payloads, or claiming downstream delivery.
   `scripts/outbox/broker/generate_source_contract_proof.py` and
   `make outbox-broker-source-contract-proof-gate` generate and validate the
   bounded outbox broker source-contract artifact consumed by aggregate
   implementation-proof readiness. A valid artifact adds provenance but clears
   no blocker. `outbox_broker_not_configured`,
   `external_broker_runtime_proof_missing`, downstream consumer runtime,
   platform mesh event, Gateway/Workbench, and supported-feature blockers
   remain.
8. `contracts/outbox-events/lotus-idea-outbox-consumers.v1.json` and
   `make outbox-consumer-contract-gate` now declare the Gateway, Advise,
   Manage, and Report outbox consumers with source-authority boundaries. This
   removes the stale missing-contract posture while leaving observed runtime
   execution and downstream delivery unsupported.
9. `scripts/outbox/generate_consumer_contract_proof.py` and
   `make outbox-consumer-contract-proof-contract-gate` generate and validate
   the bounded downstream consumer source-contract artifact consumed by
   aggregate implementation-proof readiness. A valid v2 artifact is useful
   evidence of declared coverage and authority boundaries, but clears no
   runtime blocker. `downstream_consumer_runtime_proof_missing`, platform mesh
   event, Gateway/Workbench, downstream delivery, and supported-feature
   blockers remain.
10. `scripts/outbox/platform_mesh/generate_source_contract_proof.py` and
    `make outbox-platform-mesh-event-source-contract-proof-gate` now
    generate and validate the bounded outbox platform-mesh event
    source-contract proof consumed by aggregate implementation-proof readiness.
    A valid artifact adds provenance and clears no blocker after repo-owned
    outbox event and consumer contracts plus sibling platform
    source-manifest/catalog onboarding evidence validate. The
    `platform_mesh_event_publication_proof_missing` blocker remains with
    external broker publication, downstream delivery, Gateway/Workbench,
    client-ready publication, and supported-feature blockers.
11. `make downstream-realization-contract-gate` now validates the planned
   downstream realization contract plan used by the downstream readiness proof
   family, so proof blockers stay source-authority preserving and cannot be
   rewritten as route-existence or downstream-execution claims.
9. `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot` now supplies the
   contract-shaped runtime trust telemetry test-execution evidence family used by operators and
   certification reviewers before platform mesh promotion. It remains blocked
   and not certified, omits source-sensitive identifiers, and does not replace
   platform certification or supported-feature promotion.
10. `POST /api/v1/source-ingestion/run-once` now supplies the bounded internal
    source-ingestion operator proof surface. It can exercise the configured
    manifest and Core source adapter only when durable repository posture is
    active, returns aggregate decision counts only, and remains not certified
    until bounded live Core source proof, certified long-running scheduling proof,
    data-mesh runtime telemetry, Gateway/Workbench proof, and supported-feature
    promotion evidence exist.
11. `src/app/application/source_ingestion_runtime_evidence/runtime_execution.py`,
    `scripts/source_ingestion/generate_runtime_execution.py`, and
    `make source-ingestion-runtime-execution-contract-gate` now define and enforce the
    source-safe live Core proof artifact shape. The source-ingestion readiness
    diagnostic may report a family-valid configured artifact, but aggregate
    implementation-proof readiness clears only `live_core_source_proof_missing`
    when the artifact is also aggregate-current with matching proof ref,
    freshness, and source revision; scheduled worker, data-mesh,
    Gateway/Workbench, and supported-feature blockers remain.
    The artifact now carries aggregate `blockReasonCounts` for blocked proof
    attempts, with bounded codes for Core source unavailability, entitlement
    denial, missing cash-weight evidence, and Core-reported cash-weight
    supportability blockers. This improves live-proof diagnosis without
    exposing source payloads or reconstructing cash weight in `lotus-idea`.
12. `src/app/application/source_ingestion_scheduled_worker.py`,
    `scripts/run_scheduled_source_ingestion_worker.py`,
    `scripts/generate_scheduled_source_ingestion_worker_proof.py`, and
    `make source-ingestion-scheduled-worker-check` now define and enforce the
    source-safe scheduled worker deploy-contract proof shape. When a valid
    artifact is referenced through
    `LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_PROOF`, the
     source-ingestion readiness diagnostic can clear only
     `scheduled_worker_deploy_proof_missing`; live Core, data-mesh,
     Gateway/Workbench, and supported-feature blockers remain.
13. `make implementation-proof-readiness-check` now generates that scheduled
    worker deploy-proof artifact under ignored `output/source-ingestion/` and
    passes it explicitly into aggregate proof-readiness generation, so repo-native
    evidence no longer reports a stale scheduled-worker deploy-proof blocker
    after the deploy contract is validated. Aggregate implementation-readiness
    evidence records validated live and scheduled source-ingestion proof
    artifact refs in the `source-ingestion` capability when those blockers are
    cleared. The same valid live Core source-ingestion artifact can now clear
    only `opportunity_archetype_live_core_source_proof_missing` for the
    high-cash scenario inside aggregate opportunity-archetype readiness.
14. `src/app/application/durable_repository_proof/`,
    `scripts/persistence/generate_durable_repository_proof.py`, and
    `make durable-repository-proof-contract-gate` now define and enforce a
    source-safe durable repository proof artifact. The aggregate
    implementation-readiness generator can consume that artifact to clear only
    the stale aggregate `durable_repository_not_configured` and
    `repository_side_queue_pagination_not_certified` proof blockers while
    preserving live Core, production storage, runtime trust telemetry,
    data-mesh, Gateway/Workbench, downstream, and supported-feature blockers.
15. `src/app/application/runtime_trust_telemetry/test_execution_contract.py`,
    `scripts/runtime_trust_telemetry/generate_test_execution_contract.py`, and
    `make runtime-trust-telemetry-test-execution-contract-gate` now define and enforce a
    source-safe v2 runtime trust telemetry `test_execution` artifact. The
    aggregate implementation-readiness generator records valid current
    evidence as provenance but clears no blocker. It preserves
    `runtime_candidate_snapshot_missing`, `durable_repository_not_configured`,
    and product-coverage
    blockers (`runtime_trust_telemetry_product_coverage_incomplete`,
    `certified_runtime_trust_telemetry_missing`, and
    `data_mesh_runtime_telemetry_not_certified`) plus platform source-manifest,
    platform mesh, active producer product, Gateway/Workbench discovery, and
    supported-feature blockers.
16. `lotus-workbench` PR #391 merged bounded read-only Workbench rendering for
    the Gateway-published advisor queue and source-safe candidate detail. The
    live-validation script now fails unless a populated candidate row, loaded
    detail posture, non-empty source count, and observed candidate-detail route
    are present before screenshot evidence is recorded. This clears only the
    prior absence of a Workbench read-path implementation; it does not certify
    live source ingestion, entitlement-denied panel proof, mutation
    affordances, downstream realization, data-product certification, or
    supported-feature promotion.
17. Issue `#434` replaces the flat Workbench read-path artifact with
    `src/app/application/workbench/read_path_source_contract.py`,
    `scripts/workbench/generate_read_path_source_contract.py`, and
    `make workbench-read-path-source-contract-proof-gate`. The v2
    `source_contract` artifact records source-safe queue/detail declarations,
    clears no blocker, and preserves
    `workbench_gateway_bff_consumption_proof_missing` until the owning Gateway
    and Workbench runtimes provide machine-verifiable serving, consumption,
    entitlement, and browser evidence. This is design modularity only; no new
    deployable is introduced.
18. `src/app/application/workbench/contract_proof.py`,
    `scripts/workbench/generate_contract_proof.py`, and
    `make gateway-workbench-contract-proof-contract-gate` now define and
    enforce a source-safe Gateway/Workbench contract proof artifact. The
    artifact declares evidence class `source_contract`; aggregate
    implementation readiness records its reference without clearing
    `gateway_workbench_proof_missing` for either source-ingestion or
    outbox-delivery. It also preserves Workbench product,
    panel, browser accessibility, canonical demo runtime, data-product
    discovery, client-publication, and supported-feature blockers.
19. `src/app/application/workbench/discovery_contract_proof.py`,
    `scripts/workbench/generate_discovery_contract_proof.py`, and
    `make gateway-workbench-discovery-contract-proof-contract-gate` now define
    and enforce a source-safe Gateway/Workbench discovery contract proof
    artifact. The aggregate implementation-readiness generator records that
    artifact as evidence for data-mesh and runtime trust telemetry test-execution evidence
    families without clearing `gateway_workbench_discovery_proof_missing`.
    Data-mesh certification, producer product activation, platform mesh
    certification, Workbench product proof, client publication, and
    supported-feature blockers remain.
19. `src/app/runtime/proof_artifacts.py` now gives the certified operator API
    the same source-safe artifact-ref path as the aggregate generator for
    source-ingestion runtime-execution receipt, source-ingestion scheduled-worker proof,
    durable repository, runtime trust telemetry, Workbench read-path, outbox
    broker, platform catalog source contract, and AI lineage store proofs. `tests/unit/test_proof_artifacts.py`,
    `tests/unit/test_implementation_proof_readiness.py`, and
    `tests/integration/test_implementation_proof_readiness_api.py` prove that
    configured valid artifacts clear only their intended aggregate blockers,
    record source-safe evidence refs, and keep the API `blocked`,
    `not_certified`, and unpromoted.
19. The aggregate `ai-explanation` capability evidence now cites
    `contracts/observability/lotus-idea-ai-model-risk-operations.v1.json` and
    `make ai-model-risk-ops-contract-gate`. This makes the not-certified
    dashboard-control and alert-candidate posture visible in proof-readiness
    evidence without clearing dashboard provisioning, alert-rule runtime,
    `lotus-ai` runtime, runtime trust telemetry, Workbench, or
    supported-feature blockers.
20. `src/app/application/ai_lineage_store_proof.py`,
    `scripts/generate_ai_lineage_store_proof.py`, and
    `make ai-lineage-store-proof-contract-gate` now define and enforce a
    source-safe AI lineage store proof artifact. The aggregate
    implementation-readiness generator and operator API consume that artifact
    to clear only `certified_ai_lineage_store_missing`, while preserving
    `lotus-ai` runtime execution, workflow-pack runtime, model-risk
    dashboard/alert, runtime trust telemetry, Workbench, client-ready
    publication, and supported-feature blockers.
21. `src/app/application/data_mesh/platform_catalog_source_contract.py`,
    `scripts/data_mesh/generate_platform_catalog_source_contract.py`, and
    `make platform-catalog-source-contract-proof-gate` now define and enforce
    a bounded cross-repo platform catalog source contract. Issue `#443`
    classifies it as `source_contract`, binds the exact source manifest,
    catalog, dependency graph, and maturity matrix by SHA-256, and closes the
    accepted field vocabulary against claim inflation. The repo-native
    `make implementation-proof-readiness-check` target generates the default
    artifact from `LOTUS_PLATFORM_ROOT`, tolerates absent sibling evidence by
    writing an invalid non-proof artifact, and passes it into aggregate
    readiness unless `LOTUS_IDEA_PLATFORM_CATALOG_SOURCE_CONTRACT_PROOF`
    overrides the path. The aggregate readiness generator consumes a valid,
    current artifact to satisfy only
    `platform_source_manifest_inclusion_missing` and
    `platform_catalog_inclusion_missing`, while preserving mesh certification,
    product activation, SLO/access/evidence, Gateway/Workbench, deployment,
    production-certification, and supported-feature blockers. The dependent
    Workbench discovery contract consumes the renamed source contract without
    treating it as runtime discovery evidence.
22. `src/app/application/data_mesh/mesh_policy_source_contract.py`,
    capability-owned `scripts/data_mesh/` automation, and
    `make mesh-policy-source-contract-proof-gate` define and enforce the
    digest-bound repo-owned mesh policy source contract. The repo-native
    `make implementation-proof-readiness-check` target generates the default
    artifact under `output/data-mesh/mesh-policy-source-contract.json` and
    passes it into aggregate readiness unless
    `LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF` overrides the path. A valid
    current artifact contributes supporting evidence only; SLO, access,
    evidence-policy, mesh certification, product activation, platform catalog,
    Gateway/Workbench, deployment, production, and supported-feature blockers
    remain intact.
23. `src/app/application/downstream_realization/route_source_contract.py`,
    `scripts/downstream_realization/generate_advise_route_source_contract.py`,
    `scripts/downstream_realization/generate_manage_route_source_contract.py`, and
    `make downstream-route-source-contract-proof-gate` now define and enforce
    digest-bound Advise and Manage route `source_contract` artifacts. The
    aggregate implementation-readiness generator and operator API consume valid
    artifacts as supporting evidence while preserving
    `advise_live_contract_proof_missing`, `manage_live_contract_proof_missing`, suitability,
    policy approval, mandate/rebalance authority, execution, order creation,
    client-publication, and supported-feature blockers.
24. `src/app/application/report/intake_route_source_contract.py`,
    `scripts/report/generate_intake_route_source_contract.py`, and
    `make report-intake-route-source-contract-proof-gate` now define and enforce a
    v2 `source_contract` artifact for the declared `lotus-report` intake route.
    The aggregate implementation-readiness generator and operator API consume
    that artifact as provenance while clearing no blocker and preserving
    `lotus_report_live_intake_route_proof_missing`, together with
    preserving report materialization, render output, archive record,
    client-publication, and supported-feature blockers.
25. `src/app/application/ai_workflow_pack_registration/source_contract_proof.py`,
    `scripts/ai_workflow_pack_registration/generate_source_contract_proof.py`, and
    `make ai-workflow-pack-registration-proof-contract-gate` now define and
    enforce a v2 source-safe sibling `lotus-ai` workflow-pack registration source contract
    artifact. The aggregate implementation-readiness generator and operator
    API consume that artifact as an evidence reference while preserving
    `workflow_pack_runtime_contract_not_certified`,
    `lotus-ai` runtime execution, provider invocation, runtime trust telemetry,
    Workbench, client-publication, and supported-feature blockers. Model-risk
    dashboard and alert source validation is handled by the separate
    model-risk operations proof gate.
26. `src/app/application/ai_runtime_proof/`,
    `src/app/ports/lotus_ai_runtime.py`,
    `src/app/infrastructure/lotus_ai/workflow_runtime.py`,
    `scripts/generate_ai_workflow_pack_runtime_execution_proof.py`, and
    `make ai-workflow-pack-runtime-execution-proof-contract-gate` now define
    and enforce an actual, source-safe Lotus AI workflow-pack runtime execution
    receipt. The generator invokes `idea_explanation.pack@v1`, validates exact
    caller, pack, run, task, evidence-hash, completion, review, and authority
    posture, then persists only a bounded digest-bound receipt. Aggregate
    readiness clears `lotus_ai_runtime_execution_missing` and adds
    `lotus_ai_live_provider_execution_missing`, preserving workflow-pack
    registration, provider rollout, runtime trust telemetry, Workbench,
    client-publication, and supported-feature blockers.
    Model-risk dashboard and alert source validation is handled by the
    separate model-risk operations proof gate.
27. The aggregate readiness diagnostic now includes an
    `opportunity-archetype-scenarios` capability built from
    `contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`.
    It exposes source-safe taxonomy evidence, records concentration risk review
    as a bounded source/policy foundation, and namespaced
    `opportunity_archetype_*` blockers for live proof, data-mesh
    certification, Workbench proof, client-publication, and supported-feature
    gaps while preserving the no-demo, no-client-publication,
    no-data-mesh-certification, and no-supported-feature-promotion boundaries.
28. `src/app/application/risk_concentration_runtime_evidence/`,
    `scripts/risk_concentration_runtime_evidence/`, and
    `make risk-concentration-live-proof-contract-gate` now define and enforce
    closed v2 `runtime_execution` evidence. The artifact reconciles one current
    Lotus Risk source receipt with the authoritative deterministic use-case
    result and one durable accepted/replayed Idea persistence receipt.
    Aggregate readiness can clear only
    `opportunity_archetype_live_risk_source_proof_missing`; data-mesh,
    Workbench, client-publication, deployment, production, and
    supported-feature blockers remain.
29. `src/app/application/high_volatility_runtime_evidence/`,
    `scripts/high_volatility_runtime_evidence/`, and
    `make high-volatility-live-proof-contract-gate` define and enforce a closed
    v2 Lotus Risk high-volatility `runtime_execution` contract. It binds current
    Risk source evidence and the authoritative use-case result to accepted or
    replayed durable Idea persistence. Aggregate readiness can clear only
    `opportunity_archetype_live_risk_volatility_source_proof_missing`, while
    preserving drawdown, data-mesh, Workbench, client-publication, deployment,
    production, and supported-feature blockers.
30. `src/app/application/risk_drawdown_runtime_evidence/`,
    `scripts/risk_drawdown_runtime_evidence/`, and the compatibility target
    `make risk-drawdown-live-proof-contract-gate` define and enforce a closed
    v2 Lotus Risk drawdown `runtime_execution` contract. It binds current Risk
    source evidence and the authoritative use-case result to accepted or
    replayed durable Idea persistence. Aggregate readiness can clear only
    `opportunity_archetype_drawdown_source_proof_missing`, while preserving
    volatility, data-mesh, Workbench, client-publication, deployment,
    production, and supported-feature blockers.
31. `src/app/application/performance_underperformance_runtime_evidence/`,
    `scripts/performance_underperformance_runtime_evidence/`, and
    `make performance-underperformance-live-proof-contract-gate` now define and
    enforce a closed v2 Lotus Performance underperformance
    `runtime_execution` artifact bound to accepted or replayed durable Idea
    persistence. Aggregate readiness can consume a valid artifact to clear only
    `opportunity_archetype_live_performance_source_proof_missing`, while
    preserving benchmark-assignment, data-mesh, Workbench, client-publication,
    deployment, production, and supported-feature blockers.
32. `src/app/application/core_benchmark_assignment_runtime_evidence/`,
    `scripts/core_benchmark_assignment_runtime_evidence/`, and
    `make core-benchmark-assignment-live-proof-contract-gate` now define and
    enforce closed v2 Lotus Core benchmark-assignment `runtime_execution`
    evidence bound to a named application use case and exact current source
    receipt.
    Aggregate readiness can consume a valid artifact to clear only
    `opportunity_archetype_benchmark_assignment_source_ref_missing`, while
    preserving live Performance, data-mesh, Workbench, client-publication,
    deployment, production, and supported-feature blockers. The read-only
    proof has no fabricated persistence receipt and does not assign benchmarks,
    calculate returns, or certify methodology.
33. `src/app/domain/missing_benchmark_signal.py`,
    `src/app/application/missing_benchmark_signal.py`,
    `src/app/application/core_missing_benchmark_runtime_evidence/`, and
    `scripts/core_missing_benchmark_runtime_evidence/` now define a bounded
    missing-benchmark review policy, source-preserving Core use case, and closed
    v2 runtime artifact. One Core fetch is bound to pseudonymous request scope,
    exact current assignment evidence, canonical assignment-state and
    evaluation digests, and either a deterministic review candidate or truthful
    ready-assignment no-opportunity result. Aggregate readiness can consume a
    valid artifact to clear only
    `opportunity_archetype_missing_benchmark_live_core_source_proof_missing`,
    while preserving Performance benchmark-readiness, data-mesh, Workbench,
    client-publication, deployment, production, and supported-feature blockers.
    Unknown fields, stale/future evidence, scope/assignment drift, conflicting
    diagnostics, and semantic tampering fail closed. Retired flat v1 paths are
    prohibited. The proof does not assign benchmarks, calculate benchmark
    returns, or certify benchmark methodology.
34. `src/app/application/performance_benchmark_readiness.py`,
    `src/app/application/performance_benchmark_readiness_runtime_evidence/`,
    `scripts/performance_benchmark_readiness_runtime_evidence/`, and
    `make missing-benchmark-performance-readiness-proof-contract-gate` now
    define and enforce closed v2 Lotus Performance benchmark-readiness
    `runtime_execution` evidence for missing-benchmark review. A named
    source-preserving use case performs one fetch and binds pseudonymous request
    scope to the exact `ReturnsSeriesBundle:v1` product/route/time, calculation
    and input hashes, benchmark context, coverage counts, freshness, quality,
    producer correlation/trace, and deterministic review-required or
    no-opportunity evaluation receipts. Aggregate readiness can consume a valid
    current artifact to clear only
    `opportunity_archetype_performance_benchmark_readiness_source_ref_missing`,
    while preserving Core missing-benchmark live proof, data-mesh, Workbench,
    client-publication, deployment, production, and supported-feature blockers.
    Unknown fields, raw identifiers, stale/future evidence, scope/time/hash/count
    drift, contradictory context, diagnostic drift, and semantic tampering fail
    closed. The proof does not assign benchmarks, calculate performance or
    benchmark returns, or certify benchmark methodology.
35. Live canonical proof run on 2026-07-05 against `PB_SG_GLOBAL_BAL_001` and
    as-of date `2026-04-10` generated source-safe artifacts under ignored
    `output/opportunity/` for Risk concentration, Performance
    underperformance, and missing-benchmark Performance readiness. The
    artifacts reported `sourceEvidenceCurrent: true`, cleared only
    `opportunity_archetype_live_risk_source_proof_missing`,
    `opportunity_archetype_live_performance_source_proof_missing`, and
    `opportunity_archetype_performance_benchmark_readiness_source_ref_missing`,
    and were consumed by `make implementation-proof-readiness-check` with
    `IMPLEMENTATION_PROOF_EVALUATED_AT_UTC=2026-07-05T06:48:16Z`.
    The historical Performance benchmark-readiness artifact used the retired
    flat v1 contract and no longer qualifies after issue `#500`; a fresh v2
    receipt-bound runtime capture is required.
    Remaining blockers still include Core live source proof, benchmark
    assignment, Manage/performance/risk health source refs, data-mesh
    certification, Workbench product proof, client publication, and
    supported-feature promotion.
36. `src/app/application/low_income_cashflow_runtime_evidence/`,
    `scripts/low_income_cashflow_runtime_evidence/`, and
    `make low-income-core-cashflow-live-proof-contract-gate` now define and
    enforce closed v2 Lotus Core cashflow runtime evidence. A named application
    use case binds pseudonymous request scope, exact movement-summary and
    projection receipts, projection arithmetic, movement counts, policy, and
    deterministic candidate or no-opportunity outcome. Aggregate
    readiness can consume a valid artifact to clear only
    `opportunity_archetype_live_core_cashflow_source_proof_missing`, while
    preserving Workbench, data-mesh, client-publication, supported-feature,
    suitability, planning, funding-advice, treasury-instruction, deployment,
    and production blockers. Core issue `#796` tracks producer trust metadata
    required before live qualification can pass.
33. `src/app/application/manage_mandate_runtime_evidence/`,
    `scripts/manage_mandate_runtime_evidence/`, and
    `make manage-mandate-live-proof-contract-gate` now define and enforce a
    closed v2 Lotus Manage mandate runtime-evidence artifact. A named
    source-evaluation use case binds pseudonymous scope, exact action-register
    and mandate-health receipts, producer-authored time, policy, and
    deterministic candidate or no-opportunity outcome. Aggregate readiness
    can consume a valid artifact to clear only
    `opportunity_archetype_portfolio_scoped_manage_source_proof_missing`,
    `opportunity_archetype_mandate_performance_health_source_ref_missing`, and
    `opportunity_archetype_mandate_risk_health_source_ref_missing`, while
    preserving Core portfolio-state, data-mesh, Workbench, client-publication,
    supported-feature, rebalance, action, and order-execution blockers. Manage
    issue `#620` keeps live qualification fail closed until the producer supplies
    authoritative tenant, temporal, and source-ref identity.
34. `src/app/application/core_portfolio_state_runtime_evidence/`,
    `scripts/core_portfolio_state_runtime_evidence/`, and
    `make core-portfolio-state-live-proof-contract-gate` now define and enforce
    closed v2 Lotus Core portfolio-state runtime evidence. A named read-only
    use case binds pseudonymous request scope to the complete current
    `PortfolioStateSnapshot:v1` receipt, including snapshot identity, source
    hashes, restatement, reconciliation, evidence time, policy, correlation,
    and applied/dropped sections. Aggregate readiness can consume a valid
    artifact to clear only
    `opportunity_archetype_core_portfolio_state_source_ref_missing`, while
    preserving portfolio-scoped Manage proof, mandate performance-health,
    mandate risk-health, data-mesh, Workbench, client-publication,
    supported-feature, rebalance, action, and order-execution blockers.
35. `src/app/application/bond_maturity_runtime_evidence/`,
    `scripts/bond_maturity_runtime_evidence/`, and
    `make bond-maturity-live-proof-contract-gate` replace the caller-summary v1
    artifact with closed v2 `runtime_execution` evidence. A named read-only use
    case binds pseudonymous request scope to the exact current
    `PortfolioMaturitySummary:v1` receipt and upstream `HoldingsAsOf:v1`
    content identity. Exact horizon, non-projected mode, contractual maturity
    basis, response scope, counts, supportability, snapshot, hashes,
    restatement, reconciliation, evidence time, policy, and correlation must
    reconcile. A supported empty window completes with no opportunity; partial,
    stale, unsupported-product, inconsistent, or tampered evidence clears no
    blocker. A valid current artifact can satisfy only
    `opportunity_archetype_maturity_live_core_source_proof_missing`.
33. A family-valid and aggregate-current source-ingestion live Core proof
    referenced through `LOTUS_IDEA_SOURCE_INGESTION_RUNTIME_EXECUTION` now clears only
    `opportunity_archetype_live_core_source_proof_missing` for the high-cash
    scenario while preserving Workbench, data-mesh, client-publication, and
    supported-feature blockers.

This is a proof-control surface with bounded live source-ingestion evidence
support, not full live opportunity-journey proof. It makes missing evidence
durable and machine-readable so future implementation slices can clear blockers
without relying on chat memory.

## Required Work

1. Run repo-native checks and affected cross-repo gates.
2. Run canonical live validation through source APIs, `lotus-idea`, Gateway,
   Workbench, downstream conversion, report/render/archive where claimed, and
   AI fallback/provider paths.
3. Capture proof under non-git-tracked `output/` and summarize evidence in this
   slice file.
4. Critically review returned figures, statuses, reason codes, source refs,
   lineage refs, score, review state, AI posture, conversion outcome, and
   screenshots.

## Remaining Gap

1. Bounded live Core source-ingestion proof can be captured and consumed, but no
   canonical live proof run has been captured for the full opportunity journey.
2. Full Workbench live proof, live broker runtime, downstream materialization
   proof, render proof, archive proof, and client-publication proof remain
   pending.
3. Platform data-mesh certification, runtime trust telemetry, and mesh event
   certification remain pending.
4. Supported-feature promotion remains blocked until the readiness diagnostic
   reports no blockers and evidence is merged to `main`.
5. Durable repository proof is now explicit in aggregate readiness evidence, but
    deploy migration evidence, backup/restore, recovery operations, and
    production storage certification remain pending.
6. Runtime telemetry deterministic test execution is now explicit supporting
   evidence in aggregate readiness, but it clears no blocker; durable runtime,
   platform mesh certification, and product discovery proof remain pending.
7. Workbench read-path source-contract evidence is now explicit in aggregate
   readiness, but `workbench_gateway_bff_consumption_proof_missing`, full panel
   proof, browser accessibility proof, canonical demo runtime proof,
   entitlement-denied proof, mutation affordances, and supported-feature
   promotion remain pending.
8. Advise and Manage route source contracts are explicit in aggregate readiness
   evidence, but prove only digest-bound sibling declarations and clear no live
   blocker. Route serving/acceptance, suitability, policy approval, mandate/rebalance authority,
   execution, order creation, client communication, and supported-feature
   promotion remain pending.
9. Closed v2 Manage mandate runtime evidence is now explicit in aggregate readiness,
   and proves only portfolio-scoped Manage action-register source posture plus
   current source refs for source-owned mandate performance-health and mandate
   risk-health contexts. Core portfolio-state, data-mesh, Workbench,
   client-publication, supported-feature, rebalance, action, and order-execution
   proof remain pending.
10. Core portfolio-state runtime evidence is explicit in aggregate readiness,
   but it qualifies only when the closed request and source receipts reconcile.
   Core issue `#790` tracks missing producer snapshot identity and reconciliation
   metadata, so live qualification currently fails closed. Portfolio-scoped
   Manage proof, mandate performance-health, mandate
   risk-health, data-mesh, Workbench, client-publication, supported-feature,
   rebalance, action, and order-execution proof remain pending.
11. Core bond-maturity runtime evidence is explicit in aggregate readiness, but
    it qualifies only when the closed request, maturity-summary, and upstream
    holdings receipts reconcile. Core issue `#792` tracks missing producer
    reconciliation, tenant, and correlation metadata, so real qualification
    currently fails closed. Data-mesh, Workbench, client-publication,
    deployment, production, and supported-feature proof remain pending.
12. AI lineage store proof is now explicit in aggregate readiness evidence, but
   `lotus-ai` workflow-pack registration, actual deterministic runtime
   execution, live-provider execution, runtime trust telemetry, Workbench proof,
   and supported-feature promotion remain pending unless corresponding proof
   artifacts are present and valid. Repo-owned model-risk dashboard/alert source
   validation is now covered by the model-risk operations proof gate; runtime
   provisioning, evaluation, and delivery remain blocked.
13. Non-AI operator-workflows dashboard, alert-rule, runbook, and fixture source
    validation is covered by a v2 `source_contract` proof. It adds a traceable
    aggregate evidence reference but clears no blocker; dashboard provisioning
    and query execution, live rule loading/evaluation/delivery, deployment, and
    production certification remain separately blocked under issue `#412`.
14. AI workflow-pack registration proof is now explicit in aggregate readiness
   evidence, but it proves only the governed sibling registration,
   binding, queue policy, supportability, and test coverage for
   `idea_explanation.pack@v1`; runtime execution, provider calls, model-risk
   operations certification, runtime trust telemetry, Workbench proof, and
   supported-feature promotion remain pending unless separately proven.
15. AI workflow-pack runtime execution proof is now explicit in aggregate
    readiness evidence, but it proves only an observed deterministic runtime
    invocation with a source-safe receipt, guardrails, stub-provider routing,
    and restricted `lotus-idea` caller policy; live provider execution,
    provider rollout, model-risk operations certification, runtime trust
    telemetry, Workbench proof, and supported-feature promotion remain pending.
16. Opportunity archetype scenario readiness is now explicit in aggregate
    readiness, but it proves only governed taxonomy, bounded concentration
    source/policy foundation, bounded high-volatility / drawdown source/policy
    foundation, bounded missing suitability context source/policy foundation,
    bounded missing risk-profile source/policy foundation,
    bounded allocation-drift / mandate-review Manage caller-supplied API
    foundation, bounded low-income / liquidity-shortfall Core cashflow foundation,
    bounded bond-maturity / reinvestment policy, caller-supplied API, and
    fail-closed Core maturity-summary live-source contract,
    optional live Risk concentration/high-volatility/drawdown proof
    consumption, and visible scenario blockers. Upstream consumer approval for
    `lotus-risk:ConcentrationRiskReport:v1` is source-approved; full
    source-backed archetype replay is bounded to optional high-cash live Core,
    concentration live Risk, high-volatility live Risk, drawdown live Risk,
    low-income live Core cashflow, typed mandate/restriction source-product,
    mandate/restriction live Advise, missing-suitability Advise runtime, typed
    missing risk-profile source-product, and missing-risk-profile Advise
    runtime-execution artifacts. Typed mandate/restriction source-product proof clears
    only `opportunity_archetype_typed_restriction_source_product_missing`;
    receipt-bound mandate/restriction runtime evidence clears only the Advise restriction
    live-source blocker; closed v2 missing-suitability runtime evidence binds
    exact request, workflow, and deterministic candidate or no-opportunity
    receipts and clears only the Advise policy live-source blocker; typed missing risk-profile source-product
    proof clears only
    `opportunity_archetype_typed_advise_risk_profile_source_product_missing`;
    closed v2 missing-risk-profile runtime evidence binds exact request,
    workflow, and deterministic candidate or no-opportunity receipts and clears
    only the Advise risk-profile live-source blocker; low-income Core cashflow proof clears only
    `opportunity_archetype_live_core_cashflow_source_proof_missing`;
    full Workbench product proof, data-mesh certification, client-publication,
    and supported-feature promotion remain pending.

The new downstream realization readiness diagnostic narrows the proof gap from
"unknown" to "explicitly blocked with source-authority refs"; it does not close
the downstream proof gap. The downstream realization contract gate makes those
blockers durable and machine-readable; it also does not close the downstream
proof gap.
The source-ingestion run-once operator action narrows the source proof gap from
"worker exists only as a CLI" to "service-boundary execution exists when
durable storage and runtime configuration are present"; it does not close live
Core source certification or certified long-running scheduled runtime proof.
The live-proof artifact contract narrows the live Core gap from "no durable
proof shape" to "operator-captured bounded live source-ingestion proof can be
validated and wired into readiness"; it does not close certified scheduled
daemon runtime, platform mesh, Gateway/Workbench, downstream, or
supported-feature proof.
The aggregate block-reason diagnostics further narrow the operator-debugging
gap for blocked live attempts; they are not source certification and do not
change the supported-feature posture.
The scheduled-worker deploy-contract artifact narrows the scheduling proof gap
from "no deployable worker contract" to "bounded scheduler entrypoint, Compose
worker service, source-safe proof, and aggregate readiness consumption are
CI-enforced"; it does not close long-running scheduler operations, live Core
source certification, platform mesh certification, Gateway/Workbench,
downstream, or supported-feature proof.
The outbox-delivery readiness diagnostic, run-once operator action, and bounded
outbox broker, downstream consumer runtime, and platform mesh event publication
proof artifacts do the same for broker and declared-consumer posture; they do
not close the certified external publication, Gateway/Workbench, or downstream
delivery gaps.
The runtime trust telemetry snapshot endpoint narrows the trust-evidence proof
gap from "generated artifact only" to "API-certified diagnostic plus generated
artifact"; it does not close platform mesh certification, Gateway/Workbench
discovery, or supported-feature proof gaps.
The runtime telemetry v2 `test_execution` artifact proves only that a
source-safe deterministic fixture exercises the telemetry contract. It does
not narrow runtime readiness and preserves candidate-snapshot,
durable-repository, product-coverage, certified-runtime-telemetry,
data-mesh-runtime, platform mesh, active-product, Gateway/Workbench discovery,
and supported-feature gaps.
The source-ingestion v2 `runtime_execution` artifact narrows the high-cash
live-Core gap only when the actual application result contains durable
accepted/replayed records bound to the four governed current Core source
products. Self-asserted status/count fields, in-memory runs, mixed outcomes,
missing receipts, hash/scope drift, and stale aggregate provenance do not
qualify. The artifact does not narrow scheduled-worker, data-mesh,
Gateway/Workbench, production-certification, or supported-feature gaps.
The Workbench read-path v2 source-contract artifact records bounded queue/detail
declarations without narrowing the runtime-readiness gap. It does not prove
Gateway serving, Workbench consumption, entitlement enforcement, browser
behavior, a canonical demo journey, publication, or supported-feature posture;
`workbench_gateway_bff_consumption_proof_missing` remains.
The Gateway/Workbench contract proof artifact records that bounded read-only
queue/detail contracts are linked into source-ingestion and outbox evidence.
Because this is source-contract evidence rather than observed execution, it
does not close `gateway_workbench_proof_missing` or any full Workbench product, panel,
browser accessibility proof, canonical demo runtime proof, Gateway/Workbench
data-product discovery, client-publication, or supported-feature proof.
The default platform catalog source contract narrows the aggregate readiness gap
from "no platform source-manifest/catalog proof" to "catalog-visible proposed
products and consumer dependencies can be generated and consumed through the
canonical readiness command"; it does not close mesh certification, active
product, Gateway/Workbench discovery, SLO/access/evidence, or
supported-feature proof gaps.
The runtime proof-artifact loader narrows the operator-readiness gap from
"generator-only artifact consumption" to "HTTP and generated readiness share
the same configured proof evidence." It now includes source-ingestion live and
scheduled proof artifact refs plus default Advise and Manage route, Report
intake route and materialization source contracts, and platform
mesh onboarding refs as auditable evidence; the route source contracts clear
no blocker. It
does not certify storage, live scheduler operations, mesh, Workbench,
Report/Render/Archive materialization, or supported-feature readiness.
The Report intake and materialization source contracts narrow the declaration
gap by linking sibling-owned routes into readiness provenance. They do not
prove route serving, request execution, Report package creation, rendered
output, archive record, retention/legal-hold posture, client publication,
certification, or supported-feature promotion, and clear no blocker.
The Advise/Manage source contracts narrow the declaration gap by binding the
proposal and action intake contract/route/service sources to exact digests. They
do not prove route serving, authorization, tenant isolation, request acceptance,
downstream records, suitability, mandate, rebalance, execution, order,
client-publication, production support, or supported-feature promotion.
The AI model-risk operations contract refs narrow the model-risk proof index
gap from "contract exists outside aggregate readiness" to "contract and gate are
visible in the `ai-explanation` capability evidence." They do not certify a
dashboard, alert pack, `lotus-ai` runtime workflow, AI lineage store,
Workbench surface, or supported feature.
The AI workflow-pack registration source contract narrows the source-authority evidence gap from
"no durable `lotus-ai` registration evidence" to "`idea_explanation.pack@v1`
is registered, bound, queue-governed, supportability-visible, and test-backed
in `lotus-ai`." It clears no aggregate blocker and does not close runtime
registry observation, runtime workflow execution, provider
invocation, certified model-risk operations, Workbench proof, or supported
feature proof.
The AI workflow-pack runtime execution proof narrows the execution gap from
"no observed `lotus-ai` runtime evidence" to "an actual deterministic,
review-gated `idea_explanation.pack@v1` invocation produced a bounded,
digest-bound receipt with guardrails and caller policy enforced." It does not close
live provider execution, provider rollout, certified model-risk operations,
Workbench proof, or supported-feature proof.

The signed AI attestation v2 source contract narrows the declaration gap from
unbound file/token scans to exact producer and consumer source-authority records
with canonical collection digests. A full sibling checkout can validate both
sides; isolated CI validates an explicit Idea-consumer-only posture that remains
an invalid full proof. No aggregate readiness consumer is added because source
declarations clear no current blocker. Live provider/model execution,
model-risk approval, deployment, production certification, Workbench proof,
publication, and supported-feature promotion remain separate evidence gaps.

## Acceptance Gate

Issue #331 closes the readiness/gate reconciliation gap. Aggregate readiness
no longer counts `status=implemented` independently: it consumes the typed
promotion evaluation used by `make supported-features-gate`. API and generated
artifact projections use the same count, blockers, and promotion boolean.
Malformed, missing-evidence, stale, planned, and not-applicable fixtures fail
closed; one fully evidenced current fixture proves consistent promotion. The
current repository remains empty and unpromoted.

1. All proof gaps are fixed inside RFC-0002 or the supported claim is narrowed.
2. Evidence includes success, unsupported, degraded, denied, stale, duplicate,
   AI unavailable, and downstream failure paths.
3. GitHub checks and local gates are recorded with commit SHAs.

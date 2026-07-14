# Implementation Proof Readiness

| Field | Current Truth |
| --- | --- |
| Status | Certified internal operator diagnostic |
| Audience | Operators, implementation reviewers, demo leads, and release reviewers |
| Required role | `operator` |
| Required capability | `idea.implementation-proof.readiness.read` |
| Required query | Timezone-aware `evaluatedAtUtc` |
| Supportability | `not_certified` while blockers remain |
| Product claim | Bounded live source-ingestion, runtime trust telemetry, default Advise proposal route, Manage action route, Report intake route, Report materialization, outbox broker, outbox consumer, platform-mesh event, Gateway/Workbench source contracts, Gateway/Workbench discovery, mesh policy, platform catalog source contract, receipt-bound mainline AI lineage-store CI execution, AI workflow-pack registration/runtime execution proof artifacts, and opportunity archetype scenario readiness can be consumed; Risk concentration, high-volatility, Risk drawdown, Performance underperformance, missing-benchmark Performance readiness, Core benchmark assignment, Core portfolio-state, missing-benchmark Core, low-income Core cashflow, Manage mandate, typed Advise mandate/restriction source-product, Advise mandate/restriction live, Advise missing-suitability, typed Advise missing risk-profile source-product, and Advise missing risk-profile live proof artifacts clear only source-specific blockers; the platform-mesh event and Gateway/Workbench source-contract proofs add evidence references but clear no runtime blocker; no full live journey, live AI provider execution, suitability/rebalance/risk-profile/restriction-clearance/benchmark-assignment authority, platform mesh certification, external broker or platform-mesh event publication, downstream delivery, full Gateway/Workbench product proof, live archetype replay proof, client-ready publication, or supported-feature promotion |

`GET /api/v1/implementation-proof/readiness` is the internal operator
diagnostic for RFC-0002 implementation proof posture.

It aggregates current evidence and blockers across:

1. source-owned high-cash signal ingestion,
2. deterministic advisor review queue,
3. AI-assisted explanation governance,
4. data-mesh producer and consumer certification,
5. source-safe runtime trust telemetry preview, snapshot endpoint, and snapshot generation,
6. internal outbox delivery foundation and bounded run-once operator action,
7. Workbench product realization,
8. opportunity archetype scenario readiness,
9. downstream Advise, Manage, Report, Render, and Archive realization,
10. supported-feature promotion.

## What It Proves

The diagnostic proves that `lotus-idea` can produce a source-safe, aggregate
readiness view over the current RFC-0002 implementation foundations and known
proof blockers.

It returns:

1. the current aggregate proof posture,
2. source-ingestion readiness posture,
3. advisor queue readiness posture,
4. AI explanation readiness posture,
5. data-mesh readiness posture,
6. runtime trust telemetry preview, snapshot endpoint, generated snapshot, and
   candidate-snapshot proof posture,
7. outbox delivery readiness and run-once posture,
8. Workbench realization blockers,
9. opportunity archetype scenario blockers from the governed contract,
10. downstream realization blockers and internal submission route evidence,
11. supported-feature promotion blockers,
12. source-of-truth implementation paths.

## Supported-Feature Reconciliation

Supported-feature readiness is derived by
`app.application.supported_feature_promotion`, the same evaluator used by
`make supported-features-gate`. A status string alone cannot clear promotion
blockers. Missing, malformed, unresolved, future-dated, or stale registry
evidence remains source-safely blocked; valid current evidence is projected
consistently by the application snapshot, API response, and generated proof
artifact. `make supported-feature-promotion-contract-gate` prevents those
consumers from restoring independent counting or hard-coded output.

## What It Does Not Prove

The diagnostic is deliberately not full live journey proof. It does not:

1. call `lotus-core`,
2. certify source-ingestion as a supported live source product beyond a
   configured bounded proof artifact,
3. live-call `lotus-ai`, execute live provider/RAG workflows, or certify provider rollout,
4. certify data products through platform mesh certification,
5. prove Gateway or Workbench product behavior,
6. create downstream proposals, manage actions, reports, rendered output, or
   archive records,
7. authorize external publication of client-facing material,
8. promote any supported feature.

## Current Blockers

Current posture is `blocked` and `not_certified`.

That is expected. The endpoint exists so operators and implementation agents can
see the real proof gap before demo, data-mesh, Workbench, downstream, or
supported-feature promotion.

The response remains blocked until all of the following are implemented and
validated through the owning repositories and platform gates:

1. source-ingestion certification beyond the bounded live Core proof artifact,
2. certified long-running scheduled worker runtime proof beyond the current
   deploy-contract artifact,
3. platform mesh certification, active producer products, and Gateway/Workbench discovery,
4. certified downstream delivery evidence beyond the bounded consumer-runtime proof artifact,
5. certified external broker publication and production event-publication evidence beyond the bounded platform-mesh event source-contract artifact,
6. `lotus-ai` live-provider rollout and runtime trust certification,
7. Workbench panel and browser proof,
8. downstream Advise and Manage realization authority,
9. Report/Render/Archive client-publication authority,
10. supported-feature promotion evidence.

Downstream realization blockers are backed by
`contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`.
`make downstream-realization-contract-gate` validates that the planned
contract rows stay source-authority preserving and do not become false
route-existence, downstream-execution, or supported-feature claims.
The downstream realization capability now also cites the internal submission
routes for Advise/Manage conversion intents and Report evidence-pack requests,
plus the report-owned planned intake contract at
`lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`.
Default source-safe Advise proposal and Manage action route proofs can clear
only their corresponding bounded route blockers when merged sibling evidence
is present. Report intake and materialization source contracts add declaration
provenance but clear no blocker. Those refs do not clear runtime execution,
render/archive, suitability policy, rebalance/action, client-publication,
certification, or supported-feature blockers.

Source-ingestion live proof is captured by
`scripts/generate_source_ingestion_live_proof.py`. The source-ingestion
readiness endpoint may report the family-level live Core proof as valid from
the configured artifact, but aggregate implementation-proof readiness clears
`live_core_source_proof_missing` only when that family-valid artifact is also
aggregate-current: it must carry `aggregateProofProvenance`, match the
source-safe consumed proof ref, be no more than 24 hours old, not be
future-dated, be bound to the current Lotus Idea source revision, and declare
`sourceTreeDirty=false`. A current artifact referenced through
`LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF` clears only
`live_core_source_proof_missing`; it does not clear scheduled worker,
data-mesh, Gateway/Workbench, downstream, or supported-feature blockers.
The artifact carries source-safe aggregate `blockReasonCounts` so blocked
attempts can distinguish Core unavailable, entitlement denied, missing
cash-weight evidence, and Core-reported blocked cash-weight supportability
without exposing source payloads or reconstructing source-owned calculations.
When aggregate implementation-proof readiness consumes a family-valid and
aggregate-current live proof path, the `source-ingestion` capability also
records a source-safe artifact reference in `evidenceRefs`, so release
reviewers can trace why that blocker cleared without exposing Core payloads or
portfolio identity. Missing, stale, future-dated, wrong-ref, or
wrong-source-revision provenance, or provenance generated from a dirty source
tree, leaves the source-ingestion and high-cash opportunity-archetype live Core
blockers in place and does not add the artifact ref as evidence.
Canonical Core runtimes should pass explicit `--core-query-base-url` and
`--core-query-control-plane-base-url` values because query-service reads and
query-control-plane snapshots can be served by different Core processes.
`--core-base-url` remains a compatibility fallback for older single-base
stacks.
The repo-native `make implementation-proof-readiness-check` target accepts the
same live-evidence inputs through Make variables, so release reviewers can use
the canonical target instead of a one-off command:

## Aggregate Proof Provenance

Aggregate readiness consumes optional JSON proof artifacts only after both the
family proof contract and the aggregate provenance check pass. The CLI and
runtime artifact loader attach `aggregateProofProvenance` with the source-safe
proof ref, artifact SHA-256, current source revision, source-tree dirty flag,
and proof generation timestamp before any optional proof can clear a blocker.

Blockers remain in place when the provenance envelope is missing, the proof ref
does not match the consumed artifact, `generatedAtUtc` is future-dated or older
than the 24-hour freshness window, the source revision does not match the
current Lotus Idea source revision, or `sourceTreeDirty` is missing or not
`false`. Dirty-tree proof artifacts may be useful as diagnostic evidence, but
they cannot clear release/readiness blockers or add their artifact ref to
capability evidence. Runtimes without a local `.git` checkout must set
`LOTUS_IDEA_SOURCE_REVISION` to the deployed commit or deterministic source
identifier when they expect optional proof artifacts to clear aggregate
readiness blockers. This provenance binding is internal implementation
evidence; it is not data-mesh certification, client-publication approval, or
supported-feature promotion.

## Evidence-Class Boundary

Proof authority is classified as source contract, local test execution, CI
execution, runtime execution, deployment, or production certification. These
classes are exact, not cumulative. A proof can clear only a blocker that
requires the same class.

The AI lineage-store v2 proof requires mainline `ci_execution`. It binds the
Main Releasability PostgreSQL workflow/job, run and attempt, exact commit and
main ref, successful conclusion, completion timestamp, GitHub artifact digest,
and the named lineage persistence assertions. Repository files and Make target
presence remain design evidence and cannot clear
`certified_ai_lineage_store_missing` alone. See
`docs/architecture/implementation-proof-evidence-classification.md` for the
taxonomy and the #393 same-pattern campaign.

| Variable | Effect |
| --- | --- |
| `IMPLEMENTATION_PROOF_EVALUATED_AT_UTC` | Overrides the deterministic proof timestamp. |
| `IMPLEMENTATION_PROOF_OUTPUT` | Writes the aggregate readiness JSON to a chosen ignored output path. |
| `LOTUS_CORE_QUERY_BASE_URL` | Passes the live Core query-service URL into readiness generation. |
| `LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL` | Passes the live Core query-control-plane URL into readiness generation. |
| `LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF` | Passes the live source-ingestion proof artifact into aggregate readiness. The family proof must be valid and aggregate-current before it can clear source-ingestion or high-cash opportunity-archetype live Core blockers. |
| `LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF` | Passes a validated source-safe Lotus Risk concentration live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_live_risk_source_proof_missing`; it does not certify data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF` | Passes a validated source-safe Lotus Risk high-volatility live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_live_risk_volatility_source_proof_missing`; it does not certify drawdown, data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF` | Passes a validated source-safe Lotus Risk drawdown live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_drawdown_source_proof_missing`; it does not certify volatility, data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF` | Passes a validated source-safe Lotus Performance underperformance live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_live_performance_source_proof_missing`; it does not certify benchmark assignment, data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF` | Passes a validated source-safe Lotus Performance benchmark-readiness proof artifact into missing-benchmark opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_performance_benchmark_readiness_source_ref_missing`; it does not assign benchmarks, calculate performance or benchmark returns, certify benchmark methodology, certify data mesh, prove Workbench behavior, approve client publication, or promote support. |
| `LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF` | Passes a validated source-safe Lotus Core benchmark assignment live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_benchmark_assignment_source_ref_missing`; it does not certify Performance source evidence, benchmark methodology, benchmark composition, benchmark return calculation, data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF` | Passes a validated source-safe Lotus Core portfolio-state live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_core_portfolio_state_source_ref_missing`; it does not certify Manage action-register proof, mandate performance health, mandate risk health, rebalance authority, action authority, order execution, data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF` | Passes a validated source-safe Lotus Core maturity-summary live-proof artifact into opportunity-archetype readiness. The live adapter consumes Core-owned `PortfolioMaturitySummary:v1` and fails closed when explicit maturity facts or upstream holdings lineage are missing. A valid artifact clears only `opportunity_archetype_maturity_live_core_source_proof_missing`; it does not recommend reinvestment products, forecast cashflows, certify suitability or risk, certify data mesh, prove Workbench behavior, approve client publication, or promote support. |
| `LOTUS_IDEA_MISSING_BENCHMARK_LIVE_PROOF` | Passes a validated source-safe Lotus Core missing-benchmark live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_missing_benchmark_live_core_source_proof_missing`; it does not assign benchmarks, certify Performance benchmark-readiness evidence, certify benchmark methodology, calculate benchmark composition or returns, certify data mesh, prove Workbench behavior, approve client publication, or promote support. |
| `LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF` | Passes a validated source-safe Lotus Core cashflow live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_live_core_cashflow_source_proof_missing`; it does not certify client income needs, funding advice, treasury instruction, suitability, planning objectives, data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF` | Passes a validated source-safe Lotus Manage mandate live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_portfolio_scoped_manage_source_proof_missing`, `opportunity_archetype_mandate_performance_health_source_ref_missing`, and `opportunity_archetype_mandate_risk_health_source_ref_missing`; it does not certify Core portfolio state, data mesh, Workbench, client publication, supported-feature promotion, rebalance authority, action authority, order creation, execution, or settlement. |
| `LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF` | Passes a validated source-safe Lotus Advise mandate/restriction live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_live_restriction_source_proof_missing`; it does not certify a typed restriction source product, clear restrictions, change mandate state, approve suitability or policy, certify data mesh, prove Workbench behavior, approve client publication, create rebalance/order authority, or promote support. |
| `LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF` | Passes a validated source-safe typed Lotus Advise mandate/restriction source-product proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_typed_restriction_source_product_missing`; it does not certify live Advise reachability, clear restrictions, change mandate state, approve suitability, approve policy, approve proposals, certify data mesh, prove Workbench behavior, approve client publication, create rebalance/order authority, or promote support. |
| `LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF` | Passes a validated source-safe Lotus Advise policy-evaluation live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_advise_policy_live_source_proof_missing`; it does not certify suitability, policy approval, proposal approval, data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF` | Passes a validated source-safe typed Lotus Advise risk-profile source-product proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_typed_advise_risk_profile_source_product_missing`; it does not certify live Advise reachability, approve risk profiling, approve suitability or policy, certify data mesh, prove Workbench behavior, approve client publication, or promote support. |
| `LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF` | Passes a validated source-safe Lotus Advise risk-profile diagnostic live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_advise_risk_profile_live_source_proof_missing`; it does not certify a typed risk-profile source product, risk-profile approval, suitability, policy approval, proposal approval, data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_ADVISE_ROOT` | Selects the sibling `lotus-advise` checkout used to generate the default source-safe Advise proposal route proof. Defaults to `../lotus-advise`. |
| `LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT` | Selects the default generated Advise proposal route proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/downstream/advise-proposal-route-proof.json`. |
| `LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF` | Overrides the default generated Advise proposal route proof artifact passed into aggregate readiness. |
| `LOTUS_MANAGE_ROOT` | Selects the sibling `lotus-manage` checkout used to generate the default source-safe Manage action route proof. Defaults to `../lotus-manage`. |
| `LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT` | Selects the default generated Manage action route proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/downstream/manage-action-route-proof.json`. |
| `LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF` | Overrides the default generated Manage action route proof artifact passed into aggregate readiness. |
| `LOTUS_REPORT_ROOT` | Selects the sibling `lotus-report` checkout used to generate the default source-safe report-intake route proof. Defaults to `../lotus-report`. |
| `LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default generated report-intake route proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/report/intake-route-source-contract-proof.json`. |
| `LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF` | Overrides the default generated report-intake route proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default generated report materialization source-contract artifact consumed by aggregate readiness when no override is set. Defaults to `output/report/materialization-source-contract-proof.json`. |
| `LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF` | Overrides the default report materialization source-contract artifact passed into aggregate readiness. |
| `LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default generated mesh policy source-contract artifact consumed by aggregate readiness when no override is set. Defaults to `output/data-mesh/mesh-policy-source-contract.json`. |
| `LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF` | Overrides the default generated mesh policy source-contract artifact passed into aggregate readiness. |
| `LOTUS_PLATFORM_ROOT` | Selects the sibling `lotus-platform` checkout used to generate the default source-safe platform catalog source contract. Defaults to `../lotus-platform`. |
| `LOTUS_IDEA_PLATFORM_CATALOG_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default generated platform catalog source contract artifact consumed by aggregate readiness when no override is set. Defaults to `output/data-mesh/platform-catalog-source-contract.json`. |
| `LOTUS_IDEA_PLATFORM_CATALOG_SOURCE_CONTRACT_PROOF` | Overrides the default generated platform catalog source contract artifact passed into aggregate readiness. |
| `LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF_OUTPUT` | Selects the default generated outbox consumer source-contract proof consumed by aggregate readiness when no override is set. Defaults to `output/outbox/outbox-consumer-contract-proof.json`. |
| `LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF` | Overrides the default generated outbox consumer source-contract proof passed into aggregate readiness. |
| `LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default generated outbox platform-mesh event source-contract proof consumed by aggregate readiness when no override is set. Defaults to `output/outbox/platform-mesh/event-source-contract-proof.json`. |
| `LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF` | Overrides the default generated outbox platform-mesh event source-contract proof passed into aggregate readiness. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT` | Selects the default generated Gateway/Workbench contract proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/workbench/gateway-workbench-contract-proof.json`. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF` | Overrides the default generated Gateway/Workbench contract proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_OUTPUT` | Selects the default generated Gateway/Workbench discovery contract proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/workbench/gateway-workbench-discovery-contract-proof.json`. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF` | Overrides the default generated Gateway/Workbench discovery contract proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT` | Selects the default generated AI lineage store proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/ai/ai-lineage-store-proof.json`. |
| `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF` | Overrides the default generated AI lineage store proof artifact passed into aggregate readiness. |
| `LOTUS_AI_ROOT` | Selects the sibling `lotus-ai` checkout used to generate the workflow-pack registration source-contract proof. Defaults to `../lotus-ai`. |
| `LOTUS_AI_BASE_URL` | Selects the governed Lotus AI runtime used for actual workflow-pack execution proof. Defaults to `http://127.0.0.1:8140`. |
| `LOTUS_IDEA_AI_RUNTIME_PROOF_TIMEOUT_SECONDS` | Bounds the runtime-proof HTTP call. Defaults to `2`; accepted values are greater than zero and at most `30`. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT` | Selects the default generated AI workflow-pack registration source-contract artifact consumed by aggregate readiness when no override is set. Defaults to `output/ai/ai-workflow-pack-registration-source-contract-proof.json`. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF` | Overrides the default generated AI workflow-pack registration source-contract artifact passed into aggregate readiness. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT` | Selects the default generated AI workflow-pack runtime execution proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/ai/ai-workflow-pack-runtime-execution-proof.json`. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF` | Overrides the default generated AI workflow-pack runtime execution proof artifact passed into aggregate readiness. |

When rerunning live proof against an existing durable PostgreSQL repository,
preserve idempotency history. If the same generated default idempotency key was
accepted before an upstream Core source fingerprint changed, a later run can
correctly return `conflict`. Capture a fresh release-proof run with an ignored
manifest under `output/source-ingestion/` and a source-safe explicit
`idempotencyKey`; do not reset durable state to force an accepted outcome. The
checked-in example manifest remains the canonical source-safe default, while
ignored proof-run manifests are local evidence inputs only.

Valid source-ingestion live Core proof also clears only
`opportunity_archetype_live_core_source_proof_missing` for the governed
high-cash / idle-liquidity scenario inside `opportunity-archetype-scenarios`.
It remains source-safe proof over the internal high-cash ingestion run and does
not certify Workbench behavior, data mesh, client publication, or
supported-feature promotion.

Scheduled source-ingestion worker deploy proof is captured by
`scripts/generate_scheduled_source_ingestion_worker_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_PROOF` clears
only `scheduled_worker_deploy_proof_missing`; it does not clear live Core,
data-mesh, Gateway/Workbench, downstream, or supported-feature blockers.
`make implementation-proof-readiness-check` now generates that deploy-proof
artifact under ignored `output/source-ingestion/` and passes it explicitly into
the aggregate readiness generator, so the repo-native proof snapshot does not
report a stale scheduled-worker deploy-proof blocker. Aggregate
implementation-proof readiness records the validated artifact reference in the
`source-ingestion` capability `evidenceRefs`, making the blocker-clearance
evidence auditable without leaking source payloads. This remains deploy
topology proof only; it is not live long-running scheduler certification.

Lotus Risk concentration live proof is captured by
`scripts/generate_risk_concentration_live_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF` clears only
`opportunity_archetype_live_risk_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-risk:ConcentrationRiskReport:v1` source call, current source evidence,
and deterministic concentration candidate generation without storing portfolio
identity, request or response payloads, correlation IDs, trace IDs, candidate
IDs, or source routes. It deliberately retains data-mesh, Workbench,
client-publication, and supported-feature blockers.

Lotus Risk high-volatility live proof is captured by
`scripts/generate_high_volatility_live_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF` clears only
`opportunity_archetype_live_risk_volatility_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-risk:RiskMetricsReport:v1` source call, current source evidence,
ready Risk supportability, and deterministic high-volatility candidate
generation without storing portfolio identity, request or response payloads,
correlation IDs, trace IDs, candidate IDs, source routes, volatility values, or
drawdown figures. It deliberately retains drawdown, data-mesh, Workbench,
client-publication, and supported-feature blockers.

Lotus Risk drawdown live proof is captured by
`scripts/generate_risk_drawdown_live_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF` clears only
`opportunity_archetype_drawdown_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-risk:DrawdownAnalyticsReport:v1` source call, current source evidence,
ready Risk supportability, and deterministic drawdown-review candidate
generation without storing portfolio identity, request or response payloads,
correlation IDs, trace IDs, candidate IDs, source routes, max-drawdown values,
or drawdown episodes. It deliberately retains volatility, data-mesh,
Workbench, client-publication, and supported-feature blockers.

Lotus Performance underperformance live proof is captured by
`scripts/generate_performance_underperformance_live_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF` clears
only `opportunity_archetype_live_performance_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-performance:ReturnsSeriesBundle:v1` source call, current source
evidence, benchmark context availability, and deterministic underperformance
candidate generation without storing portfolio identity, request or response
payloads, correlation IDs, trace IDs, candidate IDs, source routes, returns, or
benchmark values. It deliberately retains benchmark-assignment, data-mesh,
Workbench, client-publication, and supported-feature blockers.

Lotus Core benchmark assignment live proof is captured by
`scripts/generate_core_benchmark_assignment_live_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF` clears only
`opportunity_archetype_benchmark_assignment_source_ref_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-core:BenchmarkAssignment:v1` source call, current source evidence,
effective assignment posture, benchmark identity resolution, and assignment
version presence without storing portfolio identity, benchmark identity, request
or response payloads, correlation IDs, trace IDs, candidate IDs, or source
routes. It deliberately retains live Performance, data-mesh, Workbench,
client-publication, and supported-feature blockers, and it does not assign
benchmarks, calculate benchmark returns, or certify benchmark methodology.

Lotus Core portfolio-state live proof is captured by
`scripts/generate_core_portfolio_state_live_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF` clears only
`opportunity_archetype_core_portfolio_state_source_ref_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-core:PortfolioStateSnapshot:v1` source call and current source evidence
without storing portfolio identity, request or response payloads, correlation
IDs, trace IDs, candidate IDs, source routes, holdings, positions, allocation
weights, or portfolio totals. It deliberately retains portfolio-scoped Manage,
mandate performance-health, mandate risk-health, data-mesh, Workbench,
client-publication, supported-feature, rebalance, action, order-creation,
execution, and settlement blockers unless a separate valid Manage mandate
live-proof artifact supplies the Manage action-register and mandate-health
source refs.

Lotus Core low-income cashflow live proof is captured by
`scripts/generate_low_income_core_cashflow_live_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF` clears only
`opportunity_archetype_live_core_cashflow_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves live
`lotus-core:PortfolioCashflowProjection:v1` and
`lotus-core:PortfolioCashMovementSummary:v1` source calls, current source
evidence, cash-movement evidence presence, projected cumulative cashflow
evidence presence, and deterministic low-income / liquidity-shortfall
candidate posture without storing portfolio identity, request or response
payloads, correlation IDs, trace IDs, candidate IDs, source routes, cashflow
amounts, movement details, or client facts. It deliberately retains Workbench,
data-mesh, client-publication, supported-feature, suitability, planning,
funding-advice, and treasury-instruction blockers.

Lotus Core bond-maturity live proof is captured by
`scripts/generate_bond_maturity_live_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF` clears only
`opportunity_archetype_maturity_live_core_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The live adapter consumes
Core-owned `PortfolioMaturitySummary:v1`, requires upstream `HoldingsAsOf:v1`
lineage, and fails closed instead of deriving maturity dates or counts from raw
positions. The artifact proves live Core maturity-summary evidence, current
source refs, next maturity-date evidence, and maturing-position count presence
without storing portfolio identity, request or response payloads, correlation
IDs, trace IDs, candidate IDs, source routes, positions, holdings, security
identifiers, maturity dates, or quantities. It deliberately retains data-mesh,
Workbench, client-publication, product-recommendation, reinvestment-advice,
suitability, risk, and supported-feature blockers.

Lotus Manage mandate live proof is captured by
`scripts/generate_manage_mandate_live_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF` clears only
`opportunity_archetype_portfolio_scoped_manage_source_proof_missing`,
`opportunity_archetype_mandate_performance_health_source_ref_missing`, and
`opportunity_archetype_mandate_risk_health_source_ref_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-manage:PortfolioActionRegister:v1` source call, current source
evidence, workflow decision count, lineage edge count, portfolio-scope
confirmation, ready Manage action-register posture, Manage-provided
lineage/fingerprint metadata for `SourceRef.content_hash`, and current source
refs for `lotus-performance:MandatePerformanceHealthContext:v1` and
`lotus-risk:MandateRiskHealthContext:v1` without storing
portfolio identity, request or response payloads, correlation IDs, trace IDs,
candidate IDs, source routes, action identifiers, rebalance payloads, or order
details. It deliberately retains Core portfolio-state, data-mesh, Workbench,
client-publication, supported-feature, rebalance, action, order-creation,
execution, and settlement blockers.

Lotus Advise mandate/restriction live proof is captured by
`scripts/generate_mandate_restriction_live_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF` clears only
`opportunity_archetype_live_restriction_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1` workflow source call, current
source evidence, explicit source-owned restriction diagnostic posture, and
deterministic compliance-review candidate generation without storing evaluation
identity, request or response payloads, correlation IDs, trace IDs, candidate
IDs, source routes, requirement details, restriction details, or sign-off
details. It deliberately retains typed restriction source-product, mandate
state-change, restriction-clearance, suitability, policy, proposal, rebalance,
order, client-publication, data-mesh, Workbench, and supported-feature
blockers. Generic Advise policy diagnostics do not validate this proof; the
source diagnostic must explicitly identify a mandate/restriction review
condition.

Lotus Advise mandate/restriction source-product proof is captured by
`scripts/generate_mandate_restriction_source_product_proof.py`. A valid
artifact referenced through
`LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF` clears only
`opportunity_archetype_typed_restriction_source_product_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves that
`lotus-idea` consumes the typed
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1` source-product contract and
Advise-owned restriction diagnostic vocabulary for mandate, product
restriction, country restriction, and suitability-policy actionability posture.
It deliberately retains live Advise source proof, restriction clearance,
mandate-state authority, suitability, policy, proposal, client-publication,
data-mesh, Workbench, and supported-feature blockers.

Lotus Advise missing-suitability live proof is captured by
`scripts/generate_missing_suitability_live_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF` clears only
`opportunity_archetype_advise_policy_live_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1` workflow source call, current
source evidence, blocked client-publication posture, and deterministic
compliance-review candidate generation without storing evaluation identity,
request or response payloads, correlation IDs, trace IDs, candidate IDs,
source routes, requirement details, or sign-off details. It deliberately
retains suitability, policy, proposal, client-publication, data-mesh,
Workbench, and supported-feature blockers.

Lotus Advise missing risk-profile source-product proof is captured by
`scripts/generate_missing_risk_profile_source_product_proof.py`. A valid
artifact referenced through
`LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF` clears only
`opportunity_archetype_typed_advise_risk_profile_source_product_missing` for
the `opportunity-archetype-scenarios` capability. The artifact proves that
`lotus-idea` consumes the typed
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1` source-product contract and
Advise-owned risk-profile diagnostic vocabulary for missing, stale, expired,
and review-due risk-profile posture. It deliberately retains live Advise source
proof, risk-profile approval, suitability, policy, proposal,
client-publication, data-mesh, Workbench, and supported-feature blockers.

Lotus Advise missing risk-profile live proof is captured by
`scripts/generate_missing_risk_profile_live_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF` clears only
`opportunity_archetype_advise_risk_profile_live_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1` workflow source call, current
source evidence, explicit risk-profile diagnostic posture, and deterministic
advisor-review candidate generation without storing evaluation identity,
request or response payloads, correlation IDs, trace IDs, candidate IDs,
source routes, requirement details, or sign-off details. It deliberately
retains typed risk-profile source-product, risk-profile authority,
suitability, policy, proposal, client-publication, data-mesh, Workbench, and
supported-feature blockers.

Durable repository proof is captured by
`scripts/persistence/generate_durable_repository_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_DURABLE_REPOSITORY_PROOF` or passed with
`--durable-repository-proof` clears only these aggregate blockers inside
generated implementation-proof readiness evidence and the operator API
readiness snapshot:

1. `durable_repository_not_configured`,
2. `repository_side_queue_pagination_not_certified`.

Both blockers require CI-execution evidence, not a source-file inventory or CI
job name. Main Releasability derives a receipt from the governed PostgreSQL
JUnit report and binds it to the exact repository, workflow/job, run id and
attempt, commit SHA and main ref, successful conclusion, and uploaded artifact
digest. The receipt must include observed migration rollback/reapply,
candidate persistence/reload and replay, concurrent identity/audit/outbox, and
repository-side queue-pagination assertions. The proof does not configure the
running service, certify production storage or deployment migrations, certify
live Core ingestion or runtime trust telemetry, prove Gateway/Workbench
behavior, or promote a supported feature. Runtime readiness endpoints continue
to report missing durable repository posture when `LOTUS_IDEA_DATABASE_URL` is
absent.

Runtime trust telemetry proof is captured by
`scripts/generate_runtime_trust_telemetry_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_RUNTIME_TRUST_TELEMETRY_PROOF` or passed with
`--runtime-trust-telemetry-proof` currently clears only the seeded
candidate-snapshot runtime blocker inside generated implementation-proof
readiness evidence and the operator API readiness snapshot:

1. `runtime_candidate_snapshot_missing`.

It exercises a deterministic, source-safe candidate snapshot through the
runtime trust telemetry builder and records the proof artifact as aggregate
evidence. The artifact also records product-coverage posture from the runtime
telemetry preview, and while any declared producer product remains incomplete
it preserves `runtime_trust_telemetry_product_coverage_incomplete`,
`certified_runtime_trust_telemetry_missing`, and
`data_mesh_runtime_telemetry_not_certified`. It does not certify the platform
source manifest, platform mesh, active producer products, SLO/access/evidence
policy, Gateway or Workbench discovery, client-ready publication, or
supported-feature promotion.

Workbench read-path source-contract proof is captured by
`scripts/workbench/generate_read_path_source_contract.py`. A valid v2 artifact
referenced through `LOTUS_IDEA_WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF` or
passed with `--workbench-read-path-source-contract-proof` records bounded
queue/detail route declarations as `source_contract` evidence. It clears no
blocker, so `workbench_gateway_bff_consumption_proof_missing` remains in
generated and operator API readiness until machine-verifiable evidence proves
Gateway serving, Workbench consumption, and entitlement enforcement. It also
does not certify a panel, browser accessibility, canonical demo runtime,
data-product publication, client-ready publication, or supported-feature
promotion.

Gateway/Workbench contract proof is captured by
`scripts/workbench/generate_contract_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT` from the
validated Workbench read-path source contract and passes it into aggregate readiness when
`LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF` is not set. A valid artifact is
classified as `source_contract`: aggregate readiness may record its evidence
reference, but it clears no blocker. In particular,
`gateway_workbench_proof_missing` remains on the source-ingestion and
outbox-delivery proof families until machine-verifiable runtime execution
evidence exists. The artifact does not clear full Workbench product proof,
Workbench panel proof, browser accessibility proof, canonical demo runtime
proof, Gateway/Workbench data-product discovery proof, client-ready
publication, or supported-feature promotion.

Gateway/Workbench discovery contract proof is captured by
`scripts/workbench/generate_discovery_contract_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_OUTPUT` from
platform catalog/onboarding evidence, the Workbench read-path source contract, and the
Gateway/Workbench contract proof. A valid v2 artifact is classified as
`source_contract`: aggregate readiness may add its evidence reference to the
data-mesh and runtime-trust telemetry capabilities, but it clears no blocker.
`gateway_workbench_discovery_proof_missing` remains until machine-verifiable
runtime evidence proves active catalog publication, Gateway serving,
Workbench consumption, and entitlement enforcement. The artifact does not
certify data-mesh products, activate producer products, publish product routes,
certify canonical Workbench behavior, or promote supported features.

Outbox broker source-contract proof is captured by
`scripts/outbox/broker/generate_source_contract_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_OUTBOX_BROKER_SOURCE_CONTRACT_PROOF` or passed
with `--outbox-broker-source-contract-proof` adds a traceable evidence reference
to outbox-delivery and operator-workflow readiness. It clears no blocker.
`outbox_broker_not_configured` and `external_broker_runtime_proof_missing`
remain until separately governed runtime evidence proves external broker
configuration and publication. The artifact validates the publisher port, HTTP
adapter source contract, operator API surface, event contracts, and
`make outbox-broker-source-contract-proof-gate`; it does not certify runtime
execution, deployment, external publication, downstream consumption, platform
mesh publication, Gateway/Workbench behavior, or supported-feature promotion.

Downstream outbox consumer contract posture is enforced by
`contracts/outbox-events/lotus-idea-outbox-consumers.v1.json` and
`make outbox-consumer-contract-gate`. The contract declares Gateway, Advise,
Manage, and Report consumers with source-authority boundaries and keeps each
consumer `contract_declared_not_runtime_certified`; it changes the outbox
blocker from `downstream_consumer_contracts_missing` to
`downstream_consumer_runtime_proof_missing` without promoting support.

Outbox consumer source-contract proof is captured by
`scripts/outbox/generate_consumer_contract_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF_OUTPUT` and passes it
into aggregate readiness when `LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF` is not
set. A valid v2 artifact is `source_contract` evidence. It proves declared
Gateway, Advise, Manage, and Report consumer coverage, consumed event types,
and authority boundaries, while explicitly retaining
`downstream_consumer_runtime_proof_missing`. It does not certify external
broker publication, consumer execution, platform mesh event publication,
Gateway/Workbench behavior, downstream delivery, client-ready publication, or
supported-feature promotion.

Outbox platform-mesh event source-contract proof is captured by
`scripts/outbox/platform_mesh/generate_source_contract_proof.py`. The
repo-native `make implementation-proof-readiness-check` target now generates
the default artifact from repo-owned outbox event/consumer contracts and
sibling `lotus-platform` source-manifest/catalog evidence under
`LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_OUTPUT`, then passes
it into aggregate readiness when
`LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF` is not set. A valid
artifact is `source_contract` evidence. It records the source-safe event
contract, declared consumer coverage, platform source-manifest inclusion, and
generated catalog mapping for proposed `lotus-idea` products. It adds a
provenance reference but clears no aggregate blocker;
`platform_mesh_event_publication_proof_missing` remains until runtime
publication evidence exists. The artifact does not establish runtime execution, a publication receipt, external broker publication, downstream delivery, deployment, production certification, Gateway/Workbench behavior, client-ready publication, or supported-feature promotion. Missing sibling evidence writes an invalid non-proof artifact; drift in present sibling evidence still exits non-zero.

Advise proposal route proof and Manage action route proof are captured by
`scripts/generate_advise_proposal_route_proof.py` and
`scripts/generate_manage_action_route_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates default
artifacts from `LOTUS_ADVISE_ROOT` and `LOTUS_MANAGE_ROOT` under
`LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT` and
`LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT`, then passes them into aggregate
readiness when the corresponding override variables are not set. Valid
artifacts clear only `advise_live_contract_proof_missing` or
`manage_live_contract_proof_missing` inside downstream realization and
aggregate implementation-proof readiness. Missing sibling evidence writes
invalid non-proof artifacts and keeps the blockers so CI remains stable without
treating absence as proof. Drift in present sibling evidence exits non-zero.
These proofs cite the sibling route contract, sibling route/service evidence,
the `lotus-idea` downstream contract, and readiness endpoints. They do not
grant suitability, policy approval, mandate/rebalance authority, execution,
order creation, client communication, or supported-feature promotion.

Report intake route source-contract evidence is captured by
`scripts/report/generate_intake_route_source_contract.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_REPORT_ROOT` under
`LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT` and passes it into aggregate
readiness when `LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF` is not set. A valid
artifact is `source_contract` evidence: it adds the sibling declaration's
provenance but clears no blocker. In particular,
`lotus_report_live_intake_route_proof_missing` remains until governed runtime
evidence observes the owning Report route serving and accepting the handoff.
Missing sibling evidence writes an invalid non-proof artifact. It cites the merged
`lotus-report` route contract for `POST /reports/idea-evidence-packs`, the
report-owned intake route modules and tests, the `lotus-idea` downstream
contract, and the readiness endpoints. It does not create a report job, render
output, archive record, client publication, suitability decision, mandate
action, execution instruction, or supported feature.

Report materialization source-contract evidence is captured by
`scripts/report/generate_materialization_source_contract.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_REPORT_ROOT` under
`LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT` and passes it
into aggregate readiness when
`LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF` is not set. A valid
artifact clears no blocker. It can add a source-safe evidence reference while
preserving runtime materialization, rendered-output, archive-record,
client-publication, certification, and supported-feature blockers. Missing
sibling evidence writes an invalid source-contract artifact and keeps those
blockers. It cites the
merged `lotus-report` materialization contract for
`POST /reports/idea-evidence-packs/materializations`, report-owned
materialization/render/archive modules and tests, the `lotus-idea` downstream
contract, and the readiness endpoints. Sibling declarations do not prove that
a job ran, output was rendered, an archive record was created, or a retention
or legal-hold policy was applied. The artifact also does not grant
client-publication authority, suitability authority, mandate action, execution
instruction, production certification, or a supported feature.

The platform catalog source contract is generated by
`scripts/data_mesh/generate_platform_catalog_source_contract.py`. The
repo-native `make implementation-proof-readiness-check` target reads the
sibling checkout selected by `LOTUS_PLATFORM_ROOT`, writes the default artifact
to `LOTUS_IDEA_PLATFORM_CATALOG_SOURCE_CONTRACT_PROOF_OUTPUT`, and consumes it
unless `LOTUS_IDEA_PLATFORM_CATALOG_SOURCE_CONTRACT_PROOF` provides an explicit
artifact.

The v2 artifact declares `evidenceClass=source_contract` and binds the exact
platform source manifest, generated catalog, dependency graph, and maturity
matrix with repository, ref, and SHA-256 metadata. Its closed-field validator
rejects unknown claims and requires runtime publication, mesh certification,
producer activation, discovery certification, production certification,
supported-feature promotion, and closure fields to remain false. A valid,
current aggregate artifact can therefore satisfy only:

1. `platform_source_manifest_inclusion_missing`,
2. `platform_catalog_inclusion_missing`.

It does not certify SLO/access/evidence policy, platform runtime publication,
Gateway/Workbench discovery, deployment, production readiness, or product
support. Missing sibling evidence writes an invalid non-proof artifact and
keeps both blockers; drift in present sibling evidence remains a failing
contract condition.

Mesh policy source-contract evidence is captured by
`scripts/data_mesh/generate_mesh_policy_source_contract.py`. The repo-native
`make implementation-proof-readiness-check` target generates the default
artifact under `LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF_OUTPUT` and passes
it into aggregate readiness when
`LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF` is not set. A valid current
artifact adds a supporting evidence reference and clears no blocker. The
following policy-certification blockers remain:

1. `mesh_slo_policy_certification_missing`,
2. `mesh_access_policy_certification_missing`,
3. `mesh_evidence_policy_certification_missing`.

It digest-binds the mesh readiness, SLO, access, and evidence-pack policy
sources and cites the repo-native gates. It does not certify policy execution,
the platform mesh, producer activation, platform source-manifest/catalog
inclusion, Gateway/Workbench discovery, deployment, production readiness,
client publication, or supported-feature promotion.
`make mesh-policy-source-contract-proof-gate` validates the closed artifact
shape, authority digests, source-safe evidence refs, and zero-blocker-clearance
boundary before consumption.

AI lineage store proof is captured by
`scripts/generate_ai_lineage_store_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT` and passes it into
aggregate readiness when `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF` is not set. A
valid artifact clears only `certified_ai_lineage_store_missing` from the
AI explanation capability. It cites the AI explanation lineage migration,
rollback, governance code, persistence port, PostgreSQL adapter, PostgreSQL
runtime proof tests, and the required GitHub PostgreSQL runtime proof lane.
It does not execute `lotus-ai`, call an AI provider, expose prompts or provider
responses, prove Workbench behavior, authorize client-ready publication, or
promote a supported feature.
`make ai-lineage-store-proof-contract-gate` validates the artifact shape and
blocks source-sensitive content before the proof is consumed by aggregate
readiness.

### AI Workflow-Pack Registration Source Contract

The source-contract artifact is generated by
`scripts/ai_workflow_pack_registration/generate_source_contract_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_AI_ROOT` under
`LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT` and passes it into
aggregate readiness when `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF` is
not set.

| Evidence property | Current truth |
| --- | --- |
| Evidence class | `source_contract` |
| Source authority | `lotus-ai` |
| Blockers cleared | None |
| Runtime blocker retained | `workflow_pack_runtime_contract_not_certified` |
| Runtime/deployment observed | No |
| Product promotion | No |

The artifact cites the sibling `lotus-ai` workflow-pack phase-one spec,
registry seed, execution binding, queue policy catalog, supportability surface,
and registry/API/runtime tests for `idea_explanation.pack@v1`.
It adds a source-safe evidence reference without changing aggregate blockers.
It does not execute `lotus-ai`, observe a running registry, call an AI provider, certify runtime trust
telemetry, prove Workbench behavior, authorize client-ready publication, or
promote a supported feature.
Missing sibling evidence writes an invalid non-proof artifact and keeps the
blocker so CI remains stable without treating absence as proof; drift in
present sibling evidence still exits non-zero.
`make ai-workflow-pack-registration-proof-contract-gate` validates the artifact
shape, `source_contract` classification, empty blocker-clearance set,
source-safe evidence refs, and explicit non-execution/non-deployment posture
before aggregate readiness consumes it.

AI workflow-pack runtime execution proof is captured by
`scripts/generate_ai_workflow_pack_runtime_execution_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact by invoking `LOTUS_AI_BASE_URL` under
`LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT` and passes it into
aggregate readiness when `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF`
is not set. A valid artifact clears only
`lotus_ai_runtime_execution_missing` from the AI explanation capability and
adds `lotus_ai_live_provider_execution_missing`. The application use case sends
a synthetic redacted evidence packet through the governed
`idea_explanation.pack@v1` route. It accepts only a completed, eligible,
`lotus-idea`-scoped run whose task audit and run identity agree, whose evidence
hash matches the request, and whose review, client-publication, and downstream
authority posture remains fail-closed.

The artifact retains a bounded receipt and its digest, not the request body,
prompt, generated narrative, provider payload, candidate identity, portfolio
identity, client identity, tenant identity, or correlation identity. A
deterministic stub run proves the runtime seam and guardrails only. It does not
prove live-provider execution, signed production output acceptance, provider
rollout, runtime-trust certification, Workbench behavior, client-ready
publication, or supported-feature promotion. An unavailable or invalid runtime
writes an explicit invalid non-proof and clears no blocker.
`make ai-workflow-pack-runtime-execution-proof-contract-gate` validates the v2
receipt schema, source-safety boundary, digest binding, and one-blocker
clearance before aggregate readiness can consume it.

## Response Shape

The success response is intentionally aggregate and source-safe:

| Field | Meaning |
| --- | --- |
| `readinessStatus` | Aggregate RFC-0002 proof state, currently `blocked` |
| `supportabilityStatus` | Aggregate certification posture, currently `not_certified` |
| `capabilityCount` | Number of proof families represented in `capabilities` |
| `blockedCapabilityCount` | Number of proof families still blocked by evidence gaps |
| `overallBlockers` | Source-safe blocker codes across all proof families |
| `sourceOfTruth` | Implementation, RFC, supported-feature, demo-claim, and endpoint-ledger paths |
| `capabilities[]` | Capability-level readiness records for each proof family |
| `capabilities[].capabilityId` | Stable proof-family identifier such as `source-ingestion`, `outbox-delivery`, or `downstream-realization` |
| `capabilities[].readinessStatus` | Capability readiness derived from remaining blockers after proof artifact consumption; blocker-free capabilities report `ready` |
| `capabilities[].supportabilityStatus` | Capability supportability derived from remaining blockers after proof artifact consumption; blocker-free capabilities report `supported` |
| `capabilities[].evidenceRefs` | Source-safe implementation, endpoint, and validated proof artifact references |
| `capabilities[].blockers` | Source-safe blocker codes for that capability family |

The `opportunity-archetype-scenarios` capability reads
`contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`
and prefixes its scenario blockers with `opportunity_archetype_` so they do not
collide with source-ingestion, Workbench, data-mesh, or supported-feature
blockers from other proof families. It is a taxonomy and scenario-readiness
view only. A family-valid and aggregate-current source-ingestion live Core
proof can clear only the high-cash live Core scenario blocker, a valid Risk
concentration proof can clear only the concentration live Risk scenario blocker,
and a valid high-volatility proof can clear only the live Risk volatility
scenario blocker,
and a valid Risk drawdown proof can clear only the drawdown source blocker.
Valid Performance, Core benchmark assignment, low-income Core cashflow, Manage
mandate, Core portfolio-state, Advise mandate/restriction source-product,
Advise mandate/restriction live, Advise missing-suitability, and Advise missing
risk-profile artifacts can clear only their own namespaced source blockers when
supplied.
High-volatility / drawdown review remains blocked on data-mesh, Workbench,
publication, and supported-feature evidence unless those separate proofs are supplied. Client-demo,
data-mesh, Workbench, publication, and supported-feature blockers remain.

Live canonical proof evidence from 2026-07-05 shows the aggregate consumer can
clear Risk concentration, Performance underperformance, and missing-benchmark
Performance readiness source blockers for `PB_SG_GLOBAL_BAL_001` when the
artifacts are generated from current source services and the aggregate
`IMPLEMENTATION_PROOF_EVALUATED_AT_UTC` matches the proof window. The run
cleared only:

| Proof artifact | Cleared blocker | Remaining boundary |
| --- | --- | --- |
| `output/opportunity/risk-concentration-live-proof.json` | `opportunity_archetype_live_risk_source_proof_missing` | Data-mesh certification, Workbench product proof, client publication, supported-feature promotion |
| `output/opportunity/performance-underperformance-live-proof.json` | `opportunity_archetype_live_performance_source_proof_missing` | Benchmark assignment, data-mesh certification, Workbench product proof, client publication, supported-feature promotion |
| `output/opportunity/missing-benchmark-performance-readiness-proof.json` | `opportunity_archetype_performance_benchmark_readiness_source_ref_missing` | Core missing-benchmark live proof, benchmark assignment, benchmark methodology, data-mesh certification, Workbench product proof, client publication, supported-feature promotion |

## Example

```powershell
curl -H "X-Caller-Roles: operator" `
  -H "X-Caller-Capabilities: idea.implementation-proof.readiness.read" `
  "http://localhost:8330/api/v1/implementation-proof/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z"
```

## Source Safety

The endpoint returns aggregate capability posture only. It does not expose:

1. candidate identifiers,
2. portfolio identifiers,
3. client identifiers,
4. source routes,
5. source payloads,
6. outbox event identifiers,
7. aggregate identifiers,
8. raw idempotency keys,
9. broker payloads,
10. request or response bodies,
11. raw entitlement failures,
12. trace or correlation identifiers.

## Evidence

Implementation-backed evidence:

1. application builder: `src/app/application/implementation_proof_readiness.py`,
1. API route: `src/app/api/implementation_proof_readiness.py`,
1. runtime artifact loader: `src/app/runtime/proof_artifacts.py`,
1. artifact generator: `scripts/generate_implementation_proof_readiness.py`,
1. repo-native check that generates and consumes the scheduled-worker
   deploy-proof, durable repository proof, runtime telemetry proof, Workbench
   read-path proof, Advise proposal route proof, Manage action route proof,
   Report intake route source contract, Report materialization source contract, outbox broker
   proof, outbox consumer contract proof, and outbox platform mesh event
   publication proof artifacts, generates default AI model-risk and non-AI
   operator workflow operations proof artifacts unless explicit artifacts are
   supplied, and records validated proof refs in capability evidence:
   `make implementation-proof-readiness-check`,
1. opportunity archetype scenario contract:
   `contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`,
1. opportunity archetype contract gate:
   `make opportunity-archetype-contract-gate`,
   including allocation-drift API module, endpoint, and integration-test
   evidence refs so the scenario readiness contract cannot understate the
   bounded caller-supplied API foundation,
1. AI model-risk operations contract:
   `contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`,
1. AI model-risk operations contract gate:
   `make ai-model-risk-ops-contract-gate`,
1. AI model-risk operations proof gate:
   `make ai-model-risk-operations-proof-contract-gate`,
1. non-AI operator workflow operations contract:
    `contracts/observability/lotus-idea-operator-workflows-operations.v1.json`,
1. non-AI operator workflow operations contract gate:
    `make operator-workflows-ops-contract-gate`,
1. non-AI operator workflow operations proof gate:
    `make operator-workflows-operations-proof-contract-gate`,
1. downstream contract check: `make downstream-realization-contract-gate`,
1. report-owned planned intake contract:
   `lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`,
1. runtime trust telemetry snapshot check:
   `make runtime-trust-telemetry-snapshot-check`,
1. runtime trust telemetry snapshot endpoint:
   `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot`,
1. generated runtime telemetry evidence:
   `output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json`,
1. source-ingestion run-once endpoint:
   `POST /api/v1/source-ingestion/run-once`,
1. source-ingestion run-once runbook:
    `docs/operations/source-ingestion-run-once.md`,
1. source-ingestion live-proof generator:
    `scripts/generate_source_ingestion_live_proof.py`,
1. source-ingestion block-reason diagnostics tests:
    `tests/unit/test_source_ingestion_worker.py`,
1. scheduled source-ingestion worker proof generator:
    `scripts/generate_scheduled_source_ingestion_worker_proof.py`,
1. scheduled source-ingestion worker contract gate:
    `make source-ingestion-scheduled-worker-check`,
1. source-ingestion live-proof contract gate:
    `make source-ingestion-live-proof-contract-gate`,
1. Risk concentration live-proof generator:
    `scripts/generate_risk_concentration_live_proof.py`,
1. Risk concentration live-proof contract gate:
    `make risk-concentration-live-proof-contract-gate`,
1. High-volatility live-proof generator:
    `scripts/generate_high_volatility_live_proof.py`,
1. High-volatility live-proof contract gate:
    `make high-volatility-live-proof-contract-gate`,
1. Risk drawdown live-proof generator:
    `scripts/generate_risk_drawdown_live_proof.py`,
1. Risk drawdown live-proof contract gate:
    `make risk-drawdown-live-proof-contract-gate`,
1. Missing-suitability live-proof generator:
    `scripts/generate_missing_suitability_live_proof.py`,
1. Missing-suitability live-proof contract gate:
    `make missing-suitability-live-proof-contract-gate`,
1. Missing risk-profile source-product proof generator:
    `scripts/generate_missing_risk_profile_source_product_proof.py`,
1. Missing risk-profile source-product proof contract gate:
    `make missing-risk-profile-source-product-proof-contract-gate`,
1. Mandate/restriction source-product proof generator:
    `scripts/generate_mandate_restriction_source_product_proof.py`,
1. Mandate/restriction source-product proof contract gate:
    `make mandate-restriction-source-product-proof-contract-gate`,
1. Missing risk-profile live-proof generator:
    `scripts/generate_missing_risk_profile_live_proof.py`,
1. Missing risk-profile live-proof contract gate:
    `make missing-risk-profile-live-proof-contract-gate`,
1. Manage mandate live-proof generator:
    `scripts/generate_manage_mandate_live_proof.py`,
1. Manage mandate live-proof contract gate:
    `make manage-mandate-live-proof-contract-gate`,
1. Mandate/restriction live-proof generator:
    `scripts/generate_mandate_restriction_live_proof.py`,
1. Mandate/restriction live-proof contract gate:
    `make mandate-restriction-live-proof-contract-gate`,
1. Performance underperformance live-proof generator:
    `scripts/generate_performance_underperformance_live_proof.py`,
1. Performance underperformance live-proof contract gate:
    `make performance-underperformance-live-proof-contract-gate`,
1. Missing-benchmark Performance readiness proof generator:
    `scripts/generate_missing_benchmark_performance_readiness_proof.py`,
1. Missing-benchmark Performance readiness proof contract gate:
    `make missing-benchmark-performance-readiness-proof-contract-gate`,
1. Core benchmark assignment live-proof generator:
    `scripts/generate_core_benchmark_assignment_live_proof.py`,
1. Core benchmark assignment live-proof contract gate:
    `make core-benchmark-assignment-live-proof-contract-gate`,
1. Core portfolio-state live-proof generator:
    `scripts/generate_core_portfolio_state_live_proof.py`,
1. Core portfolio-state live-proof contract gate:
    `make core-portfolio-state-live-proof-contract-gate`,
1. Core portfolio-state live-proof tests:
    `tests/unit/test_core_portfolio_state_live_proof.py`,
1. Bond maturity live-proof generator:
    `scripts/generate_bond_maturity_live_proof.py`,
1. Bond maturity live-proof contract gate:
    `make bond-maturity-live-proof-contract-gate`,
1. Bond maturity live-proof tests:
    `tests/unit/test_bond_maturity_live_proof.py`,
1. Low-income Core cashflow live-proof generator:
    `scripts/generate_low_income_core_cashflow_live_proof.py`,
1. Low-income Core cashflow live-proof contract gate:
    `make low-income-core-cashflow-live-proof-contract-gate`,
1. Low-income Core cashflow live-proof tests:
    `tests/unit/test_low_income_core_cashflow_live_proof.py`,
1. durable repository proof generator:
    `scripts/persistence/generate_durable_repository_proof.py`,
1. durable repository proof contract gate:
    `make durable-repository-proof-contract-gate`,
1. runtime trust telemetry proof generator:
    `scripts/generate_runtime_trust_telemetry_proof.py`,
1. runtime trust telemetry proof contract gate:
    `make runtime-trust-telemetry-proof-contract-gate`,
1. Workbench read-path source-contract proof generator:
    `scripts/workbench/generate_read_path_source_contract.py`,
1. Workbench read-path source-contract proof gate:
    `make workbench-read-path-source-contract-proof-gate`,
1. Gateway/Workbench contract proof generator:
    `scripts/workbench/generate_contract_proof.py`,
1. Gateway/Workbench contract proof contract gate:
    `make gateway-workbench-contract-proof-contract-gate`,
1. Gateway/Workbench discovery contract proof generator:
    `scripts/workbench/generate_discovery_contract_proof.py`,
1. Gateway/Workbench discovery contract proof contract gate:
    `make gateway-workbench-discovery-contract-proof-contract-gate`,
1. outbox broker source-contract proof generator:
    `scripts/outbox/broker/generate_source_contract_proof.py`,
1. outbox consumer contract gate:
    `make outbox-consumer-contract-gate`,
1. outbox consumer contract proof generator:
    `scripts/outbox/generate_consumer_contract_proof.py`,
1. outbox consumer contract proof contract gate:
    `make outbox-consumer-contract-proof-contract-gate`,
1. outbox consumer contract proof tests:
    `tests/unit/outbox/test_outbox_consumer_contract_proof.py`,
1. outbox broker source-contract proof gate:
    `make outbox-broker-source-contract-proof-gate`,
1. outbox platform-mesh event source-contract proof generator:
    `scripts/outbox/platform_mesh/generate_source_contract_proof.py`,
1. outbox platform-mesh event source-contract proof gate:
    `make outbox-platform-mesh-event-source-contract-proof-gate`,
1. outbox platform-mesh event source-contract proof tests:
    `tests/unit/outbox/platform_mesh/test_source_contract_proof.py` and
    `tests/unit/outbox/platform_mesh/test_readiness_consumption.py`,
1. Advise proposal route proof generator:
    `scripts/generate_advise_proposal_route_proof.py`,
1. Manage action route proof generator:
    `scripts/generate_manage_action_route_proof.py`,
1. downstream route proof contract gate:
    `make downstream-route-contract-proof-gate`,
1. downstream route proof tests:
    `tests/unit/test_downstream_route_contract_proof.py`,
1. report intake route source-contract generator:
    `scripts/report/generate_intake_route_source_contract.py`,
1. report intake route source-contract gate:
    `make report-intake-route-source-contract-proof-gate`,
1. report intake route source-contract tests:
    `tests/unit/report/test_intake_route_source_contract.py`,
1. report materialization source-contract generator:
    `scripts/report/generate_materialization_source_contract.py`,
1. report materialization source-contract gate:
    `make report-materialization-source-contract-proof-gate`,
1. report materialization source-contract tests:
    `tests/unit/report/test_materialization_source_contract.py`,
1. outbox broker source-contract proof tests:
    `tests/unit/outbox/broker/test_source_contract_proof.py`,
    `tests/unit/outbox/broker/test_readiness_consumption.py`,
1. platform catalog source contract generator:
    `scripts/data_mesh/generate_platform_catalog_source_contract.py`,
1. platform catalog source contract contract gate:
    `make platform-catalog-source-contract-proof-gate`,
1. platform catalog source contract tests:
    `tests/unit/data_mesh/test_platform_catalog_source_contract.py`,
1. Workbench read-path source-contract proof tests:
    `tests/unit/workbench/test_read_path_source_contract.py`,
1. runtime trust telemetry proof tests:
    `tests/unit/test_runtime_trust_telemetry_proof.py`,
1. outbox delivery run-once endpoint:
    `POST /api/v1/outbox-delivery/run-once`,
1. operation event: `implementation_proof_readiness_read`,
1. endpoint ledger:
    `docs/operations/endpoint-certification-ledger.json`,
1. runtime artifact loader tests:
    `tests/unit/test_proof_artifacts.py`,
1. unit tests:
    `tests/unit/test_implementation_proof_readiness.py`,
1. durable repository proof tests:
    `tests/unit/durable_repository_proof/test_builder.py` and
    `tests/unit/durable_repository_proof/test_ci_receipt.py`,
1. generator tests:
    `tests/unit/test_generate_implementation_proof_readiness.py`,
1. AI workflow-pack registration source-contract generator:
    `scripts/ai_workflow_pack_registration/generate_source_contract_proof.py`,
1. AI workflow-pack registration proof contract gate:
    `make ai-workflow-pack-registration-proof-contract-gate`,
1. AI workflow-pack registration source-contract tests:
    `tests/unit/ai_workflow_pack_registration/test_source_contract_proof.py`,
1. AI workflow-pack runtime execution proof generator:
    `scripts/generate_ai_workflow_pack_runtime_execution_proof.py`,
1. AI workflow-pack runtime execution proof contract gate:
    `make ai-workflow-pack-runtime-execution-proof-contract-gate`,
1. AI workflow-pack runtime execution proof tests:
    `tests/unit/test_ai_workflow_pack_runtime_execution_proof.py`,
1. integration tests:
    `tests/integration/test_implementation_proof_readiness_api.py`.

The `ai-explanation` capability evidence includes the AI model-risk operations
contract, source-valid dashboard, source-valid Prometheus alert rules, runbook,
and proof gate. The v2 source-contract proof adds its evidence reference but
clears no aggregate blocker. It preserves dashboard runtime, alert-rule
runtime, `lotus-ai` execution, runtime trust telemetry, Workbench product,
client-ready publication, and supported-feature promotion blockers.

The non-AI operator workflow operations evidence includes the source-safe
dashboard, Prometheus alert rules, runbook, and proof gates for implemented
source-ingestion, outbox delivery, downstream realization, runtime trust
telemetry, and implementation-proof readiness operation events. Those refs
certify operator visibility only; live source ingestion, external broker
publication, downstream execution outcomes, Gateway/Workbench proof,
data-mesh certification, and supported-feature promotion remain separate
blockers.

Run:

```powershell
python -m pytest tests/unit/test_implementation_proof_readiness.py tests/integration/test_implementation_proof_readiness_api.py -q
make implementation-proof-readiness-check

$env:LOTUS_CORE_QUERY_BASE_URL = "http://localhost:8201"
$env:LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL = "http://localhost:8202"
$env:LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF = "output/source-ingestion/live-proof.json"
$env:LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF = "output/opportunity/high-volatility-live-proof.json"
$env:LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF = "output/opportunity/core-portfolio-state-live-proof.json"
$env:LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF = "output/opportunity/low-income-core-cashflow-live-proof.json"
$env:LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF = "output/opportunity/manage-mandate-live-proof.json"
$env:LOTUS_ADVISE_ROOT = "..\lotus-advise"
$env:LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT = "output/downstream/advise-proposal-route-proof.json"
$env:LOTUS_MANAGE_ROOT = "..\lotus-manage"
$env:LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT = "output/downstream/manage-action-route-proof.json"
$env:LOTUS_REPORT_ROOT = "..\lotus-report"
$env:LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT = "output/report/intake-route-source-contract-proof.json"
$env:LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT = "output/report/materialization-source-contract-proof.json"
$env:LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF_OUTPUT = "output/outbox/outbox-consumer-contract-proof.json"
$env:LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_OUTPUT = "output/outbox/platform-mesh/event-source-contract-proof.json"
$env:LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT = "output/workbench/gateway-workbench-contract-proof.json"
$env:LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_OUTPUT = "output/workbench/gateway-workbench-discovery-contract-proof.json"
$env:IMPLEMENTATION_PROOF_OUTPUT = "output/implementation-proof/implementation-proof-readiness.json"
make implementation-proof-readiness-check

make durable-repository-proof-contract-gate
make runtime-trust-telemetry-proof-contract-gate
make ai-workflow-pack-registration-proof-contract-gate
make outbox-broker-source-contract-proof-gate
make outbox-consumer-contract-proof-contract-gate
make outbox-platform-mesh-event-source-contract-proof-gate
make downstream-route-contract-proof-gate
make report-intake-route-source-contract-proof-gate
make report-materialization-source-contract-proof-gate
make workbench-read-path-source-contract-proof-gate
make gateway-workbench-contract-proof-contract-gate
make gateway-workbench-discovery-contract-proof-contract-gate
make source-ingestion-scheduled-worker-check
make source-ingestion-live-proof-contract-gate
make risk-concentration-live-proof-contract-gate
make high-volatility-live-proof-contract-gate
make risk-drawdown-live-proof-contract-gate
make manage-mandate-live-proof-contract-gate
make missing-suitability-live-proof-contract-gate
make missing-risk-profile-source-product-proof-contract-gate
make missing-risk-profile-live-proof-contract-gate
make performance-underperformance-live-proof-contract-gate
make core-benchmark-assignment-live-proof-contract-gate
make core-portfolio-state-live-proof-contract-gate
make bond-maturity-live-proof-contract-gate
make low-income-core-cashflow-live-proof-contract-gate
make downstream-realization-contract-gate
make runtime-trust-telemetry-snapshot-check
make endpoint-certification-gate
make openapi-gate
```

Use this endpoint to decide whether RFC-0002 is ready for live validation.
Use the live canonical stack only after the readiness blockers have been
cleared by implementation-backed slices.

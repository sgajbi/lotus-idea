# Integrations

`lotus-idea` is an orchestrating domain service. It must integrate through
source-owned APIs, data products, and Gateway/BFF contracts.

## Upstream

1. `lotus-core`
2. `lotus-performance`
3. `lotus-risk`
4. `lotus-advise`
5. `lotus-manage`
6. `lotus-report`
7. `lotus-ai`

## Downstream

1. `lotus-gateway`
2. `lotus-workbench`
3. `lotus-advise`
4. `lotus-manage`
5. `lotus-report`
6. `lotus-render`
7. `lotus-archive`

Integration claims are planned until the relevant RFC-0002 slice is implemented
and certified.

## Gateway Publication Foundation

`lotus-gateway` now publishes bounded read-only routes for the current advisor
queue and candidate detail foundations:

1. `GET /api/v1/ideas/review-queues/advisor`,
2. `GET /api/v1/ideas/candidates/{candidate_id}`.

Gateway forwards caller context and correlation headers to `lotus-idea`,
preserves `lotus-idea` ranking, source references, durable-storage posture, and
unsupported-feature posture, and blocks any upstream
`supportedFeaturePromoted=true` response. Gateway does not generate, rank,
enrich, certify, or promote ideas locally. This is not Workbench proof,
data-product certification, live source proof, client-ready publication, or a
supported feature.

## Data Product Dependencies

Mesh integration truth starts in
`contracts/domain-data-products/lotus-idea-consumers.v1.json`.
`make data-mesh-contract-gate` keeps this declaration aligned with the current
source-authority posture and optionally reconciles it with the sibling
`lotus-platform` generated product catalog when that checkout is present.
Internal operators can call `GET /api/v1/data-mesh/readiness` with the
`operator` role and `idea.mesh.readiness.read` capability to inspect the same
repo-authored readiness truth at runtime. The route reports blockers only; it
does not expose a consumer-facing product contract.

Internal operators can also call
`GET /api/v1/data-mesh/trust-telemetry/runtime-preview` with
`idea.mesh.trust-telemetry.preview.read` to inspect source-safe aggregate
runtime telemetry preview counts from the active repository provider. This
preview is not platform mesh certification, product discovery, Gateway or
Workbench proof, or supported-feature promotion.

The current planned consumer declaration names source-authority products for
the RFC-0002 first-wave map:

1. `lotus-core:PortfolioStateSnapshot:v1`
2. `lotus-core:HoldingsAsOf:v1`
3. `lotus-core:PortfolioCashMovementSummary:v1`
4. `lotus-core:PortfolioCashflowProjection:v1`
5. `lotus-core:BenchmarkAssignment:v1`
6. `lotus-performance:ReturnsSeriesBundle:v1`
7. `lotus-performance:BenchmarkExposureContext:v1`
8. `lotus-performance:MandatePerformanceHealthContext:v1`
9. `lotus-risk:RiskMetricsReport:v1`
10. `lotus-risk:MandateRiskHealthContext:v1`
11. `lotus-risk:RegimeScenarioPackEvaluation:v1`
12. `lotus-advise:AdvisoryProposalLifecycleRecord:v1`
13. `lotus-advise:AdvisoryPolicyEvaluationRecord:v1`
14. `lotus-advise:AdvisoryCopilotInteractionRecord:v1`
15. `lotus-manage:PortfolioActionRegister:v1`
16. `lotus-report:ClientReportEvidencePack:v1`

`lotus-idea` planned producer products remain proposed until implementation and
platform certification.

## Current Source Adapter Posture

RFC-0002 Slice 05 now defines the first Core source-port foundation for
high-cash / idle-liquidity evidence. The application can orchestrate through a
`CoreOpportunitySourcePort`, and the HTTP adapter can call Core's declared
`PortfolioStateSnapshot:v1`, `HoldingsAsOf:v1`,
`PortfolioCashMovementSummary:v1`, and `PortfolioCashflowProjection:v1` routes.

The adapter is intentionally conservative. It consumes a Core source-reported
cash-weight value when present, but it does not reconstruct that value from
cash totals, invested market value, or portfolio totals. Until Core publishes
that field and live proof is captured, source-backed high-cash evaluation can
only return blocked or caller-supplied foundation posture.
The upstream Core source-contract dependency is tracked in
`sgajbi/lotus-core#430`.

## Conversion Boundaries

RFC-0002 Slice 12 now has an internal governed conversion foundation. It maps
conversion targets to downstream source authorities:

1. `advise_proposal` outcomes must come from `lotus-advise`,
2. `manage_review` outcomes must come from `lotus-manage`,
3. `report_evidence` outcomes must come from `lotus-report`.

The current implementation records intent and outcome posture only through
certified internal API foundations:

1. `POST /api/v1/idea-candidates/{candidateId}/conversion-intents`,
2. `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes`.

The opt-in PostgreSQL runtime proof now covers the first internal report
conversion intent/outcome path. It proves `lotus-idea` workflow-state
persistence only; it does not prove downstream service intake.

The report conversion path also has an internal evidence-pack request foundation:

1. `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs`.

That route records source-provenanced request truth for reviewed report
conversion intents and preserves Report/Render/Archive authority refs. It does
not call downstream services, create proposals, create manage actions, create
downstream report packages, render documents, archive material, authorize
any client-ready publication without downstream approval, or grant suitability, execution, compliance, mandate,
or client-communication authority.

Operators can inspect the current downstream blocker posture through:

1. `GET /api/v1/downstream-realization/readiness`.

That route reports conversion intent/outcome counts, report evidence-pack
request counts, source-of-truth paths, planned downstream contract readiness
for Advise, Manage, and Report handoffs, and blocker groups for Advise,
Manage, Report, Render, and Archive realization. It is diagnostic only; the
planned contract records are not downstream route-existence proof and the
endpoint does not call downstream services or promote any integration claim.

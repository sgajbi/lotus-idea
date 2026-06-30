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

Gateway forwards caller context, caller entitlement-scope, and correlation
headers to `lotus-idea`, preserves `lotus-idea` ranking, source references,
durable-storage posture, and unsupported-feature posture, and blocks any upstream
`supportedFeaturePromoted=true` response. Gateway does not generate, rank,
enrich, certify, or promote ideas locally. This is not Workbench product proof,
data-product certification, full source-ingestion certification, client-ready
publication, or a supported feature.

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

Internal operators can call
`GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot` with
`idea.mesh.trust-telemetry.snapshot.read` to inspect the source-safe,
contract-shaped runtime snapshot over the same active repository provider.
This endpoint is diagnostic evidence only and remains blocked until platform
mesh certification and downstream discovery proof exist.

`make runtime-trust-telemetry-snapshot-check` generates the corresponding
contract-shaped runtime evidence under ignored
`output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json`. The artifact
is useful for CI/operator review and remains blocked until platform mesh
certification and downstream discovery proof exist.

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

The adapter is intentionally conservative. It consumes Core's
`HoldingsAsOf:v1` cash-weight value from
`totals.source_reported_cash_weight` when Core reports supported
cash-weight posture, but it does not reconstruct that value from cash totals,
invested market value, or portfolio totals. If Core omits the value or reports
blocked denominator supportability, high-cash evaluation remains blocked.
Core's source-contract dependency was closed in `sgajbi/lotus-core#430`; live
Core proof can now be captured through
`scripts/generate_source_ingestion_live_proof.py` and referenced through
`LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF`. That proof clears only the live-Core
blocker. Scheduled worker deploy proof can now be captured separately through
`scripts/generate_scheduled_source_ingestion_worker_proof.py` and referenced
through `LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_PROOF`; that proof clears
only the scheduled-worker blocker. Mesh certification, Gateway/Workbench proof,
downstream realization proof, and supported-feature promotion remain required
before source-ingestion support or product claims can be promoted.

The Manage source adapter consumes source-authored
`lotus-manage:PortfolioActionRegister:v1` lineage or fingerprint metadata for
`SourceRef.content_hash`. It fails closed with `manage_content_hash_missing`
when Manage omits content hash, request fingerprint, source-batch fingerprint,
or lineage fingerprint metadata; `lotus-idea` does not fabricate source
lineage from Manage response payloads.

All source adapters treat freshness as source-owned proof, not as a derivative
of readiness. Risk, Performance, Core, Manage, and Advise integrations may map
explicit source freshness values into `EvidenceFreshness`, but supportability,
coverage, health state, and data-quality status must not be upgraded to
`current` freshness when the source omits freshness metadata. Missing or
unrecognized freshness remains unavailable/unproven and cannot clear live
source, data-mesh, Workbench, or supported-feature blockers. `make
source-observability-contract-gate` enforces this rule for future source
adapter changes.

Route-foundation proof is consumed only from owning sibling repositories.
`lotus-advise` owns source-safe proposal intake route proof for
`POST /advisory/proposals/idea-intake`; `lotus-manage` owns source-safe action
intake route proof for `POST /api/v1/rebalance/idea-action-intake`; and
`lotus-report` owns source-safe evidence-pack intake route proof for
`POST /reports/idea-evidence-packs`. `lotus-idea` generates default
source-safe proof artifacts from `LOTUS_ADVISE_ROOT`, `LOTUS_MANAGE_ROOT`, and
`LOTUS_REPORT_ROOT` unless the corresponding override artifact variables are
set. Valid artifacts clear only their route-existence blockers. Suitability,
mandate/rebalance authority, execution, report evidence-pack materialization,
rendered output, archive record creation, client-publication authority, and
supported-feature promotion remain blocked.

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

`lotus-idea` can also submit existing internal requests through source-safe
adapter foundations when the corresponding adapter configuration is present:

1. `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions`
   for Advise or Manage conversion intents,
2. `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions`
   for Report evidence-pack requests.

Those submission routes require `idea.downstream-realization.submit` and
`Idempotency-Key`, precheck a local idempotency ledger, propagate
correlation/trace/idempotency context, and return bounded submission posture.
Same-key/same-fingerprint requests replay stored posture without another
adapter call, changed-fingerprint reuse returns `409 idempotency_conflict`, and
missing adapter configuration is persisted as a replayable
`downstream_realization_not_configured` posture. They do not record
authoritative downstream outcomes or prove downstream route existence.

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
The submission routes may call configured adapters, but adapter calls are still
not acceptance, materialization, or route-existence certification from the
owning downstream repositories.
Configured Advise/Manage/Report adapter calls use the shared outbound HTTP
client. Retry defaults remain one attempt; when operators explicitly raise the
attempt count, only timeouts, transport failures, `429`, `502`, `503`, and
`504` are retried, and downstream realization `POST` retries require the
submission `Idempotency-Key`. Client/business failures, malformed responses,
and local idempotency conflicts are not retried.
When the generated or overridden report-intake route proof is valid, the Report contract row
uses `POST /reports/idea-evidence-packs` and reports
`route_foundation_proven_not_certified`; it still remains blocked for
materialization, render, archive, and publication proof.

The planned contract rows are authored in
`contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json` and
validated by `make downstream-realization-contract-gate`. That gate keeps the
records planned, source-authority preserving, blocker-backed, and free of
current-route or supported-feature claims until Advise, Manage, and Report
implementation evidence exists.

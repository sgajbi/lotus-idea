# Integrations

`lotus-idea` is an orchestrating domain service. It must integrate through
source-owned APIs, data products, and Gateway/BFF contracts.

Current summary: bounded integration contracts and selected proof consumption
exist. They do not certify source-owned calculations, downstream execution,
Report/Render/Archive materialization, full Gateway/Workbench product support,
data-product certification, or supported-feature promotion.

## Current Integration Posture

| Reader need | Start here |
| --- | --- |
| Source authority | [Upstream](#upstream) |
| Gateway and Workbench boundary | [Gateway Publication Foundation](#gateway-publication-foundation) |
| Conversion and downstream limits | [Downstream](#downstream), [Conversion Boundaries](#conversion-boundaries) |
| Data product dependencies | [Data Product Dependencies](#data-product-dependencies) |
| Lifecycle and retention receipts | [Lotus AI Provider-Retention Receipt](#lotus-ai-provider-retention-receipt), [Lotus Archive Lifecycle Posture](#lotus-archive-lifecycle-posture), [Bank Lifecycle Authority](#bank-lifecycle-authority) |

### Lotus AI Provider-Retention Receipt

An attested AI explanation may include the signed
`lotus-ai:ProviderRetentionConfirmation:v1` envelope. Idea verifies it against
the governed Lotus AI key-discovery contract, binds it to candidate tenant and
verified run/provider/model identity, and stores only a bounded receipt with AI
lineage. It does not call the provider, record the outcome on Lotus AI's behalf,
or gain lifecycle authority. Provider-native and bank-approval evidence remain
required before certification.

The bounded producer/consumer foundations are merged and mainline-proven in
Lotus AI (`51a8e8e`), Lotus Report (`59385c5`), Lotus Archive (`e5e9253`), and
Lotus Idea (`f496c442`). This is contract-delivery evidence, not production
provider, privacy/legal, retention, archive, or purge certification.

### Lotus Archive Lifecycle Posture

For linked report evidence, Idea consumes
`lotus-archive:IdeaEvidenceLifecycleDecision:v1`. It verifies canonical digest,
Ed25519 signature, trusted-key window, five-minute TTL, tenant, candidate,
evidence-pack, document, retention-policy, and action bindings before domain
policy runs. Exact linkage comes from Idea-owned PostgreSQL state inside the
same transaction, not from caller claims.

Archive legal hold blocks local release, erasure, and purge. Local purge
requires Archive `DISPOSAL_EXECUTED`; eligibility alone is insufficient.
Migration `015` stores bounded receipt lineage and fences applied decision IDs
and digests across restart. This is consumer conformance only: the bank remains
the lifecycle-action authority, Archive remains archive/disposal authority, and
Idea remains authority only for mutation of its own records.

### Bank Lifecycle Authority

| Concern | Governed source |
| --- | --- |
| Decision and key-discovery interface | `lotus-platform/platform-contracts/lifecycle-authority/` |
| Idea consumer binding | `contracts/integrations/lifecycle-authority-consumer.v1.json` |
| Request mapping | `src/app/integration/data_lifecycle/authority_contract.py` |
| Signature and claim verification | `src/app/application/data_lifecycle/authority_verification.py` |
| Durable replay fencing | Migration `013_lifecycle_authority_receipt` |

The consumer declaration pins platform artifacts by path and SHA-256 digest. The data-lifecycle
contract gate recomputes those digests when the sibling platform repository is available, so
contract drift fails before lifecycle mutation code is promoted. This does not make Idea or
Platform a legal/privacy decision issuer. A bank-controlled producer, managed keys, approvals, and
production-authorized purge evidence remain required for certification.

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

## Local/Test Report Materialization Consumer

The Slice 13 consumer can submit an existing Idea evidence pack to Report's
`POST /reports/idea-evidence-packs/materializations` route only in `local` or
`test`. It resolves the associated persisted candidate record, projects only
its trusted portfolio identifier, requires the tenant to match the fixed
`tenant-sg` / `APAC` Report fixture, and accepts only one valid source business
date across the pack. The fixture uses server-configured `json` output and
fails before HTTP I/O when scope or dates are unsafe.

It does not consume browser identity or scope headers and is not a substitute
for an IdP, authenticated session, or token claims. It is disabled outside
local/test while Idea `#380`, platform `#563`, and Workbench `#436` remain
open. A successful handoff is still not proof of Report job completion, Render
output, Archive retention, client publication, or a supported feature.

## Gateway Publication Foundation

`lotus-gateway` publishes bounded read and Idea-workflow routes for the advisor
queue, candidate detail, review actions, feedback, and conversion intents:

1. `GET /api/v1/ideas/review-queues/advisor`,
2. `GET /api/v1/ideas/candidates/{candidate_id}`,
3. `POST /api/v1/ideas/candidates/{candidate_id}/review-actions`,
4. `POST /api/v1/ideas/candidates/{candidate_id}/feedback`,
5. `POST /api/v1/ideas/candidates/{candidate_id}/conversion-intents`.

Gateway forwards caller context, caller entitlement-scope, and correlation
headers to `lotus-idea`, preserves `lotus-idea` ranking, source references,
durable-storage posture, lifecycle, idempotency, and unsupported-feature posture,
and blocks any upstream `supportedFeaturePromoted=true` response. Workbench uses
these routes through its BFF; browser-supplied Idea authority headers are
stripped. Its configured development authority fixture is allowed only in local,
development, and test, while unconfigured and non-development requests fail closed
before Gateway. Authenticated-principal and token-claim derivation remain separate
tracked work.
Gateway does not generate, rank, enrich, approve suitability, create proposals,
execute actions, certify, or promote ideas locally. This is not full Workbench
product proof, authenticated-principal proof, data-product certification,
client-ready publication, or a supported feature.

## Data Product Dependencies

Mesh integration truth starts in
`contracts/domain-data-products/lotus-idea-consumers.v1.json`.
`make data-mesh-contract-gate` keeps this declaration aligned with the current
source-authority posture and optionally reconciles it with the sibling
`lotus-platform` generated product catalog when that checkout is present.
The gate includes the bounded Lotus Risk `ConcentrationRiskReport:v1`
dependency used by the concentration-review foundation; it does not make
`lotus-idea` the concentration calculation authority.
The same gate also protects producer-side provenance, freshness, quality,
lineage, access, and deprecation semantics plus consumer dependency
freshness/provenance metadata before any platform mesh certification claim is
made.
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
`scripts/source_ingestion/generate_runtime_execution.py` and referenced through
`LOTUS_IDEA_SOURCE_INGESTION_RUNTIME_EXECUTION`. That proof clears only the live-Core
blocker when it is family-valid and aggregate-current. Scheduled-worker source
declarations are captured separately through
`scripts/source_ingestion_scheduler/generate_source_contract.py`; this
`source_contract` evidence clears no blocker. Only matching observed
`deployment` evidence from
`scripts/source_ingestion_scheduler/generate_deployment_evidence.py` may clear
the scheduled-worker deployment blocker. Neither proves a scheduled execution.
Mesh certification, Gateway/Workbench proof, downstream realization proof, and
supported-feature promotion remain required before source-ingestion support or
product claims can be promoted.

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
`lotus-report` owns the evidence-pack intake route declaration for
`POST /reports/idea-evidence-packs`. `lotus-idea` generates default
source-safe proof artifacts from `LOTUS_ADVISE_ROOT`, `LOTUS_MANAGE_ROOT`, and
`LOTUS_REPORT_ROOT` unless the corresponding override artifact variables are
set. Valid Advise, Manage, and Report route artifacts are `source_contract`
evidence: they add declaration provenance but clear no live route, request
acceptance, downstream-record, or supportability blockers until governed
runtime evidence exists. The separate Advise idea-intake runtime-execution
artifact is `runtime_execution` evidence and can clear only
`advise_live_contract_proof_missing` after it observes source-safe accepted,
replayed, rejected, idempotency-conflict, authorization-denied, and
tenant-scoped idempotency receipts from the Advise owner route. Suitability,
mandate/rebalance authority, execution, report evidence-pack materialization,
rendered output, archive record creation, client-publication authority, and
supported-feature promotion remain blocked. The separate Manage action-intake
runtime-execution artifact is also `runtime_execution` evidence and can clear
only `manage_live_contract_proof_missing` after it observes source-safe
accepted, replayed, rejected, idempotency-conflict, authorization-denied, and
tenant-scoped idempotency receipts from the Manage owner route. It does not
create action-register records, grant rebalance or execution authority, create
orders, authorize client publication, certify production identity, or promote
support.

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

Advise and Manage adapter wire shape is pinned in
`contracts/downstream-realization/lotus-idea-downstream-intake-wire-contract.v1.json`.
The Manage adapter may use a server-side development fixture only in `local`
and `test` profiles to meet the current owner route's service-context header
requirement. It never accepts identity from browser headers and fails closed in
demo, staging, and production. It is not an IdP/session/token-claim
implementation, does not grant rebalance authority, and does not prove owner
route acceptance; the future trusted identity work remains tracked in issue
`#380`.

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
request counts, local downstream submission denominator, unresolved reconciliation workload,
source-of-truth paths, planned downstream contract readiness for Advise,
Manage, and Report handoffs, and blocker groups for Advise, Manage, Report,
Render, and Archive realization. It is diagnostic only; the local
submission/reconciliation workload is Idea posture, the planned contract records are not
downstream route-existence proof, and the endpoint does not call downstream
services or promote any integration claim.
The submission routes may call configured adapters, but adapter calls are still
not acceptance, materialization, or route-existence certification from the
owning downstream repositories.
Configured Advise/Manage/Report adapter calls use the shared outbound HTTP
client. Retry defaults remain one attempt; when operators explicitly raise the
attempt count, only timeouts, transport failures, `429`, `502`, `503`, and
`504` are retried, and downstream realization `POST` retries require the
submission `Idempotency-Key`. Client/business failures, malformed responses,
and local idempotency conflicts are not retried. Computed backoff delays use a
fixed central 20% downward jitter window; valid upstream `Retry-After` values
remain capped but are not jittered.
Valid Report intake and materialization source contracts add source-safe
declaration refs for `POST /reports/idea-evidence-packs` and
`POST /reports/idea-evidence-packs/materializations`. They do not change the
planned target route, route-fit status, readiness, supportability, or blockers.
Serving/acceptance, materialization execution, rendered output, archive record,
retention/legal hold, and publication require owning-runtime evidence.

The planned contract rows are authored in
`contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json` and
validated by `make downstream-realization-contract-gate`. That gate keeps the
records planned, source-authority preserving, blocker-backed, and free of
current-route or supported-feature claims until Advise, Manage, and Report
implementation evidence exists.

`make implementation-proof-readiness-check` generates the local/dev Advise
runtime proof by default when `LOTUS_ADVISE_ROOT` and `LOTUS_ADVISE_PYTHON`
point to a runnable sibling `lotus-advise` checkout. Override
`LOTUS_IDEA_ADVISE_INTAKE_RUNTIME_EXECUTION_PROOF` only to consume an existing
artifact. The proof is source-safe and does not store raw downstream payloads,
raw IDs, or raw entitlement failures.

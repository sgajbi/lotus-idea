# Repository Engineering Context

## Repository Role

`lotus-idea` is the Lotus domain service for wealth opportunity intelligence and
idea lifecycle management.

It turns source-owned facts from the Lotus ecosystem into governed candidate
ideas, ranked review queues, advisor evidence, and conversion intents. It is a
decision-support and workflow-orchestration service, not a system of record for
portfolio accounting, performance, risk, suitability, compliance, reporting,
rendering, archiving, AI infrastructure, or trade execution.

Service profile: `domain-service`

Primary runtime: `python-fastapi`

Default local port: `8330`

## Business And Domain Responsibility

`lotus-idea` owns:

1. idea detection policy and trigger definitions,
2. candidate idea identity, lifecycle state, review state, expiration, and
   feedback,
3. deterministic scoring, ranking, suppression, deduplication, and queue policy,
4. governed evidence packs explaining why an idea exists,
5. AI-assisted explanation orchestration through `lotus-ai` where explicitly
   governed,
6. conversion intent contracts into advisory, portfolio-management, reporting,
   and Workbench workflows,
7. data-product contracts for idea candidates, review queues, evidence,
   feedback, and conversion outcomes.

`lotus-idea` does not own:

1. official portfolio accounting, client/product master data, positions, cash, or
   transactions,
2. official return, attribution, benchmark, risk, stress, mandate, suitability,
   compliance, or model-portfolio calculations,
3. order execution, order management, settlement, document rendering, document
   archive, model hosting, prompt infrastructure, or provider selection.

## Current-State Summary

The repository is a newly scaffolded Lotus backend baseline. It contains the
bank-buyable engineering shell, CI lane definitions, quality scripts, Docker
baseline, source wiki, supported-feature registry, governance documents,
repo-owned proposed data-mesh contracts, and the first framework-free idea
domain model/lifecycle foundation.

Externally supported business functionality is intentionally not implemented
yet. Initial work is limited to repository foundation, architecture decisions,
data-mesh contract posture, RFCs that define the build order for a
bank-buyable `lotus-idea` service, and internal domain primitives for later
API/persistence slices.

RFC-0002 Slice 00 now records the implementation-start baseline: high cash /
idle liquidity is the first opportunity family, `PB_SG_GLOBAL_BAL_001` remains
the canonical Workbench/demo portfolio, `DEMO_ADV_USD_001` is the current
live-supported high-cash source-ingestion proof seed, advisor-only review is the
first audience, report-only evidence is the first downstream conversion path,
and missing evidence / unsupported-claim verification is the first AI posture.
The baseline keeps all source calculations in their owning services and does
not promote any business capability beyond the current foundation-only
supported-feature state.

RFC-0002 Slice 01 is implemented as platform automation and scaffold review
evidence. The reusable generated-wiki gap found during `lotus-idea` creation is
already addressed in `lotus-platform` commit `549d290` through
`automation/New-Lotus-Service.ps1`, the backend service scaffold guide, and
platform scaffold contract tests that assert the standard repo-local wiki page
set, validation/CI guidance, branch-hygiene posture, and supported-feature
anti-claim wording. No `lotus-core` change or new platform PR is required for
this slice; it closes only scaffold evidence and does not promote product
functionality.

RFC-0002 Slice 03 now implements the pure domain model and lifecycle vocabulary
in `src/app/domain/ideas.py`, with unit coverage for source provenance,
unsupported evidence, valid and invalid lifecycle transitions, review authority
boundaries, conversion gating, immutable models, and bounded scoring. It does
not add API, persistence, source adapters, data-product certification, or
supported-feature promotion.

RFC-0002 Slice 02 is partially implemented as cleanup and current-surface
normalization. API repository state was first isolated out of the high-cash
route module; the current composition provider now lives in
`src/app/runtime/repository_state.py`. Runtime composition providers for the
repository, source ingestion, outbox publisher, and downstream realization
clients now live under `src/app/runtime/` instead of the app root or API layer.
API route metadata now lives in `src/app/api/route_metadata.py`; route modules
and `src/app/api/signal_api_support.py` use the shared `RouteMetadata`
contract, and `make api-route-metadata-gate` blocks future local metadata type
clones.
This is structural cleanup only and does not promote a supported business
feature.

RFC-0002 Slice 04 data-mesh baseline now declares the current source-authority
consumer set from the Slice 00 map, including Core portfolio state,
holdings/cash balance, cash movement, cashflow projection, and benchmark
assignment; Performance returns, benchmark exposure, and mandate performance
health; Risk metrics, mandate risk health, and scenario-pack evaluation; Advise
proposal, policy, and copilot records; Manage action register; and Report
client report evidence. These are source contracts only until runtime adapters,
supportability, and certification evidence exist.

`make data-mesh-contract-gate` now enforces the current Slice 04 posture:
producer products stay proposed, consumer dependencies name governed source
authorities, static trust telemetry remains blocked, SLO/access/evidence policy
files stay coherent, and optional sibling `lotus-platform` catalog/source
manifest evidence is used to catch source-product drift or premature mesh
inclusion.

RFC-0002 Slice 05 is partially implemented for high-cash / idle-liquidity,
concentration, underperformance, allocation-drift mandate-review, bond
maturity / reinvestment, high-volatility / drawdown, missing suitability
context, missing risk-profile review, mandate/restriction review,
low-income / liquidity-shortfall, and missing-benchmark domain policy
foundations.
`src/app/domain/signal_evaluation.py` consumes source-reported cash-weight
evidence and Core source refs, creates deterministic `OpportunitySignal`,
`IdeaEvidencePacket`, and `IdeaCandidate` domain objects for positive cases,
and returns blocked/suppressed/not-eligible outcomes for missing source, stale
source, missing cash weight, entitlement denial, duplicate, and below-threshold
cases. `src/app/ports/core_sources.py`,
`src/app/application/high_cash_signal.py`, and
`src/app/infrastructure/lotus_core_sources.py` now define a Core high-cash
evidence port, source-backed application orchestration, and a conservative HTTP
adapter over the declared Core source products. The adapter preserves source
refs, consumes Core's `HoldingsAsOf:v1` cash-weight value from
`totals.source_reported_cash_weight`, fails closed when Core omits the value or
reports blocked cash-weight supportability, and does not calculate cash weight
from cash totals or market values. This remains internal source-adapter
foundation behavior. `src/app/domain/signal_evaluation.py` also includes
deterministic concentration, underperformance, and allocation-drift
mandate-review policies. `src/app/api/concentration_risk_signals.py` exposes
`POST /api/v1/idea-signals/concentration-risk/evaluate` as a bounded
caller-supplied API foundation over Lotus Risk concentration evidence. It
enforces `idea.signal.evaluate` or advisor role through shared signal API
support, emits bounded operation events, redacts raw source route/hash details
from candidate source refs, and does not fetch Risk sources, calculate
concentration, approve risk methodology, recommend trades, create rebalance
actions, certify data mesh, prove Workbench behavior, approve client
publication, or promote a supported feature. `src/app/api/underperformance_signals.py`
exposes `POST /api/v1/idea-signals/underperformance/evaluate` as a bounded
caller-supplied API foundation over Lotus Performance active-return and
benchmark-context evidence. It enforces `idea.signal.evaluate` or advisor role
through shared signal API support, emits bounded operation events, redacts raw
source route/hash details from candidate source refs, and does not fetch
Performance sources, calculate returns, assign benchmarks, certify benchmark
methodology, recommend trades, create rebalance actions, certify data mesh,
prove Workbench behavior, approve client publication, or promote a supported
feature. `src/app/api/high_volatility_signals.py` exposes
`POST /api/v1/idea-signals/high-volatility/evaluate` as a bounded
caller-supplied API foundation over Lotus Risk `RiskMetricsReport:v1`
volatility evidence. It uses the shared signal API support, emits bounded
operation events, redacts raw source route/hash details from candidate source
refs, and does not fetch Risk sources, calculate volatility, approve Risk
methodology, recommend trades, create rebalance actions, certify data mesh,
prove Workbench behavior, approve client publication, or promote a supported
feature. `src/app/api/drawdown_review_signals.py` exposes
`POST /api/v1/idea-signals/drawdown-review/evaluate` as a bounded
caller-supplied API foundation over Lotus Risk `DrawdownAnalyticsReport:v1`
maximum-drawdown evidence. It uses the shared signal API support, emits bounded
operation events, redacts raw source route/hash details from candidate source
refs, and does not fetch Risk sources, calculate drawdown, approve Risk
methodology, recommend trades, create rebalance actions, certify data mesh,
prove Workbench behavior, approve client publication, or promote a supported
feature. The opportunity archetype contract and
`make opportunity-archetype-contract-gate` pin the high-volatility and
drawdown API modules, routes, and integration tests as high-volatility /
drawdown evidence refs. Future proof-readiness or demo-readiness updates must
preserve those API refs unless the endpoints are intentionally retired with
matching docs, tests, OpenAPI, and supported-features truth.
`src/app/domain/low_income_signal.py` adds the low-income /
liquidity-shortfall policy. The low-income foundation uses
Core-owned `PortfolioCashflowProjection:v1` and
`PortfolioCashMovementSummary:v1` source refs, source freshness, cashflow
count, and a projected cumulative cashflow threshold to create only
advisor-review candidates; it does not infer client income needs, funding
advice, treasury instruction, suitability, or planning objectives.
`src/app/application/low_income_signal.py` maps Core source evidence into this
domain policy with entitlement and source-unavailable failure behavior.
`src/app/api/low_income_signals.py` exposes
`POST /api/v1/idea-signals/low-income/evaluate` as a bounded caller-supplied
API foundation over Core cashflow projection and cash movement evidence. It
enforces `idea.signal.evaluate` or advisor role, emits bounded operation events,
redacts raw source route/hash details from candidate source refs, and does not
fetch Core sources, infer client income needs, approve planning suitability,
provide funding advice, issue treasury instructions, publish client
communication, certify a data product, prove Workbench behavior, or promote a
supported feature.
`src/app/application/low_income_core_cashflow_live_proof.py`,
`scripts/generate_low_income_core_cashflow_live_proof.py`, and
`make low-income-core-cashflow-live-proof-contract-gate` define a source-safe
Core cashflow live-proof contract. A valid artifact clears only the
low-income / liquidity-shortfall live Core cashflow source blocker while
retaining Workbench, data-mesh, client-publication, supported-feature,
suitability, planning, funding-advice, and treasury-instruction boundaries.
`src/app/domain/bond_maturity_signal.py`,
`src/app/application/bond_maturity_signal.py`,
`src/app/api/bond_maturity_signals.py`,
`src/app/application/bond_maturity_live_proof.py`,
`src/app/infrastructure/lotus_core_sources.py`, and
`src/app/ports/core_sources.py` add the bounded bond-maturity / reinvestment
policy, Core `HoldingsAsOf:v1` maturity-date adapter, bounded caller-supplied
API foundation, and source-safe live proof contract. The policy and
`POST /api/v1/idea-signals/bond-maturity/evaluate` can create only
advisor-review candidates from Core-owned maturity facts, source refs,
freshness, maturing holding count, and entitlement posture. The API enforces
`idea.signal.evaluate` or advisor role, emits bounded operation events, redacts
raw source route/hash details from candidate source refs, and does not fetch
Core sources, recommend a replacement product, calculate reinvestment advice,
infer planning suitability, create orders, publish client communication,
certify data mesh, prove Workbench behavior, approve client publication, or
promote a supported feature. A valid Core maturity proof clears only the live
Core maturity source blocker.
The allocation-drift foundation uses
`src/app/ports/manage_sources.py`,
`src/app/application/mandate_health_signal.py`, and
`src/app/infrastructure/lotus_manage_sources.py` to consume
`lotus-manage:PortfolioActionRegister:v1` action-register supportability
posture through the source-owned `/api/v1/rebalance/supportability/summary`
route. The adapter records workflow decision count, lineage edge count,
supportability state, freshness, and source-response lineage, but the domain
policy blocks the current store-wide Manage summary from creating a portfolio
opportunity until portfolio-scoped Manage evidence is proven. This slice does
not calculate drift, mandate compliance, rebalance actions, orders, execution,
or settlement inside `lotus-idea`.
`src/app/api/allocation_drift_signals.py` exposes
`POST /api/v1/idea-signals/allocation-drift/evaluate` as a bounded
caller-supplied API foundation over source-owned Manage action-register and
mandate-health source-ref posture. It enforces `idea.signal.evaluate` or
advisor role through shared signal API support, emits bounded operation
events, redacts raw source route/hash details from candidate source refs, and
does not fetch Manage sources, calculate allocation drift, approve mandate
compliance, create rebalance actions, create orders, certify data mesh, prove
Workbench behavior, approve client publication, or promote a supported
feature.
The opportunity archetype contract and `make opportunity-archetype-contract-gate`
pin `src/app/api/allocation_drift_signals.py`,
`POST /api/v1/idea-signals/allocation-drift/evaluate`, and
`tests/integration/test_allocation_drift_signal_api.py` as allocation-drift
evidence refs. Future proof-readiness or demo-readiness updates must preserve
those API refs unless the endpoint is intentionally retired with matching docs,
tests, OpenAPI, and supported-features truth.
The same gate now requires API module, route, and integration-test evidence for
every implemented caller-supplied signal API recorded in the archetype contract:
concentration risk, underperformance, bond maturity, high volatility,
drawdown, missing suitability, missing risk profile, mandate/restriction,
low income, missing benchmark, and allocation drift. This is design-modularity
and proof-discipline hardening inside the existing service; it does not create
a separately deployable signal microservice and does not promote support.
`src/app/application/manage_mandate_live_proof.py`,
`scripts/generate_manage_mandate_live_proof.py`, and
`make manage-mandate-live-proof-contract-gate` now define a source-safe
Manage mandate live-proof contract. A valid artifact referenced through
`LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF` clears only
`opportunity_archetype_portfolio_scoped_manage_source_proof_missing`,
`opportunity_archetype_mandate_performance_health_source_ref_missing`, and
`opportunity_archetype_mandate_risk_health_source_ref_missing` for
allocation-drift / mandate-review readiness. Core portfolio-state, data-mesh,
Workbench, client-publication, supported-feature, rebalance, action, and
order-execution blockers remain.
`src/app/application/core_portfolio_state_live_proof.py`,
`scripts/generate_core_portfolio_state_live_proof.py`, and
`make core-portfolio-state-live-proof-contract-gate` now define a source-safe
Core portfolio-state live-proof contract. A valid artifact referenced through
`LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF` clears only
`opportunity_archetype_core_portfolio_state_source_ref_missing` for
allocation-drift / mandate-review readiness. Portfolio-scoped Manage proof,
mandate performance-health, mandate risk-health, data-mesh, Workbench,
client-publication, supported-feature, rebalance, action, and order-execution
blockers remain.
`src/app/application/source_ingestion.py`
now adds an internal high-cash source-ingestion orchestration wrapper over the
Core source port and repository port, including generated source-ingestion
idempotency keys, a bounded run-once batch worker foundation, batch decision
counts, and explicit accepted, replayed, conflict, blocked, suppressed, and
skipped-not-eligible decisions. `src/app/application/source_ingestion_worker.py`
and `scripts/run_source_ingestion_worker.py` now add the versioned
manifest-backed run-once worker entrypoint, product-safe check-only summary,
and product-safe run summary that redact raw source payloads, portfolio ids,
raw idempotency keys, and candidate identifiers. Run summaries and live-proof
artifacts now include aggregate `blockReasonCounts`, including bounded Core
cash-weight diagnostics, so operators can distinguish missing, unavailable,
entitlement-blocked, or Core-blocked source evidence without reconstructing
cash weight locally. `make source-ingestion-worker-check` validates the
example manifest and exact source-safe check-only output contract in the local
lint path so future agent changes cannot silently break the worker contract or
leak source-sensitive fields.
`scripts/run_scheduled_source_ingestion_worker.py` now adds a bounded
scheduled-worker entrypoint over the same run-once worker path, and
`docker-compose.yml` includes an opt-in
`lotus-idea-source-ingestion-worker` service under the `worker` profile.
`src/app/application/source_ingestion_scheduled_worker.py`,
`scripts/generate_scheduled_source_ingestion_worker_proof.py`, and
`make source-ingestion-scheduled-worker-check` define and enforce the
source-safe scheduled-worker deploy-proof contract. A valid artifact referenced
through `LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_PROOF` can clear only
the `scheduled_worker_deploy_proof_missing` blocker in readiness; live Core,
data-mesh, Gateway/Workbench, and support-promotion blockers remain.
`make implementation-proof-readiness-check` now generates that deploy-proof
artifact under ignored `output/source-ingestion/` and passes it explicitly into
the aggregate proof-readiness generator, preventing stale scheduled-worker
deploy-proof blockers in repo-native evidence. Aggregate implementation-proof
readiness now records validated source-ingestion live-proof and
scheduled-worker deploy-proof artifact refs in the `source-ingestion`
capability evidence when those blockers clear, preserving source-safe audit
traceability for release reviewers.
It also generates a source-safe durable repository proof artifact under ignored
`output/persistence/` and passes it into aggregate proof-readiness generation.
That artifact cites migration contracts, the PostgreSQL adapter, and the
GitHub PostgreSQL runtime proof lane; it clears only aggregate stale
durable-repository proof blockers and does not configure runtime storage,
certify production storage operations, or promote support.
It also generates a source-safe runtime trust telemetry proof artifact under
ignored `output/trust-telemetry/runtime/` and passes it into aggregate
proof-readiness generation. That artifact exercises a deterministic seeded
candidate snapshot through the runtime telemetry builder and clears only the
repo-owned runtime telemetry blockers:
`runtime_candidate_snapshot_missing`,
`certified_runtime_trust_telemetry_missing`, and
`data_mesh_runtime_telemetry_not_certified`; platform mesh, active producer
products, Gateway/Workbench, and supported-feature blockers remain.
It also generates a source-safe Workbench read-path proof artifact under
ignored `output/workbench/` and passes it into aggregate proof-readiness
generation. That artifact records the bounded Gateway-backed Workbench queue
and detail read implementation and clears only
`workbench_gateway_bff_consumption_proof_missing`; full panel, accessibility,
canonical demo runtime, data-product, and supported-feature blockers remain.
It also generates a source-safe Gateway/Workbench operational proof artifact
under ignored `output/workbench/` from the validated Workbench read-path proof
and passes it into aggregate proof-readiness generation unless
`LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF` overrides it. A valid artifact
clears only `gateway_workbench_proof_missing` for the source-ingestion and
outbox-delivery proof families. Full Workbench product proof, panel proof,
browser accessibility, canonical demo runtime, Gateway/Workbench discovery,
data-product certification, client publication, and supported-feature
promotion remain blocked.
It also generates a source-safe Gateway/Workbench discovery proof artifact
under ignored `output/workbench/` from platform catalog/onboarding evidence,
the Workbench read-path proof, and the Gateway/Workbench operational proof
unless `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF` overrides it. A valid
artifact clears only `gateway_workbench_discovery_proof_missing` for
data-mesh certification and runtime trust telemetry. Data-mesh certification,
producer product activation, platform mesh certification, Workbench product
proof, client publication, and supported-feature promotion remain blocked.
It also generates source-safe `lotus-advise` proposal route and `lotus-manage`
action route proof artifacts under ignored `output/downstream/` from sibling
checkouts configured by `LOTUS_ADVISE_ROOT` and `LOTUS_MANAGE_ROOT`, then
passes the artifacts into aggregate proof-readiness generation unless
`LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF` or
`LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF` overrides them. Valid artifacts record
merged sibling route foundations for `POST /advisory/proposals/idea-intake`
and `POST /api/v1/rebalance/idea-action-intake`, clearing only
`advise_live_contract_proof_missing` and `manage_live_contract_proof_missing`.
Missing sibling evidence writes invalid non-proof artifacts and keeps the
blockers. Suitability, mandate/rebalance authority, downstream execution,
client publication, and supported-feature blockers remain.
It also generates a source-safe `lotus-report` intake route proof artifact
under ignored `output/downstream/` from the sibling checkout configured by
`LOTUS_REPORT_ROOT`, then passes the artifact into aggregate proof-readiness
generation unless `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF` overrides it. A valid
artifact records the merged `POST /reports/idea-evidence-packs` route
foundation and clears only `lotus_report_live_intake_route_proof_missing`;
missing sibling evidence writes an invalid non-proof artifact and keeps the
blocker. Report materialization, render output, archive record, client
publication, and supported-feature blockers remain.
It also generates a source-safe `lotus-report` materialization proof artifact
under ignored `output/downstream/` from the sibling checkout configured by
`LOTUS_REPORT_ROOT`, then passes the artifact into aggregate proof-readiness
generation unless `LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF` overrides it. A
valid artifact records the merged
`POST /reports/idea-evidence-packs/materializations` materialization route and
clears only `report_evidence_pack_live_materialization_proof_missing`,
`rendered_output_creation_missing`, and `archive_record_creation_missing`;
missing sibling evidence writes an invalid non-proof artifact and keeps those
blockers. Client publication and supported-feature blockers remain.
It also generates a source-safe platform mesh onboarding proof artifact under
ignored `output/data-mesh/` from the sibling checkout configured by
`LOTUS_PLATFORM_ROOT`, then passes the artifact into aggregate proof-readiness
generation unless `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF` overrides it. A
valid artifact clears only `platform_source_manifest_inclusion_missing` and
`platform_catalog_inclusion_missing`; missing sibling evidence writes an
invalid non-proof artifact and keeps the corresponding blockers. Mesh
certification, active producer products, SLO/access/evidence certification,
Gateway/Workbench discovery, and supported-feature blockers remain.
It also generates a source-safe outbox platform mesh event publication proof
artifact under ignored `output/outbox/` from repo-owned outbox event/consumer
contracts and the sibling `lotus-platform` checkout configured by
`LOTUS_PLATFORM_ROOT`, then passes the artifact into aggregate proof-readiness
generation unless `LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF`
overrides it. A valid artifact clears only
`platform_mesh_event_publication_proof_missing`; missing sibling evidence
writes an invalid non-proof artifact and keeps the blocker. External broker
publication, downstream delivery, full Gateway/Workbench product proof,
client-ready publication, supported-feature promotion, and full data-mesh
certification remain blocked.
`src/app/application/source_ingestion_readiness.py` and
`GET /api/v1/source-ingestion/readiness` now expose a certified internal
operator diagnostic for run-once worker configuration and certification
blockers without calling Core or leaking source payloads.
`POST /api/v1/source-ingestion/run-once` now exposes a certified internal
operator action for the same bounded source-ingestion batch foundation. It
requires `idea.source-ingestion.run`, blocks before mutation unless durable
repository, manifest, and Core configuration are present, and returns aggregate
decision counts only. The upstream Core cash-weight contract dependency from
`sgajbi/lotus-core#430` is closed in Core PR #431, and `lotus-idea` issue #22
now tracks this adapter-consumption slice. The bounded live Core
source-ingestion proof path now exists through the proof artifact contract, but
certified long-running scheduler runtime, data-mesh certification, full
Gateway/Workbench live proof, downstream realization proof, and
supported-feature promotion remain blocked.
`src/app/application/source_ingestion_live_proof.py` and
`scripts/generate_source_ingestion_live_proof.py` now define the source-safe
live Core source-ingestion proof artifact contract. A valid artifact referenced
through `LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF` can clear
`live_core_source_proof_missing` in the source-ingestion readiness diagnostic
and `opportunity_archetype_live_core_source_proof_missing` in aggregate
opportunity-archetype readiness. It does not clear scheduled-worker,
data-mesh, Workbench, client-publication, or supported-feature blockers.
`make source-ingestion-live-proof-contract-gate` blocks proof payload shape
drift, source-sensitive fields, missing aggregate block diagnostics, and
accidental support promotion.
The runtime boundary now distinguishes Core query-service reads from
query-control-plane snapshot calls through `LOTUS_CORE_QUERY_BASE_URL` and
`LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL`, with `LOTUS_CORE_BASE_URL` retained
only as a compatibility fallback for older single-base local stacks. The live
proof remains source-authority preserving: `lotus-idea` consumes
`totals.source_reported_cash_weight*` only when Core exposes those fields and
must remain blocked rather than reconstructing source-reported cash-weight
supportability locally. Upstream issue `sgajbi/lotus-core#437` remains the
durable tracker for Core-owned runtime payload closure until the Core issue is
closed.
Data-mesh/runtime telemetry certification, full Gateway/Workbench live proof,
and supported-feature promotion remain planned.

RFC-0002 Slice 06 is partially implemented as an internal persistence
foundation in `src/app/domain/persistence.py`. The repository now has immutable
candidate persistence records, deterministic source-ref evidence hashes,
idempotent candidate persistence decisions, duplicate candidate suppression,
evidence replay posture for matched, stale, mismatched, expired, and missing
records, idempotent lifecycle-transition recording, lifecycle-transition
history, conversion intent/outcome records, conversion intent lookup, report
evidence-pack request records, safe audit events for mutating actions,
source-safe outbox records plus retry/dead-letter delivery state for accepted
internal mutations, snapshot recovery for internal replay tests,
application-level high-cash evaluate-and-persist orchestration in
`src/app/application/high_cash_signal.py`, internal high-cash source-ingestion
orchestration in `src/app/application/source_ingestion.py`, and candidate
lifecycle orchestration in `src/app/application/candidate_lifecycle.py`. The
high-cash orchestration persists only created candidates, replays matching
idempotency keys, conflicts on changed payloads, and leaves
blocked/not-eligible/suppressed evaluations non-mutating. The Core-backed
idempotency payload now pins generated candidate and source-signal identity so
same-key source changes conflict instead of being treated as an equivalent
replay. The lifecycle API records governed transitions through the
canonical domain transition graph with accepted, replayed, not-found, conflict,
and invalid-transition posture while still reporting
`durableStorageBacked=false`.
`src/app/application/candidate_evidence_replay.py` and
`POST /api/v1/idea-candidates/{candidateId}/evidence-replay` now expose the
same evidence-hash replay posture as a certified internal operator API. The
route requires `idea.candidate.evidence.replay` plus operator role, compares
caller-supplied current source refs with persisted evidence hashes, returns
matched, stale-source, hash-mismatch, expired, or not-found posture, and does
not call Core, expose raw source routes, grant downstream authority, or promote
a supported feature.
`src/app/ports/idea_repository.py` now centralizes the repository workflow
protocols for candidate snapshots, persistence, evidence replay, lifecycle,
review and feedback, conversion, report evidence-pack requests, and AI
explanation reads. Application
use cases must depend on that port instead of defining local repository
protocols; `tests/unit/test_repository_port_boundary.py` enforces the boundary
so the future durable adapter has one governed contract surface.
`src/app/domain/events.py` defines the internal outbox envelope, status
vocabulary, deterministic event identity, hashed idempotency fingerprint,
source/client-sensitive payload-key guard, published transition, failed retry
transition, and dead-letter transition. Accepted candidate persistence,
lifecycle, review, feedback, conversion, and report evidence-pack mutations
append pending outbox records; replay, conflict, not-found, blocked,
suppressed, and not-eligible paths do not create duplicate outbox work.
`src/app/application/outbox_delivery.py` adds a framework-free run-once
delivery orchestration over a publisher port and repository port. It can mark
events published, failed for retry, or dead-lettered after the configured retry
limit, maps publisher exceptions to bounded source-safe failure reasons, and
returns aggregate counts only. `InMemoryIdeaRepository` and
`PostgresIdeaRepository` expose the same delivery-ready query and status update
contract through `src/app/ports/idea_repository.py`, with unit coverage for
PostgreSQL persistence of delivery status. `src/app/ports/outbox_publisher.py`
now owns the outbox publisher port and `src/app/infrastructure/outbox_publisher.py`
adds a source-safe HTTP broker-publisher adapter foundation that emits bounded
Lotus event envelopes with trace headers and product-safe failure reasons. It
now has a source-safe outbox broker proof artifact for aggregate RFC
implementation-readiness evidence, but is not wired as certified external
broker publication until certified external publication and downstream
delivery evidence exist beyond the bounded outbox proof artifacts.
`src/app/application/outbox_delivery_readiness.py`
and `GET /api/v1/outbox-delivery/readiness` now expose a certified internal
operator diagnostic over aggregate outbox status counts, delivery-ready backlog,
durable repository posture, broker configuration posture, and certification
blockers without exposing event identifiers, aggregate identifiers, raw
idempotency keys, broker payloads, or downstream claims. This is not external
event-publication certification, downstream delivery, or mesh certification.
`POST /api/v1/outbox-delivery/run-once` now exposes the same run-once
orchestration as a certified internal operator action requiring
`idea.outbox-delivery.run`. It fails closed without valid broker configuration,
does not mutate pending outbox records in that blocked posture, emits bounded
`outbox_delivery_run_once` operation events, and returns aggregate counts only.
This is still not live broker runtime certification, downstream consumer proof,
Gateway/Workbench support, or supported-feature promotion.
`src/app/application/outbox_broker_proof.py`,
`scripts/generate_outbox_broker_proof.py`, and
`make outbox-broker-proof-contract-gate` define the bounded proof artifact that
aggregate implementation-proof readiness consumes to clear only broker
configuration/runtime-proof blockers. `contracts/outbox-events/lotus-idea-outbox-events.v1.json`
and `make outbox-event-contract-gate` define the repo-owned event envelope,
implemented event families, and source-safe payload policy.
`contracts/outbox-events/lotus-idea-outbox-consumers.v1.json` and
`make outbox-consumer-contract-gate` now declare governed downstream consumers
for Gateway, Advise, Manage, and Report while keeping them
`contract_declared_not_runtime_certified`. The broker proof artifact cites
implemented adapter and API proof, blocks source-sensitive event and payload
content, and preserves downstream consumer runtime, platform mesh event
publication, Gateway/Workbench, and supported-feature blockers.
`migrations/001_idea_repository_foundation.sql` and its rollback file now define
the first versioned schema contract for database-backed candidate,
idempotency, lifecycle, audit, outbox, review, feedback, conversion, and report
evidence-pack state. `make migration-contract-gate` blocks missing schema
objects, missing indexes, missing rollback posture, or placeholder SQL.
`src/app/infrastructure/migrations.py` and `scripts/run_migrations.py` now add
the first PostgreSQL migration execution path, with `make migration-execution-gate`
dry-running apply and rollback plans in CI, and `make migrate` /
`make migrate-rollback` requiring `LOTUS_IDEA_DATABASE_URL` for real execution.
`src/app/infrastructure/postgres_repository.py` now adds the first tested
PostgreSQL repository adapter over the governed repository port surface. It
round-trips candidate, idempotency, lifecycle, audit, outbox, review, feedback,
conversion, and report evidence-pack state through typed tables and JSONB
snapshots, and rolls back on database flush failure.
`src/app/infrastructure/postgres_codecs.py` isolates PostgreSQL JSON
serialization/deserialization helpers so adapter growth preserves the
maintainability gate instead of normalizing an oversized infrastructure module.
`src/app/application/durable_repository_proof.py`,
`scripts/generate_durable_repository_proof.py`, and
`make durable-repository-proof-contract-gate` now define and enforce a
source-safe durable repository proof contract for aggregate RFC proof-readiness
evidence. This proof references the migration, adapter, and CI runtime-proof
surface only; runtime endpoints still report durable storage from the active
repository provider and `LOTUS_IDEA_DATABASE_URL`.
`src/app/runtime/repository_state.py` now wires the adapter into API runtime
selection when `LOTUS_IDEA_DATABASE_URL` is configured, while keeping
process-local state as the default. Repository-backed routes derive
`durableStorageBacked` responses and operation-event labels from the active
repository. `make postgres-integration-gate` now exercises the real FastAPI
runtime provider against a PostgreSQL 18 service by applying migrations,
persisting a high-cash candidate through the API, reloading the provider,
proving idempotency replay from database state, projecting the advisor queue,
transitioning lifecycle state, recording review approval, recording feedback,
recording report conversion intent/outcome state, recording a report
evidence-pack request, proving internal Core-backed source-ingestion replay and
same-key changed-source conflict recovery through the repository adapter,
validating the backing workflow tables, and proving schema rollback/reapply
restores a usable API persistence contract. This is still not production
storage certification: deploy migration evidence, certified long-running
scheduled source-ingestion runtime proof, live Core source adapter proof,
data-product certification, live broker runtime proof, downstream consumer
proof, downstream workflow proof, and supported-feature promotion remain
planned. The current run-once worker CLI and scheduled worker deploy-contract
foundation are developer/operator foundations only and are validated in
check-only mode by `make source-ingestion-worker-check` and
`make source-ingestion-scheduled-worker-check`.

RFC-0002 Slice 07 is partially implemented as an internal deterministic scoring
and review-queue projection plus certified API foundation in
`src/app/domain/scoring.py`. The
repository now has bounded score inputs for materiality, urgency, confidence,
evidence quality, freshness, relevance, downstream fit, and conflict flags;
policy-versioned score breakdowns with typed reason codes; immutable candidate
score attachment; priority buckets; stable review queue ordering; snooze,
suppression, unsupported-evidence, expired, unscored, non-reviewable, and
duplicate exclusion rules; repository-snapshot application orchestration in
`src/app/application/review_queue.py`; certified internal advisor queue API
foundation in `src/app/api/review_queues.py`; optional
tenant/book/portfolio/client access-scope filtering over persisted candidate
truth; and golden unit/integration coverage for expected ordering and edge
cases. The advisor queue now parses platform caller-context scope headers,
applies those entitlements automatically, rejects broader query scopes
fail-closed, and has bounded read-only Gateway forwarding proof for the queue
route. Candidate detail now applies the same caller entitlement-scope headers
fail-closed before returning persisted candidate detail, and Gateway forwards
those headers on the published detail route. This is not yet a supported queue
or candidate-detail product: database-backed queue
projection proof exists only inside the opt-in PostgreSQL runtime proof.
Workbench proof, data-product certification, trust telemetry, and
supported-feature promotion remain planned.

RFC-0002 Slice 08 is partially implemented as an internal advisor review and
feedback governance plus certified API foundation in
`src/app/domain/review_governance.py`. The
repository now has advisor-only first-wave review action policy, fail-closed
tenant/book/portfolio/client scope checks, approve-for-conversion, reject,
no-action, suppress, snooze, and escalation outcomes, governed feedback events,
safe audit events, source/evidence provenance, and queue projection interaction
tests. `src/app/application/review_workflow.py` and
`src/app/domain/persistence.py` now add internal repository-backed review and
feedback workflow persistence orchestration with idempotency replay, conflict,
not-found posture, safe audit events, review decision and feedback event
snapshots, and lifecycle history updates. `src/app/api/review_workflow.py`
exposes certified internal review-action and feedback endpoints over this
foundation:
`POST /api/v1/idea-candidates/{candidateId}/review-actions` and
`POST /api/v1/idea-candidates/{candidateId}/feedback`. These APIs require
mutating capabilities, caller role, upstream-authorized scope, and
`Idempotency-Key`, and they return product-safe permission, not-found,
idempotency-conflict, and invalid-state errors. This is not yet a supported
review product: PostgreSQL-backed review and feedback recording proof exists
only inside the opt-in runtime proof; there is no Gateway/Workbench proof,
platform-scoped runtime entitlement contract, PM/compliance/operator queue
surface, data-product certification, trust telemetry, or supported-feature
promotion.

RFC-0002 Slice 09 is partially implemented as an internal AI governance
foundation in `src/app/domain/ai_governance.py`,
`src/app/application/ai_governance.py`, and `src/app/api/ai_governance.py`.
The repository now has redacted evidence envelopes for future `lotus-ai`
workflow-pack requests, forbidden metadata rejection, deterministic
AI-unavailable fallback, verifier outcomes for unsupported claims and
forbidden actions, safe AI audit events, no-downstream-authority semantics for
AI output, and a certified internal API at
`POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`. The API
requires `idea.ai-explanation.evaluate`, returns redacted evidence without
routes or raw provider/prompt material, emits bounded `ai_explanation`
operation events, and always reports `durableStorageBacked=false`,
`lotusAiRuntimeExecuted=false`, and `supportedFeaturePromoted=false` in the
default process-local runtime. It now records source-safe AI explanation
lineage through the repository port; PostgreSQL-backed runs persist that
lineage durably and the runtime proof now covers accepted, replayed, and
changed-request conflict behavior through the API without prompts, provider
payloads, raw source routes, trace ids, correlation ids, portfolio ids, client
ids, or free-form source payloads.
`GET /api/v1/ai-explanations/readiness` now exposes a certified internal
operator diagnostic for AI explanation supportability. It requires both the
`operator` role and `idea.ai-explanation.readiness.read`, returns guardrail
availability plus `not_certified` blockers, emits bounded
`ai_explanation_readiness_read` operation events with `lotus-ai` source
authority, reports durable lineage-store backing from the active repository,
and does not expose prompts, provider payloads, candidate identifiers, source
routes, portfolio identifiers, or client identifiers. This
is not yet a supported AI explanation product: no `lotus-ai` runtime workflow
execution, prompt/RAG/provider integration, Workbench proof, trust telemetry,
or supported-feature promotion exists. The repo-owned AI lineage store proof is
enforced by `make ai-lineage-store-proof-contract-gate` and can clear only the
`certified_ai_lineage_store_missing` blocker in aggregate proof readiness; it
does not certify `lotus-ai` execution, provider calls, Workbench, client-ready
publication, or supported-feature promotion.
The repo-owned AI model-risk operations contract is enforced by
`make ai-model-risk-ops-contract-gate`; the repo-owned Grafana dashboard,
Prometheus alert rules, and runbook are certified by
`make ai-model-risk-operations-proof-contract-gate` over implemented
AI explanation telemetry only. That proof is not `lotus-ai` runtime execution,
Workbench product proof, data-mesh certification, client-ready publication, or
supported-feature promotion.
`GET /api/v1/implementation-proof/readiness` now exposes a certified internal
operator diagnostic for aggregate RFC-0002 proof posture. It requires the
`operator` role and `idea.implementation-proof.readiness.read`, returns
source-safe blockers across source ingestion, advisor queue, AI explanation,
data mesh, runtime trust telemetry preview/snapshot evidence, outbox delivery,
Workbench realization, downstream realization, and supported-feature promotion,
emits bounded
`implementation_proof_readiness_read` operation events, and does not expose
candidate identifiers, source payloads, outbox event identifiers, broker
payloads, Gateway/Workbench proof, data-product certification, certified
runtime trust telemetry, or blocked client-ready publication or
supported-feature promotion.
`GET /api/v1/downstream-realization/readiness` now exposes a certified internal
operator diagnostic for downstream realization supportability. It requires the
`operator` role and `idea.downstream-realization.readiness.read`, reports
conversion intent, conversion outcome, and report evidence-pack request counts
plus Advise, Manage, Report, Render, and Archive blockers, source-safe
downstream application-orchestration and adapter-foundation presence, and planned downstream
contract-readiness records for Advise, Manage, and Report handoff seams from
`contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`.
The Report handoff seam now cites the report-owned planned intake contract at
`lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`,
which clears only the prior missing-contract blocker. When the generated default
or `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF` override references a valid
source-safe artifact, the Report row moves to
`POST /reports/idea-evidence-packs` with `route_foundation_proven_not_certified`,
clearing only the Report route blocker. When generated default or overridden
Advise/Manage route proofs reference valid source-safe artifacts, the Advise
and Manage rows move to `POST /advisory/proposals/idea-intake` and
`POST /api/v1/rebalance/idea-action-intake`, clearing only their route-proof
blockers. `make downstream-realization-contract-gate` and
`make downstream-route-contract-proof-gate` block premature downstream
execution, supported-feature, source-authority drift, and source-sensitive
route-proof evidence. The endpoint emits bounded
`downstream_realization_readiness_read` operation events and does not call
downstream services, grant suitability or mandate/rebalance authority, create
Report packages, render output, archive records, or promote downstream
realization.
`scripts/generate_implementation_proof_readiness.py` and
`make implementation-proof-readiness-check` now provide the same source-safe
proof-readiness snapshot as repo-native automation evidence for CI, async runs,
and operator handoff. The generator accepts explicit source-ingestion manifest,
live-proof, scheduled-worker proof, durable repository proof, runtime trust
telemetry proof, Advise proposal route proof, Manage action route proof,
Report intake route proof, Workbench read-path proof, and AI lineage store
proof paths for deterministic CI evidence without requiring ambient process
environment mutation. The Makefile generates the default Advise/Manage/Report
route proofs under ignored `output/downstream/`, default outbox platform mesh
event publication proof under ignored `output/outbox/`, and keeps CI stable
when sibling evidence is absent by preserving the corresponding blockers
instead of failing the aggregate proof snapshot. The
source-ingestion capability evidence includes validated source-ingestion
live-proof and scheduled-worker deploy-proof artifact refs when the
corresponding blockers are cleared.
The aggregate snapshot now also includes an
`opportunity-archetype-scenarios` capability built from
`contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`.
It exposes source-safe taxonomy evidence and namespaced
`opportunity_archetype_*` blockers for canonical scenario replay gaps without
clearing live replay, Workbench product, data-mesh certification, client
publication, or supported-feature promotion blockers.
The AI explanation capability evidence includes the AI model-risk operations
contract and gate refs so release reviewers can see the not-certified
dashboard-control and alert-candidate posture without clearing model-risk
dashboard or alert blockers.
The same capability now includes a generated source-safe AI lineage store proof
artifact under ignored `output/ai/` when the artifact passes
`make ai-lineage-store-proof-contract-gate`. That proof clears only the stale
lineage-store blocker and leaves `lotus-ai` runtime execution, Workbench proof,
client-ready publication, and supported-feature promotion blocked.
The same capability now also includes a generated source-safe sibling
`lotus-ai` workflow-pack registration proof artifact under ignored
`output/ai/` when the artifact passes
`make ai-workflow-pack-registration-proof-contract-gate`. That proof clears
only `workflow_pack_runtime_contract_not_certified` after `lotus-ai` exposes
the governed `idea_explanation.pack@v1` registration, binding, queue policy,
supportability surface, and test coverage. It leaves `lotus-ai` runtime
execution, provider calls, runtime trust telemetry, Workbench proof,
client-ready publication, and supported-feature promotion blocked.
The same capability now also includes a generated source-safe sibling
`lotus-ai` workflow-pack runtime execution proof artifact under ignored
`output/ai/` when the artifact passes
`make ai-workflow-pack-runtime-execution-proof-contract-gate`. That proof
clears only `lotus_ai_runtime_execution_missing` after `lotus-ai` exposes the
deterministic idea explanation stub, source-safe guardrails, workflow-pack
execution path, stub-provider routing, restricted `lotus-idea` caller policy,
and test coverage. It leaves workflow-pack registration, live provider
execution, provider rollout, runtime trust telemetry, Workbench proof,
client-ready publication, and supported-feature promotion blocked.
The live operator API also consumes configured source-ingestion live,
source-ingestion scheduled-worker, durable repository, runtime trust telemetry,
Workbench read-path, Advise proposal route, Manage action route, Report intake
route, AI lineage store, AI model-risk operations, and AI workflow-pack
registration/runtime execution proof artifact
paths through
`LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF`,
`LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_PROOF`,
`LOTUS_IDEA_DURABLE_REPOSITORY_PROOF`,
`LOTUS_IDEA_RUNTIME_TRUST_TELEMETRY_PROOF`,
`LOTUS_IDEA_WORKBENCH_READ_PATH_PROOF`, and
`LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF`, and
`LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF`, and
`LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF`, and
`LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF`, and
`LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF`, and
`LOTUS_IDEA_AI_LINEAGE_STORE_PROOF`, and
`LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF`, and
`LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF`. The repo-native Makefile
default generates `LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT` from
`LOTUS_ADVISE_ROOT`, `LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT` from
`LOTUS_MANAGE_ROOT`, `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT` from
`LOTUS_REPORT_ROOT`, `LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF_OUTPUT` from
`LOTUS_REPORT_ROOT`,
`LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_OUTPUT` from
`LOTUS_PLATFORM_ROOT`, and
`LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT` from `LOTUS_AI_ROOT`,
`LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT` from `LOTUS_AI_ROOT`,
then consumes those artifacts when no override is set, clearing only the
matching aggregate proof blockers while preserving all certification and
support-promotion blockers.

RFC-0002 Slice 10 is partially implemented as certified internal API
foundation plus bounded read-only Gateway publication for advisor queue and
candidate detail. `POST /api/v1/idea-signals/high-cash/evaluate` accepts
caller-supplied, source-owned Core evidence references and source-reported cash
weight, enforces `idea.signal.evaluate` capability or advisor role, and returns
deterministic candidate, blocked, suppressed, or not-eligible posture.
`POST /api/v1/idea-signals/low-income/evaluate` accepts caller-supplied,
source-owned Core cashflow projection and cash movement evidence, enforces
`idea.signal.evaluate` capability or advisor role, returns deterministic
advisor-review candidate, blocked, suppressed, or not-eligible posture, redacts
raw source route/hash details from candidate source refs, and does not infer
client income needs, approve planning suitability, provide funding advice,
issue treasury instructions, publish client communication, certify data
products, prove Gateway/Workbench behavior, or promote a supported feature.
`POST /api/v1/idea-signals/bond-maturity/evaluate` accepts caller-supplied,
source-owned Core holdings maturity evidence, enforces `idea.signal.evaluate`
capability or advisor role, returns deterministic advisor-review candidate,
blocked, suppressed, or not-eligible posture, redacts raw source route/hash
details from candidate source refs, and does not fetch Core sources, recommend
replacement products, calculate reinvestment advice, own maturity schedule
authority, approve planning suitability, create orders, publish client
communication, certify data products, prove Gateway/Workbench behavior, or
promote a supported feature.
`POST /api/v1/idea-signals/concentration-risk/evaluate` accepts
caller-supplied, source-owned Lotus Risk concentration evidence, enforces
`idea.signal.evaluate` capability or advisor role, returns deterministic
advisor-review candidate, blocked, suppressed, or not-eligible posture, redacts
raw source route/hash details from candidate source refs, and does not fetch
Risk sources, calculate concentration, approve risk methodology, recommend
trades, create rebalance actions, publish client communication, certify data
products, prove Gateway/Workbench behavior, or promote a supported feature.
`POST /api/v1/idea-signals/allocation-drift/evaluate` accepts
caller-supplied, source-owned Lotus Manage action-register and mandate-health
source-ref posture evidence, enforces `idea.signal.evaluate` capability or
advisor role, returns deterministic portfolio-manager review candidate,
blocked, suppressed, or not-eligible posture, redacts raw source route/hash
details from candidate source refs, and does not fetch Manage sources,
calculate allocation drift, approve mandate compliance, create rebalance
actions, create orders, publish client communication, certify data products,
prove Gateway/Workbench behavior, or promote a supported feature.
`POST /api/v1/idea-signals/missing-risk-profile/evaluate` accepts
caller-supplied, source-owned Advise risk-profile posture evidence, enforces
`idea.signal.evaluate`, returns source-safe candidate or blocked posture, and
does not approve risk profiling, suitability, policy, proposal, client
publication, typed data-product certification, Gateway, Workbench, or supported
feature promotion.
`POST /api/v1/idea-signals/missing-suitability/evaluate` accepts
caller-supplied, source-owned Advise policy-evaluation evidence, enforces
`idea.signal.evaluate`, returns source-safe compliance-review candidate or
blocked posture, redacts raw source route/hash details from candidate source
refs, and does not approve suitability, policy, proposal, sign-off, client
publication, data-product certification, Gateway, Workbench, or supported
feature promotion.
`POST /api/v1/idea-signals/missing-benchmark/evaluate` accepts
caller-supplied, source-owned Core benchmark-assignment posture evidence,
enforces `idea.signal.evaluate`, returns source-safe advisor-review candidate,
blocked, suppressed, or not-eligible posture, redacts raw source route/hash
details from candidate source refs, and does not assign benchmarks, certify
benchmark methodology, calculate portfolio or benchmark performance, publish
client communication, certify data products, prove Gateway/Workbench behavior,
or promote a supported feature.
`POST /api/v1/idea-signals/high-cash/evaluate-and-persist` uses the same source
evidence contract, requires `idea.candidate.persist` plus `Idempotency-Key`,
and persists created candidates through the internal in-memory
idempotency/audit repository foundation with accepted, replayed, duplicate, or
conflict posture. `GET /api/v1/idea-candidates/{candidateId}` exposes a
source-safe candidate detail projection over persisted snapshots, redacted
evidence, lifecycle history, review/feedback/conversion/report summaries, and
audit summary posture, applies caller entitlement-scope headers fail-closed
when present, and avoids exposing source routes, raw evidence hashes, or
downstream authority. `POST /api/v1/idea-candidates/{candidateId}/evidence-replay`
exposes internal operator replay posture over current source refs and persisted
evidence hashes with matched, stale-source, hash-mismatch, expired, and
not-found outcomes, without live Core calls, raw source export, downstream
authority, Workbench proof, data-product certification, or
supported-feature promotion. `GET /api/v1/review-queues/advisor` exposes deterministic
advisor queue projection over persisted candidate snapshots and optional
tenant/book/portfolio/client scope filters. The review-action
and feedback APIs expose internal review workflow persistence over the same
repository provider and return accepted, replayed, not-found, conflict,
permission, or invalid-state posture without granting downstream authority.
`POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions` exposes the
idempotent lifecycle transition foundation over persisted candidates, requires
`idea.candidate.lifecycle.transition` plus `Idempotency-Key`, applies the
canonical lifecycle graph, and records audit/lifecycle history without granting
downstream authority. The conversion APIs expose internal intent/outcome
recording over review-approved persisted candidates:
`POST /api/v1/idea-candidates/{candidateId}/conversion-intents` and
`POST /api/v1/conversion-intents/{conversionIntentId}/outcomes`. They require
conversion-specific capabilities plus `Idempotency-Key`, enforce the candidate
review gate, target-source authority, replay/conflict posture, and explicit
no-authority semantics for downstream realization, suitability, execution, and
client communication. The report evidence-pack API exposes internal request
recording for reviewed report conversion intents:
`POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs`.
It requires `idea.report-evidence-pack.request` plus `Idempotency-Key`,
preserves safe source summaries and Report/Render/Archive source-authority
refs, and explicitly does not create Report, Render, or Archive records or
authorize client-ready publication. The AI explanation API exposes internal
fallback/verifier evaluation over persisted candidate evidence:
`POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`. It
requires `idea.ai-explanation.evaluate`, blocks unsupported claims and
forbidden actions, and explicitly does not call providers, execute `lotus-ai`
runtime workflows, certify runtime AI lineage-store evidence, or grant downstream authority.
`GET /api/v1/ai-explanations/readiness` exposes the internal model-risk
supportability diagnostic for AI explanation guardrails and certification
blockers without executing `lotus-ai`. All twelve business routes plus the
AI-explanation-readiness, data-mesh-readiness, source-ingestion-readiness, and
advisor-queue-readiness operator diagnostics
are covered by OpenAPI and endpoint certification evidence. The PostgreSQL runtime
proof now covers the high-cash persist, advisor queue, lifecycle, review,
feedback, conversion intent/outcome, and report evidence-pack request path.
`lotus-gateway` main now publishes read-only `GET
/api/v1/ideas/review-queues/advisor` and `GET
/api/v1/ideas/candidates/{candidate_id}` routes that forward caller
context, caller entitlement scope, and correlation to `lotus-idea`, preserve `lotus-idea` ranking and source
refs, and block upstream `supportedFeaturePromoted=true`. This is not yet a
supported product capability: there is now bounded read-only Workbench
queue/detail rendering through `lotus-workbench` PR #391, but no live source
adapters, review-action/feedback/conversion Workbench affordances,
entitlement-denied live panel proof, supported database-backed API state beyond
the current opt-in PostgreSQL workflow proof, data-product certification,
runtime trust telemetry, or supported-feature promotion.

RFC-0002 Slice 12 is partially implemented as an internal conversion governance
foundation in `src/app/domain/conversion_governance.py`. The repository now has
review-gated conversion intent creation for Advise proposal, Manage review, and
Report evidence targets; target-to-source-authority mapping; lifecycle
transition to converted posture; downstream outcome recording; safe audit
events; idempotency-key validation at the domain command boundary; repository
idempotency and snapshot lookup for conversion intents/outcomes; certified
internal conversion intent/outcome APIs; and explicit no-authority semantics
for execution, suitability, client communication, and downstream realization.
`src/app/application/downstream_realization.py` adds source-safe application
orchestration for submitting Advise and Manage conversion intents and Report
evidence-pack requests through downstream ports. It deliberately does not
record authoritative downstream outcomes, because downstream services remain
the source of acceptance, rejection, completion, materialization, and failure
truth. `src/app/api/downstream_realization.py` now exposes certified internal
submission APIs for existing Advise/Manage conversion intents and Report
evidence-pack requests:
`POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions`
and
`POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions`.
Both routes require `idea.downstream-realization.submit` and
`Idempotency-Key`, propagate correlation/trace/idempotency headers through the
adapter port, fail closed with `503 downstream_realization_not_configured` when
adapter configuration is absent, and return submission posture only. They do
not record downstream outcomes, grant downstream authority, prove route
existence, or promote a supported feature. `src/app/ports/downstream_realization.py` and
`src/app/infrastructure/downstream_realization.py` add source-safe HTTP adapter
foundations for Advise proposal intent, Manage action intent, and Report
evidence-pack materialization request handoff envelopes. The adapters preserve
target source authority, omit source routes and raw downstream responses, and
map failures to bounded product-safe reasons. The operator readiness diagnostic
reports adapter-foundation presence, current conversion intent/outcome/report
evidence request counts, and explicit downstream blockers. This is not yet a
supported conversion product: PostgreSQL-backed internal conversion
intent/outcome recording proof exists only inside the opt-in runtime proof;
there is no certified live Advise/Manage/Report route contract, downstream
acceptance proof, Gateway/Workbench proof, data-product certification, runtime
trust telemetry, or supported-feature promotion.

RFC-0002 Slice 13 is partially implemented as an internal report evidence-pack
request foundation in `src/app/domain/report_evidence.py`. The repository now
has report conversion-intent gating, evidence-hash reconciliation, safe source
summary projection, Report/Render/Archive source-authority refs, retention
policy references, idempotent repository persistence, safe audit events, and a
certified internal API for report evidence-pack requests. This is not yet a
supported report evidence product: PostgreSQL-backed internal request recording
proof exists only inside the opt-in runtime proof, and bounded sibling
`lotus-report` intake/materialization proof can clear only named proof blockers
when merged evidence is present. There is no client-ready publication authority,
no suitability/rebalance authority, no Gateway/Workbench product proof, no
data-product certification, no runtime trust telemetry certification, and no
supported-feature promotion.

RFC-0002 Slice 14 is partially implemented as internal data-mesh-readiness and
runtime trust telemetry preview/snapshot diagnostics. `src/app/application/data_mesh_readiness.py`
reads repo-owned producer, mesh-readiness, and trust-telemetry contracts, and
`GET /api/v1/data-mesh/readiness` exposes the current operator-facing
`planned` / `not_certified` posture with explicit blockers. Those blockers now
name the missing platform promotion proof for source-manifest inclusion,
catalog inclusion, SLO certification, access-policy certification,
evidence-policy certification, Gateway/Workbench discovery proof, and
supported-feature promotion so aggregate proof-readiness cannot hide the real
mesh certification path. `src/app/application/runtime_trust_telemetry.py`
builds a source-safe runtime preview from the active repository snapshot, and
`GET /api/v1/data-mesh/trust-telemetry/runtime-preview` exposes aggregate
candidate, source-authority, freshness, supportability, lifecycle, review,
feedback, conversion, and report evidence-pack counts for callers with
`idea.mesh.trust-telemetry.preview.read` plus the `operator` role. The preview
emits a bounded `mesh_trust_telemetry_preview_read` operation event, reports
`certificationStatus=not_certified`, `platformCertified=false`, and
`supportedFeaturePromoted=false`, and is also available through
`make runtime-trust-telemetry-preview-check`. The same application service now
builds a contract-shaped runtime trust telemetry snapshot exposed through
`GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot` for callers with
`idea.mesh.trust-telemetry.snapshot.read` plus the `operator` role. The
snapshot diagnostic emits a bounded `mesh_trust_telemetry_snapshot_read`
operation event and preserves the same not-certified/no-promotion posture.
`scripts/generate_runtime_trust_telemetry_snapshot.py` and
`make runtime-trust-telemetry-snapshot-check` write the same source-safe
generated evidence to
`output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json`.
These endpoints and generated artifacts are diagnostic evidence only; they are
not data-product certification, platform source-manifest inclusion,
Gateway/Workbench discovery, raw lineage export, or supported mesh promotion.
`src/app/application/mesh_policy_proof.py`,
`scripts/generate_mesh_policy_proof.py`, and
`make mesh-policy-proof-contract-gate` now validate the repo-owned
SLO/access/evidence policy proof for `lotus-idea:IdeaCandidate:v1`. The default
`make implementation-proof-readiness-check` target generates
`output/data-mesh/mesh-policy-proof.json` and passes it into aggregate
readiness. A valid artifact clears only
`mesh_slo_policy_certification_missing`,
`mesh_access_policy_certification_missing`, and
`mesh_evidence_policy_certification_missing`. It deliberately leaves
`data_mesh_not_certified`, `producer_products_not_active`,
platform source-manifest/catalog, Gateway/Workbench discovery, and
supported-feature blockers in place.
`src/app/application/platform_mesh_onboarding_proof.py`,
`scripts/generate_platform_mesh_onboarding_proof.py`, and
`make platform-mesh-onboarding-proof-contract-gate` now validate bounded sibling
`lotus-platform` source-manifest/catalog onboarding evidence. A valid artifact
can clear only `platform_source_manifest_inclusion_missing` and
`platform_catalog_inclusion_missing` in aggregate implementation-proof
readiness. It deliberately leaves `data_mesh_not_certified`,
`producer_products_not_active`, certified runtime telemetry, SLO/access/evidence
certification, Gateway/Workbench discovery, and supported-feature blockers in
place.
The controlling platform standard for this boundary is
`../lotus-platform/docs/standards/Lotus Data Mesh Standard.md`; catalog-visible
onboarding is not mesh certification.

RFC-0002 Slice 15 is partially implemented as a bounded operation observability
foundation. `src/app/observability/logging.py` now defines the
`lotus_idea_operation_events_total` metric, bounded operation/outcome/
supportability vocabulary, product-safe structured operation logs, and
sensitive operation-attribute rejection. Request exception diagnostics now use
a central helper that logs route templates rather than raw URL paths, and
`make source-observability-contract-gate` blocks raw `print()`, direct Python
logging, or low-level `log_event` bypasses in application source. High-cash evaluation, candidate
persistence, candidate detail read, lifecycle transition, advisor review queue,
candidate evidence replay, review action, AI explanation, feedback, conversion
intent, conversion outcome, report evidence-pack request, and
data-mesh-readiness diagnostic APIs emit bounded operation events. The
downstream submission API emits `downstream_realization_submission` events with
`not_certified` supportability, source authority `lotus-idea`, accepted,
blocked, not-found, permission-denied, invalid-request, or invalid-state
outcomes, and no candidate, portfolio, client, request-body, or response-body
identifiers.
The
source-ingestion-readiness diagnostic emits
`source_ingestion_readiness_read` events with `not_certified` supportability,
blocked/accepted configuration posture, and no source payloads.
The source-ingestion run-once operator action emits
`source_ingestion_run_once` events with `not_certified` supportability,
aggregate work-item count buckets, fail-closed configuration posture, and no
source payloads, portfolio ids, candidate ids, or raw idempotency keys.
The AI-explanation-readiness diagnostic emits
`ai_explanation_readiness_read` events with `not_certified` supportability,
blocked certification posture, `lotus-ai` source authority, and no prompt,
provider, candidate, source-route, portfolio, or client identifiers.
The advisor-queue-readiness diagnostic emits
`review_queue_readiness_read` events with `not_certified` supportability,
aggregate-only queue counts, blocked certification posture, and no candidate or
access-scope identifiers.
The downstream-realization-readiness diagnostic emits
`downstream_realization_readiness_read` events with `not_certified`
supportability, blocked certification posture, source-authority labels for the
owning downstream systems, and no candidate, portfolio, client, request-body, or
response-body identifiers.
All operation events are emitted without
portfolio/client/account/holding/transaction identifiers, request/response
bodies, trace ids, or correlation ids as metric labels. This is not yet full
production observability: live AI runtime telemetry, live source certification,
dashboard/alert, Gateway entitlement, durable persistence, data-product
certification, and supported-feature promotion remain planned.

RFC-0002 Slice 18 is partially implemented for documentation and agent context
truth. `docs/operations/api-certification.md` now summarizes the full certified
internal foundation endpoint inventory from
`docs/operations/endpoint-certification-ledger.json`, including each endpoint's
foundation scope, required capability, and unsupported boundary. This keeps
operator-facing documentation aligned with endpoint certification evidence
without promoting any supported business feature.
`docs/demo/README.md`, `docs/demo/client-demo-operating-process.md`,
`docs/demo/client-facing-lotus-idea-brief.md`,
`docs/demo/client-demo-pack.template.md`, and `wiki/Demo-Readiness.md` now
define the app-specific client-demo hub, client-facing business narrative,
claim states, client-pack versus internal-evidence separation, evidence-pack
template, validation commands, acceptance checklist, rehearsal/follow-up
discipline, and do-not-claim boundaries. The process is governed documentation
truth only; it does not promote external demo readiness, supported features,
downstream materialization, client publication, or certified data-mesh status.
RFC-0002 Slice 16 now also has a governed opportunity archetype/scenario
contract at
`contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`.
The contract records high cash / idle liquidity as the first partially
implemented journey and concentration risk review, underperformance review,
allocation drift / mandate review, bond maturity / reinvestment,
high-volatility review, missing suitability context, missing risk-profile
review, mandate/restriction review, low-income / liquidity shortfall, and missing-benchmark review as
non-promoted bounded foundations.
Concentration is backed by deterministic
policy, a Lotus Risk concentration source port, a fail-closed HTTP adapter, a
source-safe live-proof artifact contract, and focused unit tests.
Underperformance is backed by deterministic policy, a Lotus Performance
returns-series source port, a fail-closed HTTP adapter over
`POST /integration/returns/series`, and focused unit tests that prove
source-reported active-return consumption and missing-benchmark-context
blocking. Allocation drift / mandate review is backed by deterministic policy,
a Lotus Manage action-register posture source port, a fail-closed HTTP adapter
over `GET /api/v1/rebalance/supportability/summary`, and focused unit tests
that prove current store-wide Manage posture blocks portfolio-scoped
opportunity claims. High volatility is backed by deterministic policy, a Lotus
Risk `RiskMetricsReport:v1` source port, a fail-closed HTTP adapter over
`POST /analytics/risk/calculate`, a source-safe live-proof artifact contract,
and focused unit tests that prove source-reported volatility consumption,
non-ready risk supportability blocking, and no local risk-methodology
calculation, plus a bounded caller-supplied API foundation at
`POST /api/v1/idea-signals/high-volatility/evaluate` with endpoint
certification and operation-event evidence. Drawdown review is backed by deterministic policy, a Lotus Risk
`DrawdownAnalyticsReport:v1` source port, a fail-closed HTTP adapter over
`POST /analytics/risk/drawdown`, a source-safe live-proof artifact contract,
and focused unit tests that prove source-reported max-drawdown consumption,
non-ready risk supportability blocking, and no local risk-methodology
calculation, plus a bounded caller-supplied API foundation at
`POST /api/v1/idea-signals/drawdown-review/evaluate` with endpoint
certification and operation-event evidence. Missing suitability
context is backed by deterministic policy, a Lotus Advise
`AdvisoryPolicyEvaluationRecord:v1` workflow source port, a fail-closed HTTP
adapter over `GET /advisory/policy-evaluations/{evaluation_id}/workflow`, and
focused unit tests that prove Advise-owned open approval, disclosure, consent,
and sign-off posture can create only a compliance-review candidate without
approving suitability, policy, proposals, sign-off, client publication, or
external communication. Missing risk-profile review is backed by deterministic
policy and bounded consumption of explicit Lotus Advise risk-profile diagnostic
posture from `AdvisoryPolicyEvaluationRecord:v1`; generic open suitability or
policy requirements stay on the missing suitability context path. It can create
only an advisor-review evidence-gap candidate and does not approve risk
profiling, suitability, policy, proposal, client publication, or external
communication. A source-safe missing risk-profile live-proof artifact can clear
only the Advise risk-profile live-source blocker when current explicit
diagnostic evidence produces a deterministic review candidate; it does not
certify a typed risk-profile source product, risk profiling authority,
suitability, policy, proposal, data mesh, Workbench, client publication, or
supported-feature promotion. A source-safe typed missing risk-profile
source-product proof artifact can clear only the typed Advise risk-profile
source-product blocker when it cites
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1`, the Advise source-product
contract, trust telemetry contract, and Advise-owned missing, stale, expired,
and review-due diagnostic vocabulary; it does not certify live Advise
reachability, risk profiling authority, suitability, policy, proposal, data
mesh, Workbench, client publication, or supported-feature promotion. Low-income / liquidity shortfall is backed by
deterministic policy, a Lotus Core cashflow source port, a fail-closed HTTP
adapter over `/portfolios/{portfolio_id}/cash-movement-summary` and
`/portfolios/{portfolio_id}/cashflow-projection`, the bounded
`POST /api/v1/idea-signals/low-income/evaluate` API over caller-supplied Core
cashflow evidence, and focused unit/integration tests that prove
source-reported projected cumulative cashflow consumption while blocking
planning, funding-advice, treasury-instruction, suitability, Workbench,
client-publication, and supported-feature claims. Bond maturity / reinvestment
consumes governed Core `HoldingsAsOf:v1` maturity dates through a bounded
source adapter, `POST /api/v1/idea-signals/bond-maturity/evaluate` over
caller-supplied Core holdings maturity evidence, and optional source-safe live
proof; focused unit/integration tests prove source-reported next maturity date
and maturing position count consumption while replacement product
recommendation, reinvestment advice, maturity schedule authority, planning
suitability, order execution, Workbench, data-mesh, client-publication, and
supported-feature claims remain blocked.
Mandate/restriction review is backed by deterministic policy,
`src/app/application/mandate_restriction_signal.py`, and the bounded
`POST /api/v1/idea-signals/mandate-restriction/evaluate` API over
caller-supplied Core, Manage, or Advise source refs. It can create only a
compliance-review candidate from explicit source-owned restriction posture and
does not approve suitability, change mandate state, clear product/country
restrictions, create orders, publish client communication, or promote support.
`src/app/application/mandate_restriction_live_proof.py`,
`scripts/generate_mandate_restriction_live_proof.py`, and
`make mandate-restriction-live-proof-contract-gate` define a source-safe Advise
mandate/restriction live-proof path. A valid artifact referenced through
`LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF` clears only the live restriction
source proof blocker when current `AdvisoryPolicyEvaluationRecord:v1` evidence
carries an explicit source-owned restriction diagnostic; generic Advise policy
diagnostics do not validate this proof.
`src/app/application/mandate_restriction_source_product_proof.py`,
`scripts/generate_mandate_restriction_source_product_proof.py`, and
`make mandate-restriction-source-product-proof-contract-gate` define the
separate typed Advise mandate/restriction source-product proof path. A valid
artifact referenced through
`LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF` clears only the typed
restriction source-product blocker when it cites
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1`, the Advise source-product
contract, trust telemetry contract, and Advise-owned mandate, product
restriction, country restriction, and suitability-policy actionability
diagnostic vocabulary; it does not certify live Advise reachability, clear
restrictions, change mandate state, approve suitability or policy, certify
data mesh, prove Workbench behavior, approve client publication, create
rebalance/order authority, or promote support.
A valid Risk concentration live-proof
artifact clears only the live
Risk source blocker, and a valid Performance underperformance live-proof
artifact clears only the live Performance source blocker. A valid high-volatility
live-proof artifact clears only the live Risk volatility source blocker. A
valid Risk drawdown live-proof artifact clears only the drawdown source blocker.
A valid Core benchmark assignment live-proof artifact clears only the
underperformance benchmark-assignment source-ref blocker.
A valid Core portfolio-state live-proof artifact clears only the
allocation-drift / mandate-review Core portfolio-state source-ref blocker.
A valid low-income Core cashflow live-proof artifact clears only the
low-income / liquidity-shortfall live Core cashflow source blocker.
A valid missing-suitability live-proof artifact clears only the Advise policy
live-source blocker.
A valid missing risk-profile source-product proof artifact clears only the
typed Advise risk-profile source-product blocker.
A valid missing risk-profile live-proof artifact clears only the Advise
risk-profile live-source blocker.
A valid Manage mandate live-proof artifact clears only the portfolio-scoped
Manage action-register source blocker and current source refs for source-owned
mandate performance-health and mandate risk-health contexts.
A valid mandate/restriction live-proof artifact clears only the Advise live
restriction source blocker.
A valid mandate/restriction source-product proof artifact clears only the typed
Advise restriction source-product blocker.
Concentration still
carries data-mesh certification, Workbench, client-publication, and
supported-feature blockers; underperformance still carries live Performance,
data-mesh, Workbench, client-publication, and supported-feature blockers after
Core benchmark assignment proof is supplied. Allocation drift still carries
data-mesh, Workbench, client-publication, supported-feature, rebalance, action,
and order-execution blockers after live Manage mandate and Core portfolio-state
proofs are supplied. High volatility / drawdown
review still carries data-mesh, Workbench, client-publication, and
supported-feature blockers after live Risk volatility and drawdown proofs are supplied.
Missing suitability context still carries data-mesh, Workbench,
client-publication, and supported-feature blockers after live Advise policy
proof is supplied.
Missing risk-profile review still carries live Advise source, data-mesh,
Workbench, client-publication, and supported-feature blockers after typed
Advise risk-profile source-product proof is supplied, and still carries
data-mesh, Workbench, client-publication, and supported-feature blockers after
both typed source-product proof and live Advise risk-profile proof are supplied.
Mandate/restriction review still carries live Advise source, Workbench,
data-mesh, client-publication, and supported-feature blockers after typed
Advise restriction source-product proof is supplied; it still carries typed
restriction source-product, Workbench, data-mesh, client-publication, and
supported-feature blockers after live Advise restriction proof is supplied;
and it still carries Workbench, data-mesh, client-publication, and
supported-feature blockers after both source-product and live Advise proofs
are supplied. Neither proof clears restrictions, changes mandate state,
approves policy/suitability/proposals, or creates rebalance/order authority.
Low-income / liquidity shortfall still carries Workbench, data-mesh,
client-publication, and supported-feature blockers after live Core cashflow
proof is supplied, and it still does not certify client income needs, funding
advice, treasury instruction, suitability, or planning objectives.
Missing-benchmark review is backed by deterministic policy, the existing
Lotus Core benchmark-assignment source port, a bounded caller-supplied API, and
bounded Lotus Performance benchmark-readiness proof consumption over
`ReturnsSeriesBundle:v1`. It can create only an advisor-review evidence-gap
candidate when Core-owned benchmark identity, effective assignment, active
status, or assignment version posture is missing; it does not assign a
benchmark, calculate performance or benchmark returns, certify methodology, or
promote support. A valid source-safe missing-benchmark live Core proof artifact
clears only the missing-benchmark live Core source blocker; a valid source-safe
Performance benchmark-readiness proof artifact clears only the missing-benchmark
Performance source-ref blocker. Data-mesh, Workbench, client-publication, and
supported-feature blockers remain.
The
`make opportunity-archetype-contract-gate` command blocks unsupported demo,
client publication, data-mesh certification, and supported-feature promotion
claims. Aggregate implementation-proof readiness consumes this contract as
blocked scenario readiness so operators can see archetype replay gaps without
confusing them with source-ingestion, Workbench, data-mesh, downstream, or
supported-feature proof families.
Valid source-ingestion live Core proof now clears only
`opportunity_archetype_live_core_source_proof_missing` for the first high-cash
journey while preserving Workbench, data-mesh, client-publication, and
supported-feature blockers.
`make risk-concentration-live-proof-contract-gate` now validates the optional
Lotus Risk concentration live-proof artifact. When a valid artifact is supplied
through aggregate implementation-proof readiness, it clears only
`opportunity_archetype_live_risk_source_proof_missing` and keeps data-mesh,
Workbench, client-publication, and supported-feature blockers intact.
`make performance-underperformance-live-proof-contract-gate` validates the
optional Lotus Performance underperformance live-proof artifact. When a valid
artifact is supplied through aggregate implementation-proof readiness, it clears
only `opportunity_archetype_live_performance_source_proof_missing` and keeps
benchmark-assignment, data-mesh, Workbench, client-publication, and
supported-feature blockers intact.
`make missing-benchmark-performance-readiness-proof-contract-gate` validates the
optional Lotus Performance benchmark-readiness proof artifact for
missing-benchmark review. When a valid artifact is supplied through aggregate
implementation-proof readiness, it clears only
`opportunity_archetype_performance_benchmark_readiness_source_ref_missing` and
keeps Core missing-benchmark live proof, data-mesh, Workbench,
client-publication, and supported-feature blockers intact. It does not assign
benchmarks, calculate performance or benchmark returns, or certify benchmark
methodology.
`make core-benchmark-assignment-live-proof-contract-gate` validates the optional
Lotus Core benchmark assignment live-proof artifact. When a valid artifact is
supplied through aggregate implementation-proof readiness, it clears only
`opportunity_archetype_benchmark_assignment_source_ref_missing` and keeps live
Performance, data-mesh, Workbench, client-publication, and supported-feature
blockers intact. It does not assign benchmarks, calculate benchmark returns, or
certify benchmark methodology.
`make core-portfolio-state-live-proof-contract-gate` validates the optional
Lotus Core portfolio-state live-proof artifact. When a valid artifact is
supplied through aggregate implementation-proof readiness, it clears only
`opportunity_archetype_core_portfolio_state_source_ref_missing` and keeps
portfolio-scoped Manage, mandate performance-health, mandate risk-health,
data-mesh, Workbench, client-publication, supported-feature, rebalance, action,
and order-execution blockers intact unless a separate valid Manage mandate
live-proof artifact supplies those source refs.
`make missing-benchmark-live-proof-contract-gate` validates the optional Lotus
Core missing-benchmark live-proof artifact. When a valid artifact is supplied
through aggregate implementation-proof readiness, it clears only
`opportunity_archetype_missing_benchmark_live_core_source_proof_missing` and
keeps Performance benchmark-readiness, data-mesh, Workbench, client-publication,
and supported-feature blockers intact. It does not assign benchmarks, calculate
benchmark returns, or certify benchmark methodology.
`make low-income-core-cashflow-live-proof-contract-gate` validates the optional
Lotus Core cashflow live-proof artifact. When a valid artifact is supplied
through aggregate implementation-proof readiness, it clears only
`opportunity_archetype_live_core_cashflow_source_proof_missing` and keeps
Workbench, data-mesh, client-publication, and supported-feature blockers
intact. It does not infer client income needs, funding advice, treasury
instruction, suitability, or planning objectives.
`make high-volatility-live-proof-contract-gate` validates the optional Lotus
Risk high-volatility live-proof artifact. When a valid artifact is supplied
through aggregate implementation-proof readiness, it clears only
`opportunity_archetype_live_risk_volatility_source_proof_missing` and keeps
drawdown, data-mesh, Workbench, client-publication, and supported-feature
blockers intact.
`make risk-drawdown-live-proof-contract-gate` validates the optional Lotus Risk
drawdown live-proof artifact. When a valid artifact is supplied through
aggregate implementation-proof readiness, it clears only
`opportunity_archetype_drawdown_source_proof_missing` and keeps volatility,
data-mesh, Workbench, client-publication, and supported-feature blockers
intact.

## CI And Merge Governance

`lotus-idea` follows the Lotus rebase-only PR completion model. Do not squash
RFC, workflow, scaffold, or implementation commits; keep small commits linear
and let branch protection require the PR merge gate before `main` updates.
Rebase auto-merge is allowed only when `LOTUS_AUTOMERGE_TOKEN` is configured so
the merge actor is not the suppressed workflow `GITHUB_TOKEN`. When that token
is absent, the auto-merge helper warns and exits cleanly so an authorized human
or release actor can perform the required rebase merge. Merged PRs must
explicitly dispatch the Main Releasability Gate so post-merge truth does not
depend only on a push-triggered workflow. After every merge, delete the remote
feature branch and the matching local feature branch, then re-run branch hygiene
before final closure. Durable
RFC/docs/wiki/context/contract truth is complete only when it is present on
`main`, published where required, and not stranded on a side branch.
Strict branch protection requires the PR Merge Gate contexts for workflow lint,
lint/typecheck/security, unit, integration, e2e, combined coverage, PostgreSQL
runtime proof, and Docker build validation. PostgreSQL runtime proof is a
first-class required status so durable persistence, migration, idempotency, and
source-ingestion recovery behavior cannot regress behind an implicit Docker
dependency.

Coverage aggregation jobs use the current approved `actions/download-artifact`
major and suppress its upstream Node deprecation noise with
`NODE_OPTIONS=--no-deprecation`. Do not downgrade action majors to quiet runner
logs; fix or document the owned warning source instead.

## Architecture And Module Map

1. `src/app/main.py`: application entrypoint, health, readiness, metadata, and
   OpenAPI surface.
2. `src/app/api/`: route modules and DTO mapping. Routes must expose explicit
   idea contracts and must not embed domain logic. Current business routes are
   registered directly on the FastAPI app before Prometheus instrumentation so
   endpoint certification and metrics instrumentation remain compatible. Route
   modules must use `app.api.runtime_dependencies` for runtime composition
   helpers and must not import `app.runtime` directly.
3. `src/app/runtime/`: process-local dependency composition for repositories,
   source adapters, outbox publishers, and downstream realization clients. The
   repository provider is process-local in-memory by default and
   PostgreSQL-backed when `LOTUS_IDEA_DATABASE_URL` is configured. Workers and
   proof generators depend on this package for runtime wiring directly; API
   routes reach it only through the API runtime dependency facade so route
   modules stay thin and reviewable.
4. `src/app/application/`: use-case orchestration, source aggregation, and
   conversion workflows. Current use cases map the certified high-cash API
   requests into framework-free domain signal evaluation, fetch Core high-cash
   evidence through a source port, and internally persist created high-cash
   candidates through the Slice 06 idempotency/audit repository contract.
   Review-queue orchestration reads candidate repository snapshots and delegates
   ordering/exclusion behavior to the Slice 07 domain policy. Review/feedback
   workflow orchestration applies Slice 08 domain governance to repository
   snapshots and persists accepted decisions and feedback through the same
   idempotency/audit posture. Candidate lifecycle orchestration maps API
   commands into the Slice 06 idempotent lifecycle transition repository
   contract. Conversion workflow orchestration applies Slice 12 conversion
   governance to repository snapshots and persists accepted intents/outcomes
   through the same idempotency/audit posture. Report evidence-pack
   orchestration applies Slice 13 evidence-pack governance to report conversion
   intents and persists source-provenanced request packages without downstream
   Report/Render/Archive realization. Downstream realization orchestration
   submits existing Advise/Manage conversion intents and Report evidence-pack
   requests through downstream ports while leaving authoritative outcome
   recording to downstream services. Downstream-realization-readiness
   orchestration reports conversion intent/outcome/report evidence-pack request
   counts, source-safe application-orchestration and adapter-foundation
   presence, planned Advise/Manage/Report handoff contract posture, and
   downstream blockers without calling downstream systems or claiming route
   existence in owning services.
   Source-ingestion-readiness orchestration reports manifest, Core query URL,
   Core query-control-plane URL, durable repository configuration, and
   certification blockers for the high-cash run-once worker without executing
   Core source reads. The
   source-ingestion run-once route executes the same bounded domain batch only
   when durable repository and runtime configuration are present, returning
   aggregate decision counts only.
   Runtime-trust-telemetry orchestration emits both the internal preview and a
   contract-shaped, source-safe runtime snapshot while keeping platform
   certification blockers explicit.
   Implementation-proof-readiness orchestration aggregates current RFC-0002
   capability proof blockers across source ingestion, queue, AI, data mesh,
   runtime trust telemetry preview/snapshot evidence, outbox delivery and its
   bounded broker proof artifact, bounded Advise proposal, Manage action, and
   Report intake route proof artifacts,
   Workbench, opportunity archetype scenarios, downstream realization, and
   supported-feature promotion without leaking source payloads, event
   identifiers, broker payloads, or promoting support. Capability readiness and
   supportability are normalized after proof
   artifact consumption, so future proof additions cannot leave stale
   `blocked` or `not_certified` labels when a proof family has no remaining
   blockers.
4. `src/app/domain/`: framework-free idea models, lifecycle rules, scoring
   policies, review-queue projection, review governance, AI governance,
   conversion governance, report evidence-pack request governance, evidence
   policy, deterministic governance checks, internal persistence records,
   replay posture, idempotency, audit primitives, source-safe outbox records,
   and retry/dead-letter delivery state semantics.
5. `src/app/ports/`: interfaces to `lotus-core`, `lotus-performance`,
   `lotus-risk`, `lotus-advise`, `lotus-manage`, `lotus-report`, and `lotus-ai`.
   `idea_repository.py` owns the central repository workflow protocols used by
   application orchestration, and `core_sources.py` owns the high-cash,
   benchmark-assignment, bond-maturity, and low-income Core evidence ports.
6. `src/app/infrastructure/`: HTTP/database/message adapters behind ports. The
   current Core adapter preserves source-data product refs, requires Core to
   report cash weight explicitly rather than deriving it locally, consumes Core
   holdings maturity evidence for bounded bond-maturity / reinvestment review
   without moving maturity-schedule authority or reinvestment advice into
   `lotus-idea`, and consumes Core cashflow products for bounded low-income /
   liquidity-shortfall review without moving cashflow methodology into
   `lotus-idea`. The layer also
   contains source-safe downstream realization adapter foundations for
   Advise/Manage/Report handoff envelopes, migration execution helpers,
   PostgreSQL codec helpers, and `PostgresIdeaRepository`, which is tested as a
   durable repository adapter and selected by API runtime wiring when
   `LOTUS_IDEA_DATABASE_URL` is configured.
7. `src/app/observability/`: correlation, logging, tracing, metrics, route-template request
   diagnostics, bounded idea operation events, safe metric-label policy, and audit event helpers.
8. `src/app/security/`: caller context, advisor/PM role handling, entitlement
   policy, and sensitive-output controls.
9. `src/app/resilience/`: timeout, retry, backoff, and circuit-breaker policies.
10. `src/app/contracts/`: contract models shared by route and application
    boundaries.
11. `contracts/domain-data-products/`: proposed producer products, consumer
    dependencies, and mesh readiness posture.
12. `contracts/trust-telemetry/`, `contracts/mesh-slo/`,
    `contracts/mesh-access/`, and `contracts/mesh-evidence/`: planned trust,
    SLO, access, and evidence policies that stay blocked until runtime
    certification.
13. `docs/architecture/adr/`: architecture decisions that shape implementation.
14. `docs/rfcs/`: governed implementation slices and evidence requirements.
15. `tests/unit`, `tests/integration`, `tests/e2e`: test pyramid baseline.
16. `wiki/`: repo-authored GitHub wiki source with the standard Lotus operator
    pages for getting started, development workflow, validation/CI, roadmap,
    supported features, operations, security, integrations, architecture, and
    RFC navigation.

## Runtime And Integration Boundaries

Upstream dependencies:

1. `lotus-core`: source facts for accounts, portfolios, holdings, instruments,
   cash, mandates, clients, products, and benchmark identity.
2. `lotus-performance`: source-owned performance, attribution,
   underperformance, benchmark, and analytics evidence.
3. `lotus-risk`: source-owned risk measures, stress/scenario outputs, exposure
   flags, and risk attention events.
4. `lotus-advise`: proposal, suitability, advisory journey, and client-advice
   context.
5. `lotus-manage`: model portfolio, rebalance, drift, DPM action, and mandate
   implementation context.
6. `lotus-report`: report pack metadata and reportable evidence requirements.
7. `lotus-ai`: AI workflow, prompt, RAG, verifier, evaluation, and provider
   gateway capabilities.

Downstream consumers:

1. `lotus-gateway`: API composition and product-surface BFF routing.
2. `lotus-workbench`: advisor and portfolio-manager review panels.
3. `lotus-advise`: conversion to proposal and suitability journeys.
4. `lotus-manage`: conversion to model/rebalance/action workflows.
5. `lotus-report`: reportable idea evidence and commentary packages.

Boundary rule: `lotus-idea` may reference source evidence and computed values
only with source provenance. It must not recompute or override official numbers
owned by upstream services.

## Repo-Native Commands

1. install or bootstrap: `make install`
2. lint: `make lint`
3. typecheck: `make typecheck`
4. unit tests: `make test-unit`
   Use `UNIT_TESTS=<path>` for focused unit validation.
5. integration tests: `make test-integration`
   Use `INTEGRATION_TESTS=<path>` for focused integration validation.
6. end-to-end tests: `make test-e2e`
   Use `E2E_TESTS=<path>` for focused e2e validation.
7. repo-native CI parity: `make check`
8. full CI parity: `make ci`
9. OpenAPI gate: `make openapi-gate`
10. architecture boundary gate: `make architecture-boundary-gate`
11. architecture report: `make architecture-boundary-report`
12. quality scorecard refresh: `make quality-baseline`
13. CI contract gate: `make ci-contract-gate`
14. repository hygiene gate: `make repository-hygiene-gate`
15. maintainability gate: `make maintainability-gate`
16. documentation contract gate: `make documentation-contract-gate`
17. quality scorecard gate: `make quality-scorecard-gate`
18. monetary float guard: `make monetary-float-guard`
19. no-sensitive-content guard: `make no-sensitive-content-guard`
20. source-observability contract gate:
    `make source-observability-contract-gate`
21. operation metric contract gate:
    `make operation-metric-contract-gate`
22. AI model-risk operations contract gate:
    `make ai-model-risk-ops-contract-gate`
23. AI model-risk operations proof gate:
    `make ai-model-risk-operations-proof-contract-gate`
24. implementation-truth gate: `make implementation-truth-gate`
25. data-mesh contract gate: `make data-mesh-contract-gate`
26. opportunity archetype contract gate:
    `make opportunity-archetype-contract-gate`
27. downstream realization contract gate:
    `make downstream-realization-contract-gate`
28. downstream route proof contract gate:
    `make downstream-route-contract-proof-gate`
29. migration contract gate: `make migration-contract-gate`
30. migration execution dry-run gate: `make migration-execution-gate`
31. durable repository proof contract gate:
    `make durable-repository-proof-contract-gate`
32. runtime trust telemetry proof contract gate:
    `make runtime-trust-telemetry-proof-contract-gate`
33. report-intake route proof contract gate:
    `make report-intake-route-proof-contract-gate`
34. report materialization proof contract gate:
    `make report-materialization-proof-contract-gate`
35. Workbench read-path proof contract gate:
    `make workbench-read-path-proof-contract-gate`
36. Gateway/Workbench operational proof contract gate:
    `make gateway-workbench-operational-proof-contract-gate`
37. Gateway/Workbench discovery proof contract gate:
    `make gateway-workbench-discovery-proof-contract-gate`
38. run-once source-ingestion worker manifest and output-contract gate:
    `make source-ingestion-worker-check`
39. scheduled source-ingestion worker deploy-contract gate:
    `make source-ingestion-scheduled-worker-check`
40. source-ingestion live-proof artifact contract gate:
    `make source-ingestion-live-proof-contract-gate`
41. Risk concentration live-proof artifact contract gate:
    `make risk-concentration-live-proof-contract-gate`
42. High-volatility live-proof artifact contract gate:
    `make high-volatility-live-proof-contract-gate`
43. Performance underperformance live-proof artifact contract gate:
    `make performance-underperformance-live-proof-contract-gate`
44. Core benchmark assignment live-proof artifact contract gate:
    `make core-benchmark-assignment-live-proof-contract-gate`
45. Core portfolio-state live-proof artifact contract gate:
    `make core-portfolio-state-live-proof-contract-gate`
46. Low-income Core cashflow live-proof artifact contract gate:
    `make low-income-core-cashflow-live-proof-contract-gate`
47. AI lineage store proof contract gate:
    `make ai-lineage-store-proof-contract-gate`
48. outbox platform mesh event publication proof contract gate:
    `make outbox-platform-mesh-event-publication-proof-contract-gate`
49. AI workflow-pack registration proof contract gate:
    `make ai-workflow-pack-registration-proof-contract-gate`
50. AI workflow-pack runtime execution proof contract gate:
    `make ai-workflow-pack-runtime-execution-proof-contract-gate`
51. implementation proof readiness generator:
    `make implementation-proof-readiness-check`
    It remains CI-stable by default and can consume live source-proof evidence
    through `LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF`,
    `LOTUS_CORE_QUERY_BASE_URL`, `LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL`,
    `LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF`,
    `LOTUS_ADVISE_ROOT`, `LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT`,
    `LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF`, `LOTUS_MANAGE_ROOT`,
    `LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT`,
    `LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF`,
    `LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF`,
    `LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF`,
    `LOTUS_REPORT_ROOT`, `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT`,
    `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF`,
    `LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF_OUTPUT`,
    `LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF`, `LOTUS_PLATFORM_ROOT`,
    `LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_OUTPUT`,
    `LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF`,
    `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT`,
    `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF`,
    `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT`,
    `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF`,
    `LOTUS_AI_ROOT`,
    `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT`,
    `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF`,
    `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT`,
    `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF`,
    `IMPLEMENTATION_PROOF_EVALUATED_AT_UTC`, and
    `IMPLEMENTATION_PROOF_OUTPUT` when release reviewers are validating against
    a running Core stack or merged sibling route-proof/platform/AI proof
    artifacts. Missing sibling Advise, Manage, Report, platform, or `lotus-ai`
    evidence leaves the generated proof invalid and keeps the corresponding
    blockers.
39. runtime trust telemetry preview generator:
    `make runtime-trust-telemetry-preview-check`
40. runtime trust telemetry snapshot generator:
    `make runtime-trust-telemetry-snapshot-check`
40. PostgreSQL runtime proof with configured integration URL:
    `make postgres-integration-gate`
41. apply migrations with configured PostgreSQL URL: `make migrate`
42. rollback migrations with configured PostgreSQL URL: `make migrate-rollback`
43. remove ignored generated local artifacts: `make clean`

## Validation And CI Expectations

`lotus-idea` follows the standard Lotus backend lane model:

1. feature lane for fast branch feedback,
2. PR merge gate for required merge readiness,
3. main releasability for post-merge truth,
4. merged-PR dispatch so auto-merged PRs still generate release evidence on
   `main`.

Required baseline checks include lint, format check, typecheck, architecture
boundary enforcement, repository hygiene, maintainability thresholds,
documentation contract enforcement, quality-scorecard truth, monetary precision
guarding, no-sensitive-content evidence guarding, source-observability contract
enforcement, operation metric contract enforcement, OpenAPI quality, implementation-truth gate,
supported-feature gate,
endpoint-certification gate, data-mesh contract gate, opportunity archetype
contract gate, migration contract gate, migration execution dry-run gate,
source-ingestion worker manifest and
output-contract validation, scheduled source-ingestion worker deploy-contract
validation, source-ingestion live-proof contract validation,
durable repository proof contract validation,
runtime trust telemetry proof contract validation,
report-intake route proof contract validation,
report materialization proof contract validation,
Workbench read-path proof contract validation,
Gateway/Workbench operational proof contract validation,
Gateway/Workbench discovery proof contract validation,
outbox platform mesh event publication proof contract validation,
AI lineage store proof contract validation,
AI workflow-pack registration proof contract validation,
implementation-proof readiness artifact generation,
runtime trust telemetry preview and snapshot artifact generation,
unit tests, integration tests, e2e tests,
PostgreSQL runtime proof in PR/main GitHub lanes, coverage gate, security audit,
Docker build validation, bounded GitHub job timeouts, and no soft-failed
critical workflow jobs.

`make ci-contract-gate` is blocking through `make lint`. It protects the
bank-buyable lane contract itself so future agentic changes cannot silently
remove architecture, repository-hygiene, maintainability, OpenAPI, endpoint-certification, supported-feature,
data-mesh contract validation, migration contract validation, coverage,
opportunity archetype contract validation,
safe migration execution dry-run validation, source-ingestion worker manifest
and output-contract validation, scheduled source-ingestion worker
deploy-contract validation, no-sensitive-content evidence validation,
durable repository proof contract validation, runtime trust telemetry proof
contract validation, report-intake route proof contract validation, report
materialization proof contract validation, Workbench read-path proof contract
validation, Gateway/Workbench operational proof contract validation, Gateway/Workbench discovery proof contract validation, outbox broker proof contract validation, platform mesh onboarding
proof contract validation, outbox platform mesh event publication proof
contract validation, AI lineage store proof contract validation,
AI workflow-pack registration proof contract validation,
AI model-risk operations proof contract validation, Risk high-volatility and
drawdown live-proof contract validation, Advise mandate/restriction live-proof
contract validation, implementation-proof readiness artifact generation,
runtime trust telemetry preview generation, source-observability contract
validation, PostgreSQL runtime proof, coverage,
security, Docker, release-evidence, verified immutable action SHA pins with
version provenance comments, least-privilege workflow controls, bounded
workflow timeouts, no `continue-on-error: true` in critical lanes,
implementation-truth enforcement, non-suppressed auto-merge token usage,
workflow-dispatch access, repo-native GitHub test and coverage target usage,
or merged-PR main-releasability dispatch from local or GitHub validation. Unit
coverage proves current pass behavior and failure cases for floating action
tags, wrong verified SHAs, missing action-version provenance, raw workflow
`pytest` shortcuts, weakened coverage-target selectors, and removal of current
blocking lint gates from the repo-native quality path.

`make repository-hygiene-gate` is blocking through `make lint`. It scans
tracked Git files and fails if generated Python cache files, local coverage
artifacts, build outputs, dependency directories, local environment files, log
files, or local database files are committed. This preserves a clean
bank-buyable source boundary: durable implementation, contract, test, evidence,
and documentation truth belongs in Git; local runtime byproducts do not.
`make clean` removes ignored local test, coverage, build, HTML coverage, and
Python bytecode cache residue through `scripts/clean_generated_artifacts.py`
without traversing `.git`, `.venv`, or dependency cache directories.
`make ci-contract-gate` requires the Makefile cleanup target to use that script
so future agentic cleanup changes remain reviewable and test-backed.

`make maintainability-gate` is blocking through `make lint`. It enforces the
current measured enterprise-quality thresholds for Python size hotspots:
source files must stay at or below 1200 lines, source functions at or below
130 lines, test files at or below 1200 lines, test functions at or below 180
lines, script files at or below 500 lines, and script functions at or below
120 lines. These limits are intentionally conservative against the current
baseline and prevent future agentic changes from normalizing large, hard-to-review
modules.

`make documentation-contract-gate` is blocking through `make lint`. It protects
the durable agent and operator context surface: `AGENTS.md`, `README.md`,
`REPOSITORY-ENGINEERING-CONTEXT.md`, RFC index, enterprise standard, operations
runbooks, demo operating process, demo pack template, quality evidence, RFC
implementation evidence guide, and wiki source must remain present,
substantive, and anchored to validation and governance commands. The gate also
enforces a polished
operator-document profile for proof, readiness, and client-demo guides:
current-truth tables, explicit proof and non-proof boundaries, blocker
sections, response-shape tables, evidence references, claim-state discipline,
client-friendly explanation, Mermaid flow diagrams, and executable examples.
This gate complements implementation-truth enforcement: it prevents deletion,
hollowing-out, and text-dump erosion of context, while implementation-truth
prevents overclaiming unsupported product posture.

`make quality-scorecard-gate` is blocking through `make lint`. It protects the
bank-buyable control matrix from drift by requiring the standard control rows,
approved readiness statuses, non-empty evidence/gap/next-slice cells,
implementation-backed evidence anchors, and stale scaffold-era underclaim
detection after internal API, persistence, observability, and test foundations
land.

`make monetary-float-guard` is blocking through `make lint`. It uses AST-backed
checks to fail money-like `float` annotations, literals, and conversions across
`src` while allowing non-monetary operational float usage such as timeout
seconds. This keeps Lotus Idea aligned to the financial precision posture from
the first implementation slices.

`make no-sensitive-content-guard` is blocking through `make lint`. It scans
local evidence, log, and output artifacts for forbidden sensitive marker names
including portfolio, client, account, holding, transaction, request-body,
response-body, and raw entitlement failure markers. The guard has focused
pass/fail unit coverage so future agents cannot leave untested artifact-leak
checks in the merge path.

`make source-observability-contract-gate` is blocking through `make lint`. It
scans application source and fails raw `print()`, direct Python logging imports
or calls, and low-level `log_event` bypasses outside the central observability
module. Feature code should emit bounded operation events or use the central
request diagnostic helper so supportability evidence stays product-safe and
low-cardinality.

`make signal-api-contract-gate` is blocking through `make lint`. It scans the
caller-supplied signal API modules and fails local copies of signal-evaluation
permission policy or signal outcome mapping, and requires shared signal API
support for permission, source-authority, operation-event, and problem-detail
behavior. It also requires every signal evaluation route metadata block to
compose the shared product-safe 400/403 `ProblemDetails` OpenAPI examples from
`signal_problem_responses()`. This keeps design modularity inside `lotus-idea`
without creating a new runtime microservice boundary.

Workflow and operator route modules should use `src/app/api/problem_details.py`
for shared product-safe RFC-7807 OpenAPI response metadata and common
permission/request-failure helpers. Keep route-specific error codes and
descriptions in the route module, but do not hand-roll duplicate
`ProblemDetails` shapes for lifecycle, review, feedback, conversion,
report-evidence, or readiness/operator APIs. This is design modularity only; it
does not imply a separately scalable `lotus-idea` sub-service.

`make operation-metric-contract-gate` is blocking through `make lint`. It
validates `contracts/observability/lotus-idea-operation-metrics.v1.json`
against code-owned operation, outcome, supportability, and metric-label
vocabulary, and blocks sensitive labels plus premature dashboard, alert, mesh,
Gateway/Workbench, or supported-feature certification claims.

`make ai-model-risk-ops-contract-gate` is blocking through `make lint`. It
validates
`contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`
against implemented AI explanation and AI readiness operation telemetry,
required model-risk dashboard controls, required alert rules, source-of-truth
paths, and explicit non-proof boundaries.

`make ai-model-risk-operations-proof-contract-gate` is blocking through
`make lint`. It validates the source-safe dashboard, Prometheus alert rules,
and model-risk operations runbook against implemented
`lotus_idea_operation_events_total` telemetry. It clears only model-risk
dashboard/alert operations blockers; it does not certify `lotus-ai` runtime
execution, AI lineage store, Workbench surface, data-mesh certification, or
supported-feature promotion.

`make ai-lineage-store-proof-contract-gate` is blocking through `make lint`.
It validates the source-safe AI lineage store proof artifact that aggregate
implementation-proof readiness consumes to clear only
`certified_ai_lineage_store_missing`. The gate blocks prompt, provider
response, candidate, portfolio, client, database URL, request-body, and
response-body leakage, and preserves the no-`lotus-ai`-runtime,
no-model-risk-dashboard, no-Workbench, no-client-ready-publication, and
no-supported-feature-promotion boundaries.

`make ai-workflow-pack-registration-proof-contract-gate` is blocking through
`make lint`. It validates the source-safe sibling `lotus-ai` workflow-pack
registration proof artifact that aggregate implementation-proof readiness
consumes to clear only `workflow_pack_runtime_contract_not_certified`. The
gate verifies registry seed, phase-one spec, execution binding, queue policy,
supportability surface, and test evidence for `idea_explanation.pack@v1`, while
preserving the no-`lotus-ai`-runtime, no-provider-call, no-model-risk-dashboard,
no-Workbench, no-client-ready-publication, and no-supported-feature-promotion
boundaries.

`make implementation-truth-gate` is blocking through `make lint`. It scans the
durable current-state surfaces (`README.md`, repository context, operations and
demo docs, quality docs, and wiki source) and fails unqualified claims of demo
readiness, production readiness, external support, certification, live source
ingestion, Gateway/Workbench support, or client-ready publication while the
supported-feature registry has no implemented features. RFC target-state
planning text is intentionally excluded; current-state surfaces must use
explicit blocked, planned, unsupported, not-yet, or evidence-required wording.
The same gate also fails stale scaffold-era underclaims in current-state demo
documentation when they conflict with repository evidence, including claims
that no business workflow exists after internal APIs are certified or that
architecture-boundary enforcement remains report-only after the
`architecture-boundary-gate` target is blocking.

`make endpoint-certification-gate` is blocking through `make lint`. It now
validates more than ledger presence: public OpenAPI operations must stay
synchronized with `docs/operations/endpoint-certification-ledger.json`, JSON
examples must parse, test references must resolve to real pytest functions,
baseline health/metadata routes must use `baseline_certified`, and certified
business/operator endpoints must name an `idea.*` capability, document
product-safe 403 behavior, preserve Gateway and Workbench boundaries, preserve
the no-supported-feature-promotion boundary, reference
`scripts/openapi_quality_gate.py` evidence, and cite bounded operation-event
test evidence before remaining `certified`. Certified business/operator
endpoints must also cite at least one non-operation-event integration API
behavior test and at least one negative or degraded-path test. This keeps API
certification aligned to the test pyramid and prevents schema-only, unit-only,
or telemetry-only evidence from being treated as implementation proof.
For endpoints with implemented bounded read-only Gateway publication, the same
gate also requires `docs/operations/endpoint-certification-ledger.json` to name
the exact `lotus-gateway` route and to keep Workbench proof, data-product
certification, client-ready publication, and supported-feature promotion
explicitly out of scope.

Every RFC slice that exposes behavior must update endpoint certification,
supported-feature registration, docs/wiki truth, observability, and regression
tests in the same change.

Data-mesh declarations are repo-owned from day one, but certification remains
`not_certified` until implementation-backed products emit runtime telemetry,
the platform source manifest includes `lotus-idea`, and platform mesh gates pass.
The repo-native data-mesh contract gate is a pre-certification anti-drift guard:
it is not platform certification and must not be used to promote supported mesh
claims.

`lotus-idea` adopts
`lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`
from day one. Treat the contract as a merge-time obligation, not a later
hardening theme: dependency hygiene, source-authority discipline, supported
claims, CI evidence, docs/wiki truth, and operational supportability must move
with each implementation slice.

## Standards And RFCs That Govern This Repository

1. `lotus-platform/rfcs/RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md`
2. `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`
3. `lotus-platform/context/playbooks/ENTERPRISE-BACKEND-REFACTORING-INSTRUCTIONS.md`
4. `docs/architecture/adr/ADR-0001-lotus-idea-service-boundary.md`
5. `docs/architecture/adr/ADR-0002-scaffold-and-repository-foundation.md`
6. `docs/architecture/adr/ADR-0003-source-authority-and-data-mesh-boundaries.md`
7. `docs/architecture/adr/ADR-0004-ai-assisted-human-governed-decision-support.md`
8. `docs/rfcs/README.md`

## Known Constraints And Implementation Notes

1. This repository is currently a governed scaffold and RFC foundation.
2. Demo claims must remain planned until implemented and certified.
3. Idea scoring must be deterministic and explainable before AI enhancement.
4. AI output must be advisory assistance, never an autonomous suitability,
   compliance, mandate, execution, or client-communication decision.
5. Every idea must carry source evidence, source timestamps, calculation
   provenance, lifecycle status, expiry behavior, and review outcome.
6. Overlap with `lotus-risk` must be resolved by source authority: risk owns risk
   analytics and risk events; `lotus-idea` owns cross-domain opportunity
   lifecycle and review orchestration.
7. Overlap with `lotus-advise` must be resolved by workflow authority: advise
   owns proposal/suitability workflows; `lotus-idea` owns candidate opportunity
   intelligence before conversion.
8. Overlap with `lotus-manage` must be resolved by implementation authority:
   manage owns model/rebalance/action workflows; `lotus-idea` owns opportunity
   queue and conversion intent.

## Context Maintenance Rule

Update this document when:

1. repository ownership changes,
2. idea domain authority changes,
3. repo-native commands or CI gates change,
4. runtime or integration boundaries change,
5. data-product contracts change,
6. supported features become implementation-backed,
7. dominant local implementation patterns change,
8. current-state rollout or product posture materially changes.

## Cross-Links

1. `lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `lotus-platform/context/CONTEXT-REFERENCE-MAP.md`
4. `lotus-platform/context/LOTUS-SKILL-ROUTING-MAP.md`
5. `lotus-platform/context/playbooks/ENTERPRISE-BACKEND-REFACTORING-INSTRUCTIONS.md`
6. `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`

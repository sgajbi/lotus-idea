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

RFC-0002 Slice 05 is partially implemented for the high-cash / idle-liquidity
domain policy and the first Core source-port foundation.
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
foundation behavior. `src/app/application/source_ingestion.py`
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
stale aggregate `runtime_candidate_snapshot_missing` blocker; platform mesh,
Gateway/Workbench, and supported-feature blockers remain.
It also generates a source-safe Workbench read-path proof artifact under
ignored `output/workbench/` and passes it into aggregate proof-readiness
generation. That artifact records the bounded Gateway-backed Workbench queue
and detail read implementation and clears only
`workbench_gateway_bff_consumption_proof_missing`; full panel, accessibility,
canonical demo runtime, data-product, and supported-feature blockers remain.
It also generates a source-safe `lotus-report` intake route proof artifact
under ignored `output/downstream/` from the sibling checkout configured by
`LOTUS_REPORT_ROOT`, then passes the artifact into aggregate proof-readiness
generation unless `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF` overrides it. A valid
artifact records the merged `POST /reports/idea-evidence-packs` route
foundation and clears only `lotus_report_live_intake_route_proof_missing`;
missing sibling evidence writes an invalid non-proof artifact and keeps the
blocker. Report materialization, render output, archive record, client
publication, and supported-feature blockers remain.
It also generates a source-safe platform mesh onboarding proof artifact under
ignored `output/data-mesh/` from the sibling checkout configured by
`LOTUS_PLATFORM_ROOT`, then passes the artifact into aggregate proof-readiness
generation unless `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF` overrides it. A
valid artifact clears only `platform_source_manifest_inclusion_missing` and
`platform_catalog_inclusion_missing`; missing sibling evidence writes an
invalid non-proof artifact and keeps the corresponding blockers. Mesh
certification, active producer products, SLO/access/evidence certification,
Gateway/Workbench discovery, and supported-feature blockers remain.
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
through `LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF` can clear only the
`live_core_source_proof_missing` blocker in the source-ingestion readiness
diagnostic. `make source-ingestion-live-proof-contract-gate` blocks proof
payload shape drift, source-sensitive fields, missing aggregate block
diagnostics, and accidental support promotion.
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
broker publication until platform mesh event certification and downstream
consumer contracts exist.
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
configuration/runtime-proof blockers. The artifact cites implemented adapter
and API proof, blocks source-sensitive event and payload content, and preserves
downstream consumer, platform mesh event, Gateway/Workbench, and
supported-feature blockers.
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
execution, prompt/RAG/provider integration, certified AI lineage-store proof,
certified model-risk dashboard/alert evidence, Workbench proof, trust
telemetry, or supported-feature promotion exists. The repo-owned AI
model-risk operations contract is enforced by
`make ai-model-risk-ops-contract-gate`, but it is explicitly not dashboard,
alert, `lotus-ai`, Workbench, or supported-feature certification.
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
clearing only the Report route blocker. `make downstream-realization-contract-gate` blocks premature
downstream-execution, supported-feature, and source-authority drift in that
contract plan. The endpoint emits bounded
`downstream_realization_readiness_read` operation events and does not call
downstream services, create Report packages, render output, archive records,
or promote downstream realization.
`scripts/generate_implementation_proof_readiness.py` and
`make implementation-proof-readiness-check` now provide the same source-safe
proof-readiness snapshot as repo-native automation evidence for CI, async runs,
and operator handoff. The generator accepts explicit source-ingestion manifest,
live-proof, scheduled-worker proof, durable repository proof, runtime trust
telemetry proof, report-intake route proof, and Workbench read-path proof paths
for deterministic CI evidence without requiring ambient process environment
mutation. The Makefile generates the default report-intake route proof under
ignored `output/downstream/` and keeps CI stable when sibling `lotus-report`
evidence is absent by preserving the downstream blocker instead of failing the
aggregate proof snapshot. The
source-ingestion capability evidence includes validated source-ingestion
live-proof and scheduled-worker deploy-proof artifact refs when the
corresponding blockers are cleared.
The AI explanation capability evidence includes the AI model-risk operations
contract and gate refs so release reviewers can see the not-certified
dashboard-control and alert-candidate posture without clearing model-risk
dashboard or alert blockers.
The live operator API also consumes configured source-ingestion live,
source-ingestion scheduled-worker, durable repository, runtime trust telemetry,
Workbench read-path, and report-intake route proof artifact paths through
`LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF`,
`LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_PROOF`,
`LOTUS_IDEA_DURABLE_REPOSITORY_PROOF`,
`LOTUS_IDEA_RUNTIME_TRUST_TELEMETRY_PROOF`,
`LOTUS_IDEA_WORKBENCH_READ_PATH_PROOF`, and
`LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF`. The repo-native Makefile default
generates `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT` from `LOTUS_REPORT_ROOT`
and consumes that artifact when no override is set, clearing only the matching
aggregate proof blockers while preserving all certification and
support-promotion blockers.

RFC-0002 Slice 10 is partially implemented as certified internal API
foundation plus bounded read-only Gateway publication for advisor queue and
candidate detail. `POST /api/v1/idea-signals/high-cash/evaluate` accepts
caller-supplied, source-owned Core evidence references and source-reported cash
weight, enforces `idea.signal.evaluate` capability or advisor role, and returns
deterministic candidate, blocked, suppressed, or not-eligible posture.
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
proof exists only inside the opt-in runtime proof; there is no certified live
`lotus-report` idea evidence-pack intake route or materialization proof, no
`lotus-render` deterministic output, no
`lotus-archive` metadata or access-audit record, no client-ready publication
authority, no Gateway/Workbench proof, no data-product certification, no runtime
trust telemetry, and no supported-feature promotion.

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
`docs/demo/client-demo-operating-process.md`,
`docs/demo/client-facing-lotus-idea-brief.md`,
`docs/demo/client-demo-pack.template.md`, and `wiki/Demo-Readiness.md` now
define the app-specific client-demo process, client-facing business narrative,
claim states, client-pack versus internal-evidence separation, evidence pack
template, validation commands, acceptance checklist, rehearsal/follow-up
discipline, and do-not-claim boundaries. The process is governed documentation
truth only; it does not promote external demo readiness, supported features,
downstream materialization, client publication, or certified data-mesh status.

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
   endpoint certification and metrics instrumentation remain compatible.
3. `src/app/runtime/`: process-local dependency composition for repositories,
   source adapters, outbox publishers, and downstream realization clients. The
   repository provider is process-local in-memory by default and
   PostgreSQL-backed when `LOTUS_IDEA_DATABASE_URL` is configured. API routes,
   workers, and proof generators depend on this package for runtime wiring
   instead of placing state providers in the API layer or app root.
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
   bounded broker proof artifact, bounded report-intake route proof artifact,
   Workbench, downstream realization, and supported-feature promotion without
   leaking source payloads, event identifiers, broker payloads, or promoting
   support.
4. `src/app/domain/`: framework-free idea models, lifecycle rules, scoring
   policies, review-queue projection, review governance, AI governance,
   conversion governance, report evidence-pack request governance, evidence
   policy, deterministic governance checks, internal persistence records,
   replay posture, idempotency, audit primitives, source-safe outbox records,
   and retry/dead-letter delivery state semantics.
5. `src/app/ports/`: interfaces to `lotus-core`, `lotus-performance`,
   `lotus-risk`, `lotus-advise`, `lotus-manage`, `lotus-report`, and `lotus-ai`.
   `idea_repository.py` owns the central repository workflow protocols used by
   application orchestration, and `core_sources.py` owns the high-cash Core
   evidence port.
6. `src/app/infrastructure/`: HTTP/database/message adapters behind ports. The
   current Core adapter preserves source-data product refs and requires Core to
   report cash weight explicitly rather than deriving it locally. The layer also
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
23. implementation-truth gate: `make implementation-truth-gate`
24. data-mesh contract gate: `make data-mesh-contract-gate`
25. downstream realization contract gate:
    `make downstream-realization-contract-gate`
26. migration contract gate: `make migration-contract-gate`
27. migration execution dry-run gate: `make migration-execution-gate`
28. durable repository proof contract gate:
    `make durable-repository-proof-contract-gate`
29. runtime trust telemetry proof contract gate:
    `make runtime-trust-telemetry-proof-contract-gate`
30. report-intake route proof contract gate:
    `make report-intake-route-proof-contract-gate`
31. Workbench read-path proof contract gate:
    `make workbench-read-path-proof-contract-gate`
32. run-once source-ingestion worker manifest and output-contract gate:
    `make source-ingestion-worker-check`
33. scheduled source-ingestion worker deploy-contract gate:
    `make source-ingestion-scheduled-worker-check`
34. source-ingestion live-proof artifact contract gate:
    `make source-ingestion-live-proof-contract-gate`
35. implementation proof readiness generator:
    `make implementation-proof-readiness-check`
    It remains CI-stable by default and can consume live source-proof evidence
    through `LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF`,
    `LOTUS_CORE_QUERY_BASE_URL`, `LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL`,
    `LOTUS_REPORT_ROOT`, `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT`,
    `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF`, `LOTUS_PLATFORM_ROOT`,
    `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT`,
    `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF`,
    `IMPLEMENTATION_PROOF_EVALUATED_AT_UTC`, and
    `IMPLEMENTATION_PROOF_OUTPUT` when release reviewers are validating against
    a running Core stack or merged sibling route-proof/platform proof
    artifacts. Missing sibling report or platform evidence leaves the generated
    proof invalid and keeps the corresponding blockers.
36. runtime trust telemetry preview generator:
    `make runtime-trust-telemetry-preview-check`
37. runtime trust telemetry snapshot generator:
    `make runtime-trust-telemetry-snapshot-check`
38. PostgreSQL runtime proof with configured integration URL:
    `make postgres-integration-gate`
39. apply migrations with configured PostgreSQL URL: `make migrate`
38. rollback migrations with configured PostgreSQL URL: `make migrate-rollback`
39. remove ignored generated local artifacts: `make clean`

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
endpoint-certification gate, data-mesh contract gate, migration contract gate,
migration execution dry-run gate, source-ingestion worker manifest and
output-contract validation, scheduled source-ingestion worker deploy-contract
validation, source-ingestion live-proof contract validation,
durable repository proof contract validation,
runtime trust telemetry proof contract validation,
report-intake route proof contract validation,
Workbench read-path proof contract validation,
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
safe migration execution dry-run validation, source-ingestion worker manifest
and output-contract validation, scheduled source-ingestion worker
deploy-contract validation, no-sensitive-content evidence validation,
durable repository proof contract validation, source-observability contract
validation, PostgreSQL runtime proof, coverage,
security, Docker, release-evidence, verified immutable action SHA pins with
version provenance comments, least-privilege workflow controls, bounded
workflow timeouts, no `continue-on-error: true` in critical lanes,
implementation-truth enforcement, non-suppressed auto-merge token usage,
workflow-dispatch access, or merged-PR main-releasability dispatch from local
or GitHub validation. Unit coverage proves current pass behavior and failure
cases for floating action tags, wrong verified SHAs, and missing action-version
provenance.

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

`make operation-metric-contract-gate` is blocking through `make lint`. It
validates `contracts/observability/lotus-idea-operation-metrics.v1.json`
against code-owned operation, outcome, supportability, and metric-label
vocabulary, and blocks sensitive labels plus premature dashboard, alert, mesh,
Gateway/Workbench, or supported-feature certification claims.

`make ai-model-risk-ops-contract-gate` is blocking through `make lint`. It
validates
`contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`
against implemented AI explanation and AI readiness operation telemetry,
required model-risk dashboard controls, required alert candidates, source-of-
truth paths, and explicit non-proof boundaries. It narrows the prior
model-risk operations gap from missing contract to not-certified contract
posture; it does not certify a dashboard, alert, `lotus-ai` runtime execution,
AI lineage store, Workbench surface, or supported feature.

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
test evidence before remaining `certified`.
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

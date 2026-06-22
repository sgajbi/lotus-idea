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
idle liquidity is the first opportunity family, `PB_SG_GLOBAL_BAL_001` is the
canonical first proof portfolio, advisor-only review is the first audience,
report-only evidence is the first downstream conversion path, and missing
evidence / unsupported-claim verification is the first AI posture. The baseline
keeps all source calculations in their owning services and does not promote any
business capability beyond the current foundation-only supported-feature state.

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
`src/app/repository_state.py`, with `src/app/api/repository_state.py` retained
as a compatibility shim. This is structural cleanup only and does not promote a
supported business feature.

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
refs and fails closed when Core omits a source-reported cash-weight field; it
does not calculate cash weight from cash totals or market values. This remains
internal source-adapter foundation behavior. `src/app/application/source_ingestion.py`
now adds an internal high-cash source-ingestion orchestration wrapper over the
Core source port and repository port, including generated source-ingestion
idempotency keys and explicit accepted, replayed, conflict, blocked,
suppressed, and skipped-not-eligible decisions. There is still no live Core
integration proof, scheduled database-backed source-ingestion worker, Gateway
route, Workbench proof, data-product certification, or supported-feature
promotion yet.
The upstream Core cash-weight contract dependency is tracked in
`sgajbi/lotus-core#430`.

RFC-0002 Slice 06 is partially implemented as an internal persistence
foundation in `src/app/domain/persistence.py`. The repository now has immutable
candidate persistence records, deterministic source-ref evidence hashes,
idempotent candidate persistence decisions, duplicate candidate suppression,
evidence replay posture for matched, stale, mismatched, expired, and missing
records, idempotent lifecycle-transition recording, lifecycle-transition
history, conversion intent/outcome records, conversion intent lookup, report
evidence-pack request records, safe audit events for mutating actions, snapshot
recovery for internal replay tests,
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
`src/app/ports/idea_repository.py` now centralizes the repository workflow
protocols for candidate snapshots, persistence, lifecycle, review and feedback,
conversion, report evidence-pack requests, and AI explanation reads. Application
use cases must depend on that port instead of defining local repository
protocols; `tests/unit/test_repository_port_boundary.py` enforces the boundary
so the future durable adapter has one governed contract surface.
`migrations/001_idea_repository_foundation.sql` and its rollback file now define
the first versioned schema contract for database-backed candidate,
idempotency, lifecycle, audit, review, feedback, conversion, and report
evidence-pack state. `make migration-contract-gate` blocks missing schema
objects, missing indexes, missing rollback posture, or placeholder SQL.
`src/app/infrastructure/migrations.py` and `scripts/run_migrations.py` now add
the first PostgreSQL migration execution path, with `make migration-execution-gate`
dry-running apply and rollback plans in CI, and `make migrate` /
`make migrate-rollback` requiring `LOTUS_IDEA_DATABASE_URL` for real execution.
`src/app/infrastructure/postgres_repository.py` now adds the first tested
PostgreSQL repository adapter over the governed repository port surface. It
round-trips candidate, idempotency, lifecycle, audit, review, feedback,
conversion, and report evidence-pack state through typed tables and JSONB
snapshots, and rolls back on database flush failure.
`src/app/repository_state.py` now wires the adapter into API runtime
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
storage certification: deploy migration evidence, scheduled source-ingestion
worker proof, live Core source adapter proof, data-product certification,
downstream workflow proof, and supported-feature promotion remain planned.

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
foundation in `src/app/api/review_queues.py`; and golden unit/integration
coverage for expected ordering and edge cases. This is not yet a supported
queue product: no database-backed queue state, Gateway/Workbench proof,
entitlement-backed scope filtering, data-product certification, trust
telemetry, or supported-feature promotion exists.

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
`lotusAiRuntimeExecuted=false`, and `supportedFeaturePromoted=false`. This is
not yet a supported AI explanation product: no `lotus-ai` runtime workflow
execution, prompt/RAG/provider integration, durable AI lineage store,
Gateway/Workbench proof, trust telemetry, model-risk operations dashboard, or
supported-feature promotion exists.

RFC-0002 Slice 10 is partially implemented as certified internal API
foundation. `POST /api/v1/idea-signals/high-cash/evaluate` accepts
caller-supplied, source-owned Core evidence references and source-reported cash
weight, enforces `idea.signal.evaluate` capability or advisor role, and returns
deterministic candidate, blocked, suppressed, or not-eligible posture.
`POST /api/v1/idea-signals/high-cash/evaluate-and-persist` uses the same source
evidence contract, requires `idea.candidate.persist` plus `Idempotency-Key`,
and persists created candidates through the internal in-memory
idempotency/audit repository foundation with accepted, replayed, duplicate, or
conflict posture. `GET /api/v1/review-queues/advisor` exposes deterministic
advisor queue projection over persisted candidate snapshots. The review-action
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
runtime workflows, persist durable AI lineage, or grant downstream authority.
All ten business routes plus the data-mesh-readiness operator diagnostic are
covered by OpenAPI and endpoint certification evidence. The PostgreSQL runtime
proof now covers the high-cash persist, advisor queue, lifecycle, review,
feedback, conversion intent/outcome, and report evidence-pack request path.
This is not yet a supported product capability: there are no live source
adapters, Gateway routes, Workbench surfaces, supported database-backed API
state beyond the current opt-in PostgreSQL workflow proof, data-product
certification, runtime trust telemetry, or supported-feature promotion.

RFC-0002 Slice 12 is partially implemented as an internal conversion governance
foundation in `src/app/domain/conversion_governance.py`. The repository now has
review-gated conversion intent creation for Advise proposal, Manage review, and
Report evidence targets; target-to-source-authority mapping; lifecycle
transition to converted posture; downstream outcome recording; safe audit
events; idempotency-key validation at the domain command boundary; repository
idempotency and snapshot lookup for conversion intents/outcomes; certified
internal conversion intent/outcome APIs; and explicit no-authority semantics
for execution, suitability, client communication, and downstream realization.
This is not yet a supported conversion product: PostgreSQL-backed internal
conversion intent/outcome recording proof exists only inside the opt-in runtime
proof; there are no downstream adapters, Gateway/Workbench proof,
Advise/Manage/Report acceptance tests, data-product certification, runtime
trust telemetry, or supported-feature promotion.

RFC-0002 Slice 13 is partially implemented as an internal report evidence-pack
request foundation in `src/app/domain/report_evidence.py`. The repository now
has report conversion-intent gating, evidence-hash reconciliation, safe source
summary projection, Report/Render/Archive source-authority refs, retention
policy references, idempotent repository persistence, safe audit events, and a
certified internal API for report evidence-pack requests. This is not yet a
supported report evidence product: PostgreSQL-backed internal request recording
proof exists only inside the opt-in runtime proof; there is no `lotus-report`
package intake adapter, no `lotus-render` deterministic output, no
`lotus-archive` metadata or access-audit record, no client-ready publication
authority, no Gateway/Workbench proof, no data-product certification, no runtime
trust telemetry, and no supported-feature promotion.

RFC-0002 Slice 14 is partially implemented as an internal data-mesh-readiness
diagnostic foundation. `src/app/application/data_mesh_readiness.py` reads
repo-owned producer, mesh-readiness, and trust-telemetry contracts, and
`GET /api/v1/data-mesh/readiness` exposes the current operator-facing
`planned` / `not_certified` posture with explicit blockers. The endpoint
requires `idea.mesh.readiness.read` plus the `operator` role, emits a bounded
`mesh_readiness_read` operation event with `not_certified` supportability, and
returns `supportedFeaturePromoted=false`. This is endpoint-certified diagnostic
evidence only; it is not data-product certification, platform source-manifest
inclusion, Gateway/Workbench discovery, runtime lineage proof, or supported
mesh promotion.

RFC-0002 Slice 15 is partially implemented as a bounded operation observability
foundation. `src/app/observability/logging.py` now defines the
`lotus_idea_operation_events_total` metric, bounded operation/outcome/
supportability vocabulary, product-safe structured operation logs, and
sensitive operation-attribute rejection. High-cash evaluation, candidate
persistence, lifecycle transition, advisor review queue, review action,
AI explanation, feedback, conversion intent, conversion outcome, report
evidence-pack request, and data-mesh-readiness diagnostic APIs emit bounded
operation events without
portfolio/client/account/holding/transaction identifiers, request/response
bodies, trace ids, or correlation ids as metric labels. This is not yet full
production observability: live AI runtime telemetry, live source readiness,
dashboard/alert, Gateway entitlement, durable persistence, data-product
certification, and supported-feature promotion remain planned.

RFC-0002 Slice 18 is partially implemented for documentation and agent context
truth. `docs/operations/api-certification.md` now summarizes the full certified
internal foundation endpoint inventory from
`docs/operations/endpoint-certification-ledger.json`, including each endpoint's
foundation scope, required capability, and unsupported boundary. This keeps
operator-facing documentation aligned with endpoint certification evidence
without promoting any supported business feature.

## CI And Merge Governance

`lotus-idea` follows the Lotus rebase-only PR completion model. Do not squash
RFC, workflow, scaffold, or implementation commits; keep small commits linear
and let branch protection require the PR merge gate before `main` updates.
Rebase auto-merge is allowed only when `LOTUS_AUTOMERGE_TOKEN` is configured so
the merge actor is not the suppressed workflow `GITHUB_TOKEN`. Merged PRs must
explicitly dispatch the Main Releasability Gate so post-merge truth does not
depend only on a push-triggered workflow. After every merge, delete the remote
feature branch and the matching local feature branch, then re-run branch hygiene
before final closure. Durable
RFC/docs/wiki/context/contract truth is complete only when it is present on
`main`, published where required, and not stranded on a side branch.

Coverage aggregation jobs use the current approved `actions/download-artifact`
major and suppress its upstream Node deprecation noise with
`NODE_OPTIONS=--no-deprecation`. Do not downgrade action majors to quiet runner
logs; fix or document the owned warning source instead.

## Architecture And Module Map

1. `src/app/main.py`: application entrypoint, health, readiness, metadata, and
   OpenAPI surface.
2. `src/app/api/`: route modules, DTO mapping, and API-facing process state
   providers. Routes must expose explicit idea contracts and must not embed
   domain logic. Current business routes are registered directly on the FastAPI
   app before Prometheus instrumentation so endpoint certification and metrics
   instrumentation remain compatible. `app.repository_state` owns the API
   repository provider at the composition root: process-local in-memory by
   default, PostgreSQL-backed when `LOTUS_IDEA_DATABASE_URL` is configured. The
   `app.api.repository_state` shim preserves existing route/test imports without
   importing concrete infrastructure into the API layer.
3. `src/app/application/`: use-case orchestration, source aggregation, and
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
   Report/Render/Archive realization.
4. `src/app/domain/`: framework-free idea models, lifecycle rules, scoring
   policies, review-queue projection, review governance, AI governance,
   conversion governance, report evidence-pack request governance, evidence
   policy, deterministic governance checks, internal persistence records,
   replay posture, idempotency, and audit primitives.
5. `src/app/ports/`: interfaces to `lotus-core`, `lotus-performance`,
   `lotus-risk`, `lotus-advise`, `lotus-manage`, `lotus-report`, and `lotus-ai`.
   `idea_repository.py` owns the central repository workflow protocols used by
   application orchestration, and `core_sources.py` owns the high-cash Core
   evidence port.
6. `src/app/infrastructure/`: HTTP/database/message adapters behind ports. The
   current Core adapter preserves source-data product refs and requires Core to
   report cash weight explicitly rather than deriving it locally. The layer also
   contains migration execution helpers and `PostgresIdeaRepository`, which is
   tested as a durable repository adapter and selected by API runtime wiring
   when `LOTUS_IDEA_DATABASE_URL` is configured.
7. `src/app/observability/`: correlation, logging, tracing, metrics, bounded
   idea operation events, safe metric-label policy, and audit event helpers.
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
5. integration tests: `make test-integration`
6. end-to-end tests: `make test-e2e`
7. repo-native CI parity: `make check`
8. full CI parity: `make ci`
9. OpenAPI gate: `make openapi-gate`
10. architecture boundary gate: `make architecture-boundary-gate`
11. architecture report: `make architecture-boundary-report`
12. quality scorecard refresh: `make quality-baseline`
13. CI contract gate: `make ci-contract-gate`
14. maintainability gate: `make maintainability-gate`
15. implementation-truth gate: `make implementation-truth-gate`
16. data-mesh contract gate: `make data-mesh-contract-gate`
17. migration contract gate: `make migration-contract-gate`
18. migration execution dry-run gate: `make migration-execution-gate`
19. PostgreSQL runtime proof with configured integration URL:
    `make postgres-integration-gate`
20. apply migrations with configured PostgreSQL URL: `make migrate`
21. rollback migrations with configured PostgreSQL URL: `make migrate-rollback`

## Validation And CI Expectations

`lotus-idea` follows the standard Lotus backend lane model:

1. feature lane for fast branch feedback,
2. PR merge gate for required merge readiness,
3. main releasability for post-merge truth,
4. merged-PR dispatch so auto-merged PRs still generate release evidence on
   `main`.

Required baseline checks include lint, format check, typecheck, architecture
boundary enforcement, maintainability thresholds, OpenAPI quality, implementation-truth gate,
supported-feature gate,
endpoint-certification gate, data-mesh contract gate, migration contract gate,
migration execution dry-run gate, unit tests, integration tests, e2e tests,
PostgreSQL runtime proof in PR/main GitHub lanes, coverage gate, security audit,
Docker build validation, bounded GitHub job timeouts, and no soft-failed
critical workflow jobs.

`make ci-contract-gate` is blocking through `make lint`. It protects the
bank-buyable lane contract itself so future agentic changes cannot silently
remove architecture, maintainability, OpenAPI, endpoint-certification, supported-feature,
data-mesh contract validation, migration contract validation, coverage,
safe migration execution dry-run validation, PostgreSQL runtime proof, coverage,
security, Docker, release-evidence, action-version, least-privilege workflow
controls, bounded workflow timeouts, no `continue-on-error: true` in critical
lanes, implementation-truth enforcement, non-suppressed auto-merge token usage,
workflow-dispatch access, or merged-PR main-releasability dispatch from local
or GitHub validation.

`make maintainability-gate` is blocking through `make lint`. It enforces the
current measured enterprise-quality thresholds for Python size hotspots:
source files must stay at or below 1200 lines, source functions at or below
130 lines, test files at or below 1200 lines, test functions at or below 180
lines, script files at or below 500 lines, and script functions at or below
120 lines. These limits are intentionally conservative against the current
baseline and prevent future agentic changes from normalizing large, hard-to-review
modules.

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

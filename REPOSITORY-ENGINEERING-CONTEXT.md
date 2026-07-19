# Repository Engineering Context

## Repository Role

`lotus-idea` is the Lotus domain service for private-banking opportunity
intelligence and governed idea lifecycle management.

Service profile: `domain-service`.

Primary runtime: Python FastAPI.

Default local port: `8330`.

This file is the curated repository engineering context. It is not the full
implementation ledger. Detailed slice history belongs in `docs/rfcs/README.md`
and the RFC-0002 slice files.

## Current-State Summary

`lotus-idea` is in RFC-0002 foundation implementation.

The repo-authored product blueprint is `docs/LOTUS_IDEA_BLUEPRINT.md`. Treat it
as the durable anchor for the service product definition, source-authority map,
owned/non-owned capabilities, AI/human-governance posture, and non-claim
boundary. It replaces dependence on a local Downloads-path blueprint during
agent execution, but it is not implementation evidence or supported-feature
promotion by itself.

The repository now contains certified internal API foundations, deterministic
signal policies, caller-supplied evaluation APIs, persistence and migration
support, PostgreSQL repository projections, source-ingestion foundations,
outbox delivery foundations, downstream submission foundations, runtime
readiness diagnostics, implementation-proof artifact generation, GitHub
Security governance, and repo-native CI guardrails.

No externally supported product feature is promoted yet.

Workbench read-path and action-path declarations are v2 `source_contract`
evidence only. The bounded Gateway BFF action family forwards Idea-owned review
actions, feedback, and conversion intents; it must not transfer source,
suitability, restriction, proposal, execution, or supported-feature authority.
Workbench PR `#438` adds an explicit `development_configured` BFF authority
fixture for local, development, and test only. It strips browser-supplied
`X-Caller-*` authority, rejects unallowlisted Idea paths, and fails closed
before Gateway when the environment or authority mode is not explicitly
development. It is not an identity-provider, authenticated-session, or
token-claims implementation; production principal resolution remains tracked
by Workbench `#436`, platform `#563`, and Idea promotion tracker `#380`.
Keep builders, generators, gates, and focused tests under capability-owned
`workbench/` packages. Static files, Make targets, route strings, and historical
PR/SHA references must never clear
`workbench_gateway_bff_consumption_proof_missing`; only machine-verifiable
Gateway serving, Workbench consumption, authenticated entitlement, and browser
evidence may clear that runtime blocker. This is design modularity inside the
existing service, not evidence for a runtime split.

Typed Advise source-product evidence is closed v2 `source_contract` evidence.
Keep shared source-authority loading, digest binding, and validation under
`app.application.advise_source_product_evidence`, with separate
mandate/restriction and missing-risk-profile profiles. A current artifact must
bind the Advise product declaration and trust-telemetry file by repository,
ref, and SHA-256 and must preserve blocked producer telemetry. It may clear
only its named typed-contract blocker. It cannot prove a live Advise call,
risk-profile or suitability approval, policy or proposal approval, mandate
change, restriction clearance, mesh certification, Workbench behavior,
publication, deployment, production certification, or support.

Repo-owned mesh readiness, SLO, access, and evidence-policy declarations are
v2 digest-bound `source_contract` evidence only. Keep their builder, generator,
gate, and focused tests under capability-owned `data_mesh/` packages. A valid
current artifact may add supporting evidence, but it must not clear SLO,
access, or evidence-policy certification blockers without a separately
authority-bound certification artifact. This is design modularity inside the
existing Idea service; it does not justify a runtime split.

Scheduled source-ingestion worker evidence is split by authority class under
`app.application.source_ingestion_scheduler`. Digest-bound entrypoint, Compose,
manifest, and scheduler-configuration declarations are closed
`source_contract` evidence and clear no blocker. Only a matching `deployment`
receipt may clear `scheduled_worker_deploy_proof_missing`; it must bind the
immutable image digest, exact Git SHA, named environment, controller
workflow/run/attempt/actor, workload rollout completion, and exact source
contract/configuration digests. Unknown fields, class substitution, identity
drift, incomplete rollout, and scheduled-execution or production claim
inflation fail closed. This is internal design modularity in the existing Idea
deployable, not justification for another runtime service.

The supported-feature registry remains `foundation_only` with an empty
`features` list. Keep it that way until code, tests, contracts, OpenAPI,
docs/wiki, runtime proof, CI proof, and mainline validation exist for an
implemented feature.

Current internal foundations are real implementation. They are not client-ready
publication, data-product certification, full Gateway/Workbench proof,
downstream execution proof, live source certification, or supported-feature
promotion.

Current implementation includes these bounded foundations:

1. deterministic idea domain vocabulary, lifecycle, review, feedback, scoring,
   evidence, suppression, and conversion-intent models,
2. caller-supplied signal APIs for high cash, concentration risk,
   underperformance, allocation drift / mandate review, bond maturity,
   high volatility, drawdown review, missing suitability, missing risk profile,
   mandate/restriction, low income / liquidity shortfall, and missing
   benchmark review,
3. source-adapter and receipt-bound runtime-evidence foundations for selected
   Core, Risk, Performance, Advise, and Manage evidence families,
4. durable repository support with PostgreSQL migrations and source-safe
   migration rollback/reapply proof,
5. evidence replay, idempotency, safe audit, operation events, and bounded
   problem-details behavior,
6. advisor queue, candidate detail, downstream realization readiness, including
   bounded downstream reconciliation workload, outbox readiness, and runtime
   trust telemetry projections that avoid whole-store snapshot hydration on
   PostgreSQL,
7. downstream conversion/report submission foundations that record local
   submission posture and never grant downstream source authority,
8. source-safe outbox event publication foundations with retry/dead-letter
   state, idempotent operator run-once identity, and a bounded broker
   source-contract proof that never substitutes for external broker runtime
   evidence,
9. AI explanation foundations with deterministic evidence, API-idempotent
   lineage storage, signed Lotus AI run-attestation verification and replay
   protection, model-risk operations evidence, and no provider-runtime
   certification,
10. implementation-proof readiness diagnostics that aggregate blockers instead
    of promoting support.
11. a canonical opportunity-source proof runner that composes existing source
    adapters and proof generators, binds aggregate evidence to source revision,
    correlation, and trace IDs, and fails closed on stale or incomplete source
    evidence without persisting raw child process output.
12. capability-owned closed v2 runtime-evidence packages that call named
    application use cases and bind exact source receipts to deterministic
    outcomes. Shared `runtime_evidence/` code is limited to source-neutral scope,
    identity, hash, and receipt primitives; source authority and schemas remain
    capability-owned. Advise policy families additionally share producer
    workflow qualification and request-envelope mechanics while
    missing-suitability, missing-risk-profile, and mandate/restriction retain
    independent outcome contracts. These are internal design modules, not
    separately deployable services.
13. a typed implementation-proof artifact registry that maps every aggregate
    proof CLI input to its readiness arguments, evidence class, blocker effect,
    tracking issue, and classification status. The documentation contract gate
    fails when CLI, application signature, registry, or evidence inventory
    drift, including duplicate payload or reference arguments. Aggregate,
    opportunity-archetype, downstream component, source-ingestion, and
    scheduler consumers assert the registered effect before accepting evidence
    or mutating blockers. Unknown, duplicate, pending, or wrong-effect wiring
    fails closed. Scheduled-worker source and deployment inputs are
    independently classified and cannot substitute for one another.
14. a tracked architecture-boundary report contract at
    `quality/architecture_boundary_report.json`. The report binds the current
    `src/app` import inventory and rule digest through
    `architecture-boundary-report.v2`; `make architecture-boundary-gate` fails
    when that evidence is missing, malformed, stale, or tampered. This is
    deterministic design-boundary evidence only, not runtime certification or
    product support.

The first canonical demo/front-office portfolio remains
`PB_SG_GLOBAL_BAL_001` when a governed Lotus front-office flow requires a
portfolio identity. Do not infer broader portfolio support from that seed.

## Product Boundary

`lotus-idea` owns:

1. opportunity detection policy,
2. candidate identity, lifecycle, review, feedback, and expiry,
3. deterministic scoring, ranking, suppression, and queue policy,
4. source-provenanced evidence packs,
5. conversion intent and local submission posture,
6. readiness posture and implementation-proof aggregation,
7. idea data-product declarations while certification remains blocked.

`lotus-idea` does not own:

1. portfolio accounting, holdings, transactions, client master, product master,
   or official portfolio state,
2. official performance, attribution, benchmark, risk, stress, mandate,
   suitability, compliance, or model-portfolio calculations,
3. proposal suitability approval, mandate approval, rebalance execution, order
   management, settlement, report rendering, report archive, or client-ready
   publication,
4. AI provider infrastructure, model hosting, prompt-platform ownership, RAG
   infrastructure, or autonomous AI decisions.

AI/ML/RAG may assist only behind deterministic evidence, source authority,
entitlement checks, model-risk controls, prompt/output governance, audit, and
human review. AI output is advisory assistance only.

## Source Authority Map

Primary upstream source authorities:

1. `lotus-core`: portfolio state, holdings, cash, cashflow, benchmark
   assignment, maturity facts, mandate/client/product facts.
2. `lotus-performance`: return series, active return, benchmark context, and
   mandate performance-health context.
3. `lotus-risk`: concentration, volatility, drawdown, risk metrics, stress, and
   mandate risk-health context.
4. `lotus-advise`: suitability, proposal, policy evaluation, risk-profile, and
   advisory journey context.
5. `lotus-manage`: action register, model/rebalance workflow posture, mandate
   workflow context.
6. `lotus-report`: report-pack and report evidence context.
7. `lotus-ai`: governed AI workflow, prompt governance, model evaluation, and
   explanation assistance.

Primary downstream consumers:

1. `lotus-gateway`: API composition and BFF publication.
2. `lotus-workbench`: advisor and portfolio-manager review surfaces.
3. `lotus-advise`: proposal and suitability workflow conversion.
4. `lotus-manage`: portfolio action, mandate, and rebalance workflow
   conversion.
5. `lotus-report`, `lotus-render`, `lotus-archive`: evidence-pack intake,
   rendering, and archive workflows after downstream approval.

Source refs must preserve producer product identity, source system, version,
as-of date, generated-at timestamp, freshness, and content lineage where the
source provides it. Do not synthesize source-owned hashes from response payloads
unless the source contract explicitly permits it.
Manage mandate-health runtime qualification also requires trusted tenant scope,
producer-authored as-of and generated-at timestamps, and authoritative
action-register, Performance-health, and Risk-health source identities. Missing
metadata fails closed. Lotus Manage issue `#620` tracks the producer correction;
Idea must not substitute request or consumer timestamps.
Caller-supplied signal APIs must also validate source refs against the route's
governed source contract before candidate creation: wrong `sourceSystem` or
wrong `productId` is `400 invalid_request`, and rejection telemetry must use
the expected source authority instead of the caller-supplied mismatched
authority.
Bounded source-fetching signal APIs may exist only when they call an explicit
source-port/adapter, enforce caller entitlement scope before runtime dependency
construction, return product-safe dependency failures, and preserve source
authority. High-cash, low-income, bond-maturity, missing-benchmark,
concentration-risk, high-volatility, drawdown-review, underperformance,
allocation-drift, missing-suitability, missing-risk-profile, and
mandate/restriction `evaluate-from-source` APIs are internal foundations inside
the existing runtime; they do not certify live source support, persist
candidates, create a separate runtime service, prove Gateway/Workbench
behavior, certify a data product, or promote a supported feature.

Core-backed source evaluation requires exactly one tenant resolved from trusted
caller context before runtime construction. That tenant flows through request
DTO mapping, application commands, Core source ports, tenant-aware Core snapshot
payloads, candidate access scope, candidate identity, and generated ingestion
idempotency identity. Missing, ambiguous, self-asserted production, and
request-body override attempts fail closed before source I/O. Operational events
record only bounded `tenant_scope_provenance`; raw tenant identifiers remain
forbidden in operation attributes and metric labels. Core reads whose published
contract is not tenant-aware are not given invented query parameters.

All signal families share the versioned
`src/app/domain/source_temporal.py` contract:

1. every source business date must equal the consuming signal `as_of_date`,
2. source evidence must not be generated after `evaluated_at_utc`,
3. every included source ref is checked, including optional cross-domain refs,
4. caller-supplied DTO and source-adapter paths use the same domain policy,
5. a changed source content hash creates new lineage-bound candidate identity,
6. source-specific effective windows require a new explicit contract version
   and must never be inferred locally.

Low-income source-backed evaluation
consumes only Core-owned cash movement and cashflow projection evidence and
must not infer income needs, funding advice, treasury instructions, planning
suitability, or client-ready communication. Its closed v2 runtime evidence must
invoke the named application use case and bind exact request, movement-summary,
projection, and deterministic evaluation receipts. Zero cashflow is a valid
no-opportunity boundary; partial, stale, degraded, scope-inconsistent,
arithmetically inconsistent, or tampered evidence clears no blocker. Core issue
`#796` tracks producer trust metadata that Idea must not invent. Bond-maturity source-backed
evaluation consumes only Core-owned maturity summary and holdings lineage
evidence and must not own maturity schedules, recommend replacement products,
calculate reinvestment advice, approve planning suitability, or create orders.
Missing-benchmark source-backed evaluation consumes only Core-owned
benchmark-assignment evidence and must not assign benchmarks, certify benchmark
methodology, or calculate portfolio or benchmark performance.
Concentration-risk source-backed evaluation consumes only Lotus Risk-owned
`ConcentrationRiskReport:v1` evidence and must not calculate concentration,
approve risk methodology, recommend trades, create rebalance actions, or
promote risk/product support.
Concentration runtime evidence must invoke the authoritative Idea evaluation
and persistence use case and bind the exact current Lotus Risk source receipt
to an accepted or replayed durable Idea persistence receipt. In-memory runs,
self-asserted success, missing provenance, unknown claims, and receipt drift
clear no readiness blocker. Valid evidence affects only the live-Risk source
posture; it does not certify data mesh, Gateway/Workbench behavior, client
publication, deployment, production, or supported-feature promotion.
High-volatility source-backed evaluation consumes only Lotus Risk-owned
`RiskMetricsReport:v1` volatility evidence and must not calculate volatility,
VaR, tracking error, approve risk methodology, recommend trades, create
rebalance actions, or promote risk/product support.
High-volatility runtime evidence must invoke the authoritative Idea evaluation
and persistence use case and bind the exact current Risk source receipt to an
accepted or replayed durable Idea persistence receipt. In-memory execution,
self-asserted success, stale or mismatched evidence, non-candidate outcomes,
unknown claims, and receipt drift clear no blocker. Concentration and volatility
share internal execution and receipt assembly, but remain separate capability
contracts inside the existing service and Idea-owned database boundary.
Drawdown-review source-backed evaluation consumes only Lotus Risk-owned
`DrawdownAnalyticsReport:v1` evidence and must not calculate drawdown, approve
risk methodology, recommend trades, create rebalance actions, or promote
risk/product support.
Drawdown runtime evidence must invoke the authoritative Idea evaluation and
persistence use case and bind the exact current Risk source receipt to an
accepted or replayed durable Idea persistence receipt. Unknown claims,
self-asserted success, stale or mismatched evidence, non-candidate outcomes,
conflicts, in-memory execution, missing persistence, and receipt drift clear no
blocker. Concentration, volatility, and drawdown share internal execution and
receipt mechanics while retaining capability-owned contracts inside the
existing service and Idea-owned database boundary.
Drawdown-review remains family-compatible with the existing
`high_volatility` candidate family for persisted/API compatibility, while
`src/app/domain/opportunity_family_compatibility.py` explicitly records it as
the distinct Lotus Risk drawdown-review evidence lane under the combined
high-volatility / drawdown-review archetype. Do not introduce a first-class
drawdown candidate family without a migration/API-compatibility plan and
consumer coordination.
Underperformance source-backed evaluation consumes only Lotus Performance-owned
`ReturnsSeriesBundle:v1` active-return and benchmark-context evidence and must
not calculate returns, assign benchmarks, approve benchmark methodology,
recommend trades, create rebalance actions, or promote performance/product
support.
Allocation-drift source-backed evaluation consumes only Lotus Manage-owned
`PortfolioActionRegister:v1` posture and optional source-owned mandate-health
refs and must not calculate drift, approve mandate compliance, approve
suitability, recommend trades, create rebalance actions, create orders, or
promote Manage/product support.
Missing-suitability source-backed evaluation consumes only Lotus Advise-owned
`AdvisoryPolicyEvaluationRecord:v1` workflow posture and must not approve
suitability, approve policy, approve proposals, approve sign-off, publish
client communication, or promote Advise/product support.
Its closed v2 runtime-evidence contract invokes one named application use case
and binds pseudonymous request scope, producer workflow scope/time, policy and
source hashes, workflow posture, and deterministic candidate or no-opportunity
receipts. Missing or mismatched producer authority fails closed. The stable
environment variable and Make target reject retired v1 artifacts. Shared
Advise workflow qualification reduces duplicate producer logic while each
opportunity family retains its own schema and outcome policy. This is internal
design modularity, not a runtime service boundary.
Missing-risk-profile source-backed evaluation consumes only Lotus Advise-owned
`AdvisoryPolicyEvaluationRecord:v1` risk-profile diagnostic posture and must
not approve risk profiling, determine suitability, approve policy/proposals,
publish client communication, certify a typed risk-profile data product, or
promote Advise/product support.
Mandate/restriction source-backed evaluation consumes only Lotus Advise-owned
`AdvisoryPolicyEvaluationRecord:v1` explicit mandate/restriction diagnostic
posture and must not clear restrictions, change mandate state, determine
suitability, approve policy/proposals, recommend trades, create rebalance
actions, create orders, publish client communication, certify a typed
restriction data product, or promote Advise/product support.
Its v2 runtime-evidence contract calls the named application use case once and
binds pseudonymous request scope, producer workflow scope/time, policy and
source hashes, workflow posture, deterministic candidate or no-opportunity
outcome, and canonical digests. Missing producer as-of or trusted tenant scope
fails closed; request values and consumer clocks are never substituted. This is
an internal design module in the existing service, not a deployable boundary.

## Current Implementation Map

The codebase is organized around stable internal bounded modules before any
runtime modularity:

1. `src/app/domain/`: domain vocabulary, immutable persistence models, signal
   evaluation model contracts, policies, lifecycle, evidence, scoring,
   feedback, conversion, report evidence, outbox, and idempotency invariants.
2. `src/app/application/`: use-case orchestration, proof-readiness builders,
   source ingestion, downstream submission, outbox delivery, AI explanation,
   and readiness diagnostics.
3. `src/app/api/`: FastAPI routes, shared DTO modules for signal, idea-signal,
   review workflow, conversion, candidate detail, AI, outbox operator, and
   runtime trust telemetry surfaces, shared route metadata, caller-context binding,
   idempotency header validation, product-safe problem details, signal API
   support, and API-internal mutation-operation helpers.
4. `src/app/ports/`: repository, source, publisher, and downstream realization
   interfaces.
5. `src/app/infrastructure/`: HTTP source adapters, PostgreSQL repository,
   codecs, downstream HTTP client, publisher, and proof persistence helpers.
6. `src/app/runtime/`: runtime composition from environment variables.
7. `scripts/`: repo-native proof generators, gates, validation utilities, and
   operator helpers, including
   `run_canonical_opportunity_source_proofs.py` for source-specific live proof
   aggregation.
8. `data_lifecycle/` is the first capability-package pilot repeated inside the
   existing `api`, `application`, `domain`, `ports`, `infrastructure`,
   `integration`, and `runtime` layers. It groups lifecycle policy, signed
   authority verification, DTO mapping, ports, PostgreSQL/HTTP adapters, and
   composition without allowing cross-layer shortcuts. Focused tests mirror the
   package under `tests/unit/data_lifecycle/`. Repository hygiene blocks the
   retired flat paths and RFC/slice-coupled executable filenames. Scheduled
   review, proof-gate, and disposable-seed entrypoints are grouped under
   `scripts/data_lifecycle/`; they remain thin callers of application/domain
   policy and support direct Windows and CI execution.
9. `outbox/` is the second measured capability package. It groups operator API
   DTOs/routes, delivery and recovery use cases, event/lineage and state
   policies, the publisher port, PostgreSQL/HTTP adapters, publisher runtime
   composition, supportability metrics, proof generators, contract gates, and
   focused tests. The root `app.domain` surface continues to export stable
   public event types, but internal consumers use `app.domain.outbox`. Broader
   implementation-proof consumers remain with their owning capability. No
   compatibility modules, broker service, worker process, database boundary,
   or supported-feature claim was added.
10. `infrastructure/persistence/` owns bounded durable mutation and replay
    composition. Aggregate, PostgreSQL orchestration, and replay modules load
    only command, exact identity, and idempotency-linked candidates under
    identity/candidate/idempotency transaction locks. Outbox run idempotency is
    row-only; evidence replay is candidate-only. Full snapshots are reserved
    for explicit administrative/test/DR behavior. Focused unit and PostgreSQL
    tests mirror the package.
11. `app.infrastructure.postgres_snapshot_writes` owns PostgreSQL snapshot
    replacement and detail-write helpers for full snapshot/admin/test/DR flows.
    Keep candidate snapshot inserts, snapshot idempotency inserts, downstream
    submission inserts, lifecycle/audit/review/feedback/conversion/report
    detail inserts, and AI explanation lineage detail insertion out of the
    top-level `postgres_repository.py` class. Ordinary request paths should
    still use bounded mutation/projection modules rather than broad snapshot
    hydration.

Design modularity does not imply runtime modularity. Do not introduce a new
process, service, queue, worker class, or separately scalable boundary unless
workload, failure isolation, ownership, or operability evidence justifies it.

Current runtime process composition is still the `lotus-idea` service plus
bounded scripts/operators where explicitly implemented.

## Dominant Engineering Patterns

Use shared API helpers instead of route-local clones:

1. `app.api.route_metadata.RouteMetadata` for route metadata,
2. `app.api.problem_details` for product-safe RFC-7807 responses,
3. `app.api.idempotency` for mutating route `Idempotency-Key` validation,
4. `app.api.base_model.CamelModel` for camel-case API DTOs,
5. `app.api.signal_models` for shared signal-family DTOs,
6. `app.api.idea_signal_models` for high-cash and mandate-restriction
   idea-signal request/response DTOs behind the existing
   `app.api.idea_signals` route surface,
7. `app.api.review_workflow_models` for review-action and feedback
   request/response DTOs behind the existing `app.api.review_workflow` route
   surface,
8. `app.api.conversion_governance_models` for conversion-intent and
   conversion-outcome request/response DTOs behind the existing
   `app.api.conversion_governance` route surface,
9. `app.api.ai_governance_models` for AI explanation request/response DTOs
   behind the existing `app.api.ai_governance` import surface,
10. `app.api.outbox.delivery_models` for outbox delivery readiness
   and run-once response DTOs behind the existing
   `app.api.outbox.delivery` route surface,
11. `app.api.source_ingestion_readiness_models` for source-ingestion readiness
   and run-once response DTOs behind the existing
   `app.api.source_ingestion_readiness` route surface,
12. `app.api.runtime_trust_telemetry_models` for runtime trust telemetry
   preview/snapshot response DTOs behind the existing
   `app.api.runtime_trust_telemetry` route surface,
13. `app.api.candidate_detail_models` for source-safe candidate-detail,
   evidence, lifecycle, review, feedback, conversion, report evidence-pack,
   and audit-summary response DTOs behind the existing
   `app.api.candidate_detail` route surface,
14. `app.api.review_queue_models` for business review queue and readiness DTOs,
   with request mapping, access narrowing, audience routes, and operator
   exception models grouped under `app.api.review_queue`,
15. `app.api.signal_api_support` for caller context, scope checks, source-ref
   validation, the ordered caller-supplied and source-backed signal boundaries,
   source-ref rendering, signal outcome mapping, source runtime cleanup, and
   fail-closed dependency responses. Routes still supply request DTO mappers,
   concrete runtime factories, application use cases, and source ports; the
   shared boundary prevents lifecycle-order drift without introducing a new
   process boundary.
16. `app.api.review_workflow_operations` for review-action and feedback route
   caller parsing, mutating capability checks, trusted entitlement-scope subset
   validation, idempotency validation, durable-write guards, operation-event
   mapping, and product-safe persistence problem mapping,
17. `app.api.conversion_governance_operations` for conversion-intent and
   conversion-outcome route caller parsing, mutating capability checks,
   idempotency validation, durable-write guards, operation-event mapping, and
   product-safe persistence problem mapping,
18. `app.api.temporal_validation` for API timestamp awareness and UTC query
   validation.

When route behavior is moved into API-internal operation helper modules, tests
that capture operation events must patch the helper emitter aliases as well as
legacy route-local emitter names. Do not silently rely on route modules owning
the emitter after review/conversion/outbox helper extraction.

AI explanation evaluation remains inside `app.api.ai_governance` for now, but
the route must stay as a thin API-boundary orchestrator. Keep trusted caller
context binding, idempotency-to-command mapping, durable-write problem mapping,
exception-to-ProblemDetails mapping, and success/result response projection in
named helper functions rather than re-growing `evaluate_ai_explanation(...)`.
This is internal design modularity only; it does not implement production
authentication/authorization, Lotus AI runtime/provider certification, API
contract changes, or a separate runtime service.

When one HTTP status can return multiple stable `ProblemDetails` codes, use
`app.api.problem_details.merged_problem_response_metadata` instead of spreading
multiple response-metadata dictionaries with the same status key. Downstream
submission routes and durable-write routes rely on named OpenAPI examples so
generated API truth preserves `downstream_realization_not_configured`,
`durable_repository_not_configured`, `durable_repository_unavailable`,
`unsupported_downstream_realization_target`, and `idempotency_conflict` without
last-write-wins response overwrites. Shared `ProblemDetails` metadata must
publish examples under both `application/json` and `application/problem+json`;
`make openapi-problem-details-example-gate` enforces both media types so legacy
route-local metadata cannot silently understate RFC-7807 error contracts.

Use public domain and infrastructure APIs:

1. import cross-module domain objects through `app.domain`,
2. use public proof-readiness helpers from
   `app.application.implementation_proof_capability_updates`,
3. use `app.infrastructure.postgres_codecs` for PostgreSQL row, JSON, datetime,
   and domain serialization behavior,
4. do not couple tests or application code to protected private helpers across
   modules.

The public persistence import surface remains `app.domain.persistence`;
immutable persistence records, decisions, and snapshots live in
`app.domain.persistence_models` so repository behavior and domain data
contracts can evolve independently without creating a runtime boundary.

The public signal evaluation import surface remains
`app.domain.signal_evaluation`; immutable signal input, policy, outcome, and
result contracts live in `app.domain.signal_evaluation_models` so deterministic
signal-family contracts can evolve independently from evaluator algorithms
without creating a runtime boundary.

For durable reads, prefer bounded projections over whole repository snapshots:

1. advisor queue page projection,
2. candidate-detail projection,
3. downstream conversion/report lookup projection,
4. downstream realization readiness-count projection, including bounded
   downstream submission reconciliation workload,
5. outbox delivery readiness projection,
6. runtime trust telemetry aggregate projection, including local downstream
   submission posture counts,
7. advisor queue readiness aggregate projection.

When adding another read path or aggregate diagnostic, first ask whether the
query needs a bounded projection contract. Avoid `snapshot()` for narrow
PostgreSQL reads unless the provider is process-local, the request needs
in-memory-only policy state such as snoozes, or the flow is still explicitly
legacy.

Advisor queue paging uses one temporal contract across both providers:

1. `evaluatedAtUtc` is the inclusive candidate `createdAtUtc` boundary,
2. source `asOfDate` and evidence `generatedAtUtc` retain source-authority
   semantics and are not queue visibility fields,
3. page zero issues opaque identity bound to evaluation time, effective scope,
   queue ranking policy, accepted candidate score-policy set, snoozes, and
   visible candidate state,
4. positive offsets require that identity and fail with a stable conflict when
   visible state changes,
5. PostgreSQL verifies the fingerprint around the bounded page query, while
   later-created rows remain outside the historical snapshot,
6. `make review-queue-snapshot-contract-gate` protects command/port/adapter/SQL/
   API drift, and real PostgreSQL proof remains required for closure.

Keep this as domain policy plus an internal adapter boundary. A separately
deployed queue service requires measured scaling, failure-isolation, ownership,
or operability evidence.

Advisor-queue HTTP success evidence is code-owned rather than illustrative:
the capability factory persists a deterministic internal candidate through the
existing use case, builds the real queue projection, and serializes the
production response DTO for the named `itemsAvailable` and `noItemsAvailable`
200 modes. The endpoint ledger and generated OpenAPI must match that factory
exactly through the centralized named-success registry. This strengthens an
internal read-only contract only; it does not promote a supported feature or
transfer suitability, compliance, mandate, execution, or client-publication
authority to Idea.

Candidate scoring and queue ranking are distinct versioned policies:

1. `app.domain.scoring` owns weighted score calculation and the closed current
   candidate score-policy registry,
2. `app.domain.review_queue.policy` owns comparable score-policy versions,
   priority thresholds, exclusions, deduplication, and ordering,
3. `app.domain.review_queue.snapshot` owns continuation identity,
4. unknown or missing score-policy versions fail closed as
   `unrankable_score_policy` in both process-local and PostgreSQL providers,
5. readiness exposes only the aggregate
   `review_queue_score_policy_coverage_incomplete` blocker,
6. API `policyVersion` names the queue policy while candidate
   `scorePolicyVersion` preserves score provenance.

This package is design modularity inside the existing `lotus-idea` deployable.
Do not flatten it back into generic scoring or create a queue microservice
without measured workload, ownership, isolation, or operability evidence.

For mutation workflows, preserve idempotency, audit, operation events, source
authority, and supportability posture. Do not bypass repository mutation
methods just to optimize a write path.
Review-action and feedback API route orchestration is intentionally centralized
in `app.api.review_workflow_operations` as design modularity inside the
existing `lotus-idea` process. Do not split this into a separate runtime
service, worker, or queue boundary without measured workload, failure-isolation,
ownership, security, or operability evidence.
Materially distinct normal API outcomes must be published from DTO-validated,
code-owned examples and checked against both OpenAPI and the endpoint
certification ledger. For feedback, accepted and business-resource replay are
separate HTTP 200 modes; do not collapse replay into prose or a single accepted
example. Review actions, conversion intents, and conversion outcomes follow
the same rule, as does report evidence-pack request recording. Keep sibling
capability contracts in
`app.api.examples.review_workflow`,
`app.api.examples.conversion_workflow`, `app.api.examples.report_evidence`,
and their corresponding `scripts/endpoint_*_contracts.py` modules. Reuse
`app.api.examples.openapi` and
`endpoint_contract_support.validate_named_success_contract` so DTO validation,
OpenAPI publication, ledger parity, replay evidence, and authority boundaries
evolve together without copied enforcement. Apply this rule endpoint by
endpoint from executable application behavior and integration tests rather
than inferring completeness from example counts. Issue `#542` tracked the
capability-by-capability multi-shape HTTP 2xx inventory, and issue `#581`
closed the final status-aware `GET /health/ready` entry. Remaining blockers
are product/runtime/promotion evidence blockers, not missing named-response
contract inventory.
Register each capability validator in
`scripts/endpoint_named_success_contracts.py`; do not add another direct import
and invocation pair to the central endpoint certification gate. The registry
keeps capability ownership explicit while the central gate remains a stable,
maintainable orchestrator. Allocation-drift caller and Manage-backed
evaluation follows this contract under issue `#557`: both routes publish
candidate-created, blocked, suppressed, and not-eligible modes from their real
application paths. Source-backed candidates retain supporting Manage,
Performance, and Risk product lineage without granting Idea drift-calculation,
mandate, performance, risk, rebalance, or order authority. Twenty multi-shape
operations remained under issue `#542` after that family. Underperformance
caller and Performance-backed evaluation now follow the same contract under
issue `#559`. Both routes publish candidate-created, blocked, suppressed, and
not-eligible modes from their real application paths while preserving
`ReturnsSeriesBundle:v1` as Performance-owned evidence. Idea must not infer
returns, benchmark assignment, benchmark methodology, or investment-action
authority from these examples. Eighteen multi-shape operations remain under
issue `#542` after this family. Concentration-risk caller and Risk-backed
evaluation now follow the same contract under issue `#561`. Both routes
publish candidate-created, blocked, suppressed, and not-eligible modes from
their real application paths while preserving `ConcentrationRiskReport:v1` as
Risk-owned evidence. Idea must not infer concentration calculations,
methodology approval, trade recommendations, rebalance, or execution authority
from these examples. Sixteen multi-shape operations remain under issue `#542`
after this family. High-volatility caller and Risk-backed evaluation now follow
the same contract under issue `#563`. Both routes publish candidate-created,
blocked, suppressed, and not-eligible modes from their real application paths
while preserving `RiskMetricsReport:v1` as Risk-owned evidence. Idea must not
infer volatility, VaR, tracking-error calculations, methodology approval,
trade recommendations, rebalance, or execution authority from these examples.
Fourteen multi-shape operations remain under issue `#542` after this family.
Drawdown-review caller and Risk-backed evaluation now follow the same contract
under issue `#565`. Both routes publish candidate-created, blocked, suppressed,
and not-eligible modes from their real application paths while preserving
`DrawdownAnalyticsReport:v1` as Risk-owned evidence. Idea must not infer
drawdown calculation, period selection, methodology approval, trade
recommendations, rebalance, or execution authority from these examples. Twelve
multi-shape operations remain under issue `#542` after this family.
Mandate-restriction caller and Advise-backed evaluation now follow the same
contract under issue `#567`. Both routes publish candidate-created, blocked,
suppressed, and not-eligible modes from their real application paths. The
caller route preserves the actual governed Core, Manage, or Advise source
authority; the source-backed route retains Advise
`AdvisoryPolicyEvaluationRecord:v1` identity. Idea must not infer restriction
clearance, mandate change, suitability or policy approval, client publication,
rebalance, order, or execution authority from these examples. Ten multi-shape
operations remain under issue `#542` after this family.
Missing-risk-profile caller and Advise-backed evaluation now follow the same
contract under issue `#569`. Both routes publish candidate-created, blocked,
suppressed, and not-eligible modes from their real application paths. The
source-backed route uses only the Advise source port and retains
`AdvisoryPolicyEvaluationRecord:v1` identity. Idea detects review posture only;
it must not approve or create a client risk profile, determine risk capacity,
approve suitability or policy, publish to a client, or infer product authority
from these examples. Eight multi-shape operations remain under issue `#542`
after this family.
Missing-benchmark caller and Core-backed evaluation now follow the same
contract under issue `#571`. Both routes publish candidate-created, blocked,
suppressed, and not-eligible modes from their real application paths. The
source-backed route uses only `CoreBenchmarkAssignmentSourcePort` and retains
`BenchmarkAssignment:v1` identity. Idea detects review posture only; it must
not assign a benchmark, approve benchmark methodology, calculate performance,
recommend a trade, rebalance, execute, or infer Core product authority from
these examples. Six multi-shape operations remain under issue `#542` after
this family. The existing platform named-success skill and validator guardrail
already cover this recurrence, so no new skill/context change is required.
Missing-suitability caller and Advise-backed evaluation now follow the same
contract under issue `#573`. Both routes publish candidate-created, blocked,
suppressed, and not-eligible modes from their real application paths. Advise
retains `AdvisoryPolicyEvaluationRecord:v1`, suitability, policy, proposal,
sign-off, and client-publication authority; Idea only detects deterministic
evidence-gap posture and routes compliance review. Four multi-shape operations
remain under issue `#542`; the existing platform guardrail covers this recurrence.
Unit-test modules must also use globally unique basenames across nested
directories because pytest imports this repository's tests by module basename.
Name example-publication tests for the durable concern, such as
`test_report_evidence_examples.py`, rather than colliding with an existing
domain test such as `test_report_evidence.py`.
The downstream-submission family under issue `#575` reduced that inventory to
two operations by certifying both conversion-intent and report-evidence-pack
submissions as status-aware application-backed contracts. The advisor queue
under issue `#577` then reduced it to one by publishing exact
`itemsAvailable` and `noItemsAvailable` queue examples. Issue `#581` closes
the final `GET /health/ready` entry with runtime-derived named `200` and `503`
response modes. Its generic status-mode validator is deliberately separate
from the named-success vocabulary because readiness failures are operational
traffic controls, not business outcomes. The central endpoint gate invokes
targeted validators for baseline platform operations as well as business
endpoints. None of these inventory corrections promote a supported feature or
transfer product authority.
Conversion-intent and conversion-outcome API route orchestration follows the
same pattern in `app.api.conversion_governance_operations`. This helper is an
internal API boundary only; conversion posture remains local, review-gated, and
source-authority preserving. It must not become a separate runtime boundary
unless measured workload, failure-isolation, ownership, security, or
operability evidence justifies the added distributed-systems cost.

For PostgreSQL-backed mutations, candidate-row updates use an optimistic
`updated_at_utc` compare-and-set guard and reject stale same-candidate snapshot
writes before detail rows or outbox events can be committed. Idempotency rows
are inserted with PostgreSQL conflict detection; concurrent duplicate-key races
roll back and retry once from a fresh database snapshot so same-payload reuse
returns governed replay posture and changed-payload reuse returns governed
conflict posture.

Ordinary PostgreSQL mutations acquire transaction-scoped identity locks, sorted
candidate locks, and the exact idempotency lock before bounded state reads.
Candidate, lifecycle, review, feedback, conversion, report evidence, and AI
lineage operations hydrate only command or exact identity-linked aggregates;
the outbox delivery-run request hydrates only its idempotency row. Evidence
replay and report precheck use candidate-only and idempotency-linked projections.
The 17-test disposable PostgreSQL 18 lane proves the resulting restart,
concurrency, recovery, queue, downstream, lifecycle, and nullable-bind posture.

## Outbound HTTP Resilience Pattern

Outbound HTTP resilience is centralized in
`app.infrastructure.downstream_client`.

Defaults remain one attempt. Opt-in retry settings exist for:

1. Core source ingestion,
2. Advise/Manage/Report downstream realization,
3. outbox broker publication.

The shared client retries only:

1. timeout exceptions,
2. HTTP transport failures,
3. `429`,
4. `502`,
5. `503`,
6. `504`.

The shared client does not retry local validation failures, local
idempotency conflicts, local business-state failures, malformed upstream
responses, or ordinary client errors such as `400`, `401`, `403`, `404`, and
`409`.

`POST` retries require an idempotency key unless the runtime explicitly marks
the route as read-only source-query traffic. Today that exception is limited to
Core source-ingestion query/control-plane `POST` calls.

Configured retry backoff uses a fixed central 20% downward jitter window for
computed backoff delays so source ingestion, downstream realization, and outbox
publication do not create synchronized retry waves. Valid upstream
`Retry-After` values remain authoritative and are only capped by
`retry_max_backoff_seconds`; they are not jittered.

Outbox publication propagates the event idempotency fingerprint as the
outbound `Idempotency-Key`.

Do not add adapter-local retry loops. Extend `DownstreamClientConfig`,
`DownstreamJsonClient`, and the caller-boundary tests instead.

## Runtime Configuration Families

Repository provider:

1. local/test profiles may use process-local repository state,
2. demo/staging/production must configure `LOTUS_IDEA_DATABASE_URL`,
3. missing durable storage in non-local profiles fails closed.

Source ingestion:

1. `LOTUS_IDEA_SOURCE_INGESTION_MANIFEST`,
2. `LOTUS_IDEA_CORE_BASE_URL` or split query/control-plane URLs,
3. `LOTUS_IDEA_SOURCE_INGESTION_TIMEOUT_SECONDS`,
4. `LOTUS_IDEA_SOURCE_INGESTION_MAX_CONNECTIONS`,
5. `LOTUS_IDEA_SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS`,
6. `LOTUS_IDEA_SOURCE_INGESTION_POOL_TIMEOUT_SECONDS`,
7. `LOTUS_IDEA_SOURCE_INGESTION_RETRY_MAX_ATTEMPTS`,
8. `LOTUS_IDEA_SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS`,
9. `LOTUS_IDEA_SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS`.

Downstream realization:

1. `LOTUS_IDEA_ADVISE_REALIZATION_BASE_URL`,
2. `LOTUS_IDEA_ADVISE_REALIZATION_SUBMIT_PATH`,
3. `LOTUS_IDEA_MANAGE_REALIZATION_BASE_URL`,
4. `LOTUS_IDEA_MANAGE_REALIZATION_SUBMIT_PATH`,
5. local/test-only Manage fixture: `LOTUS_IDEA_MANAGE_REALIZATION_ACTOR_ID`,
   `LOTUS_IDEA_MANAGE_REALIZATION_ROLE`,
   `LOTUS_IDEA_MANAGE_REALIZATION_TENANT_ID`, and
   `LOTUS_IDEA_MANAGE_REALIZATION_SERVICE_IDENTITY`, and
   `LOTUS_IDEA_MANAGE_REALIZATION_CAPABILITIES`,
6. `LOTUS_IDEA_REPORT_REALIZATION_BASE_URL`,
7. `LOTUS_IDEA_REPORT_REALIZATION_SUBMIT_PATH`,
8. local/test-only Report fixture: `LOTUS_IDEA_REPORT_REALIZATION_ACTOR_ID`,
   `LOTUS_IDEA_REPORT_REALIZATION_CALLER_APPLICATION`,
   `LOTUS_IDEA_REPORT_REALIZATION_TENANT_ID`, and
   `LOTUS_IDEA_REPORT_REALIZATION_REGION`. The owner-authorized synthetic
   fixture is fixed to `tenant-sg` / `APAC`; other local/test values fail
   closed. At the Report adapter boundary only, the Idea-owned
   `lotus-report:idea-evidence-retention:v1` reference maps to the
   Report-owned `generated-report-standard` selector. Do not persist that
   selector in Idea or treat it as trusted production identity,
9. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_TIMEOUT_SECONDS`,
10. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_MAX_CONNECTIONS`,
11. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_MAX_KEEPALIVE_CONNECTIONS`,
12. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_POOL_TIMEOUT_SECONDS`,
13. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_MAX_ATTEMPTS`,
14. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_INITIAL_BACKOFF_SECONDS`,
15. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_MAX_BACKOFF_SECONDS`.

The Manage and Report fixtures are server-side local/test development aids
only. They never trust browser-supplied identity headers and fail closed in
demo, staging, and production until trusted service identity and
IdP/session/token-claim mapping are delivered through the tracked identity
work in issue `#380`. The Report adapter maps the Idea evidence envelope into
the Report-owned strict snake-case intake contract, performs only the governed
retention-policy selector translation documented above, and does not grant
Report, Render, Archive, or publication authority.

Outbox broker:

1. `LOTUS_IDEA_OUTBOX_BROKER_URL`,
2. `LOTUS_IDEA_OUTBOX_BROKER_TIMEOUT_SECONDS`,
3. `LOTUS_IDEA_OUTBOX_BROKER_MAX_CONNECTIONS`,
4. `LOTUS_IDEA_OUTBOX_BROKER_MAX_KEEPALIVE_CONNECTIONS`,
5. `LOTUS_IDEA_OUTBOX_BROKER_POOL_TIMEOUT_SECONDS`,
6. `LOTUS_IDEA_OUTBOX_BROKER_RETRY_MAX_ATTEMPTS`,
7. `LOTUS_IDEA_OUTBOX_BROKER_RETRY_INITIAL_BACKOFF_SECONDS`,
8. `LOTUS_IDEA_OUTBOX_BROKER_RETRY_MAX_BACKOFF_SECONDS`.

Invalid or internally inconsistent runtime settings fail closed before
outbound work is attempted.

## API And Contract Posture

Certified internal foundation endpoints are tracked in
`docs/operations/endpoint-certification-ledger.json`.

OpenAPI truth is enforced by repo-native gates. Do not add a public route
without updating route metadata, endpoint certification, tests, docs, wiki, and
operation-event evidence where applicable.

Downstream submission endpoints are internal foundations:

1. `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions`,
2. `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions`.

They require `idea.downstream-realization.submit` and `Idempotency-Key`, record
bounded local posture, and propagate correlation, trace, and idempotency
context. They do not record authoritative downstream outcomes or prove route
existence in the owning downstream service.

Both routes publish application-derived accepted, rejected, accepted-replayed,
and rejected-replayed HTTP `200` modes, plus a separately named HTTP `202`
`reconciliation_required` mode. Same-key retries preserve the local outcome and
do not make another downstream call. Advise/Manage retain conversion workflow
and outcome authority; Report retains materialization authority. Idea retains
only local intent, claim/finalize, reconciliation, and audit posture. The
status-aware named-success validator is the reusable repository guardrail; no
README or supported-feature promotion follows from this contract closure.

Readiness endpoints are diagnostic foundations. `GET /health/ready` publishes
one `200 ready` mode and source-safe `503` draining, restoring,
durable-repository, and release-identity blocked modes from the same typed
assembly path used by the route. They report aggregate blockers and
source-of-truth refs; they are not support, certification, or live journey
proof by themselves.

## Data Mesh Posture

Repo-owned data-mesh declarations live under
`contracts/domain-data-products/`.

Producer products remain proposed or not certified until implementation-backed
products emit runtime telemetry, the platform source manifest includes
`lotus-idea`, and platform mesh gates pass.

Consumer declarations must name governed source authorities and must not imply
that `lotus-idea` owns upstream calculations.

`make data-mesh-contract-gate` is a pre-certification anti-drift guard. It is
not platform mesh certification.

Runtime trust telemetry preview/snapshot endpoints and generated artifacts are
source-safe readiness evidence. They include bounded local downstream
submission posture counts, but those counts are Idea-owned posture only. They
are not certified data products, downstream acceptance/materialization proof,
or supported-feature promotion.

PostgreSQL trust projections count only lifecycle-active or held-from-active
records as candidate and workflow data products. Erased and purged tombstones
remain visible only through bounded `dataLifecycleStateCounts`,
`retentionExpiredCount`, and `lifecycleControlMissingCount` posture. Missing
controls block certification; process-local repositories report uncontrolled
lifecycle posture rather than implying durable governance.
Downstream submission posture in trust telemetry is counted only as aggregate
local state from `idea_downstream_submission` statuses and must not hydrate
submission payloads or support references.

## Security And Privacy Posture

Security controls currently include:

1. route-level caller context and capability policy,
2. scope-aware entitlement checks,
3. product-safe permission failures,
4. no-sensitive-content artifact guard,
5. source-safe operation events and low-cardinality metric labels,
6. stream-enforced HTTP request-size limits for JSON write methods,
7. trusted caller-context provenance enforcement for production-like profiles,
8. GitHub Security posture checks,
9. Dependabot/security-update governance,
10. CodeQL default setup governance,
11. secret scanning and push protection where GitHub reports them enabled.
12. versioned field classification, residency, retention, legal-hold,
    erasure, purge, and immutable tombstone controls for Idea-owned records.
13. exact runtime/CI license inventory, SPDX classification, deterministic
    notices, expiring exception governance, and digest-bound release evidence.

These are foundation controls, not production identity-provider proof.
Route-level capability checks consume caller-context headers inside the service
boundary. In `demo`, `staging`, and `production` profiles, privileged
`X-Caller-*` role, capability, and entitlement headers are rejected unless the
request also carries `X-Lotus-Trusted-Caller-Context` matching
`LOTUS_IDEA_TRUSTED_CALLER_CONTEXT_TOKEN`. This is a bounded trusted-ingress
provenance marker for service-to-service propagation; it is not an
identity-provider integration, signed assertion, Workbench entitlement proof,
client-publication proof, or supported-feature promotion.

The data-lifecycle operator route requires `privacy_officer` or
`records_manager`, `idea.data-lifecycle.manage`, exact trusted tenant scope,
idempotency, durable sanitized correlation/trace, governed authority, preview,
and distinct approval for release, erase, and purge. Lotus Idea enforces externally approved decisions and must
not self-authorize legal hold, privacy erasure, Report/Archive retention, or AI
provider deletion. Erased and purged records must be excluded at every direct
read projection, not only from whole-repository snapshots. New downstream
claims participate in the lifecycle lock so erasure and delivery cannot create
an unsafe terminal state. Lifecycle mutations lock the candidate row and then
the lifecycle-control row before reading active outbox or downstream-delivery
posture. This ordered fence prevents a concurrent claim from being accepted
after erasure evaluated stale delivery state; replay-only reads do not take the
mutation lock.

When a candidate has an Idea-owned report evidence-pack request, lifecycle
actions also consume an independently signed
`lotus-archive:IdeaEvidenceLifecycleDecision:v1` posture. The API verifies the
strict trust bundle from `LOTUS_IDEA_ARCHIVE_LIFECYCLE_TRUST_BUNDLE_JSON`; the
domain reconciles the receipt against exact report-pack IDs loaded inside the
same PostgreSQL transaction. Active Archive hold blocks release, erase, and
purge; local hold requires Archive `LEGAL_HOLD`; local purge requires
`DISPOSAL_EXECUTED`. Migration `015` persists source-safe receipt lineage and
fences applied decision IDs and payload digests across restart. This consumer
control stays inside the existing deployable service. It does not grant Archive
disposal authority or replace the independent signed bank decision.

Caller-supplied opportunity signal routes and advisor-facing candidate detail /
review queue reads require both the product role and the explicit `idea.*`
capability published for the route. `app.api.signal_api_support` requires
advisor role plus `idea.signal.evaluate` before evaluating source-owned
evidence. `src/app/api/candidate_detail.py` and the capability-grouped
`src/app/api/review_queue/` package require route-specific business or operator
roles and read capabilities before returning source-safe candidate, audience
queue, or aggregate exception data. The signal API
contract gate blocks route-local signal permission policies, and the caller
context contract gate blocks route policies that name both `allowed_roles` and
an `idea.*` capability but authorize through role-or-capability semantics.

`make github-security-posture-check` is the operator-run live posture check for
GitHub Security settings. Treat GitHub Security state as mutable external
truth; verify before claiming it.

At the last reviewed posture on 2026-06-30 UTC, GitHub reported zero open
code-scanning, secret-scanning, and Dependabot alerts. Dependabot security
updates, secret scanning, and secret-scanning push protection reported enabled;
non-provider secret patterns and secret validity checks reported disabled.
`SECURITY.md` and `.github/dependabot.yml` were still not present on
`origin/main`, so those repository-authored controls remain branch-local until
merged and visible on the default branch.

No raw source payloads, portfolio identifiers, client identifiers, request
bodies, response bodies, raw entitlement failures, prompt text, provider output,
database URLs, or local secrets belong in logs, operation events, proof
artifacts, wiki, or PR evidence.

License and IP truth is governed by
`contracts/compliance/lotus-idea-license-policy.v1.json`. Every resolved
runtime and CI dependency must have exact version, scope, SPDX expression,
source, attribution, and obligations; unknown, denied, unlocked, or stale
entries fail closed. Exceptions require application-owner, security, and legal
approval, immutable evidence, and expiry. Main release evidence binds policy
version, lock hashes, NOTICE digest, SBOM serial, exception IDs, and final image
digest. `CODEOWNERS` provides repository routing only and cannot self-prove
legal approval. Base-image package licensing and external generated/model/data
asset rights remain distinct review boundaries. Use
`docs/operations/license-ip-compliance.md`; this control adds no supported
feature and no runtime deployable.

## Observability And Operability

Operation events are the primary supportability surface. They must stay
bounded, source-safe, and low-cardinality.

Use route templates rather than raw paths in diagnostics.

Use correlation and trace headers across outbound calls when available.

Metrics and operation-event vocabulary are governed by
`contracts/observability/lotus-idea-operation-metrics.v1.json`.

AI model-risk operations proof is limited to implemented AI explanation
telemetry and is classified as `source_contract`. Keep its builder, thin
generator, gate, and focused tests under capability-oriented
`ai_model_risk_operations/` packages. A valid artifact adds an aggregate
evidence reference but clears no blocker and must retain dashboard provisioning
and alert-rule evaluation/delivery blockers. It does not certify deployment,
`lotus-ai` runtime execution, provider calls, Workbench behavior, data-mesh
certification, or supported-feature promotion. This is internal design
modularity; no runtime split is justified without workload, failure-isolation,
ownership, security, or operability evidence.

AI workflow-pack runtime evidence is a separate v2 execution-receipt boundary.
`app.application.ai_runtime_proof` builds the synthetic redacted request and
validates the bounded receipt, `app.ports.lotus_ai_runtime` owns the stable
execution interface, and `app.infrastructure.lotus_ai.workflow_runtime` owns
HTTP transport. Static sibling-source inspection is registration/design
evidence only and must never set `lotusAiRuntimeExecuted` or clear a runtime
blocker. A deterministic stub receipt clears only the generic runtime seam and
must add `lotus_ai_live_provider_execution_missing`; it is not provider,
production approval, Workbench, client-publication, or supported-feature proof.
Issue `#393` tracks the same evidence-classification audit across other proof
builders.

Gateway/Workbench route declarations and local file or Make-target checks are
also source-contract evidence. Keep their application policy, thin generator,
contract gate, and focused tests under capability-oriented `workbench/`
packages. A valid contract artifact may add aggregate evidence references but
must preserve `gateway_workbench_proof_missing`; only machine-verifiable
runtime execution evidence can clear that blocker. This is internal design
modularity inside the existing deployable service. Do not introduce a separate
runtime service without workload, failure-isolation, ownership, security, or
operability evidence.

Gateway/Workbench catalog entries, approved-consumer declarations, and sibling
platform generated files are also `source_contract` evidence. Keep the
discovery contract builder, generator, gate, and focused tests in the same
capability-oriented `workbench/` packages. A valid discovery contract artifact
may add evidence references to data-mesh and runtime-trust readiness, but it
must clear no blocker and must preserve
`gateway_workbench_discovery_proof_missing`. Active catalog publication,
Gateway serving, Workbench consumption, entitlement enforcement, and canonical
runtime behavior require machine-verifiable evidence from their owning
runtimes. No separate Lotus Idea service is justified by this design boundary.

Outbox consumer declarations are source-contract evidence. Keep their builder,
generator, contract gate, and tests under the existing `outbox/` capability
directories with `consumer_contract_proof` naming. A valid declaration may add
an aggregate evidence reference, but it must clear no runtime blocker. Only an
observed, machine-verifiable consumer execution receipt may satisfy
`downstream_consumer_runtime_proof_missing`; file presence, Make targets,
consumer names, and authority-boundary text cannot be promoted into runtime
truth.

AI proposed-action labels are untrusted input even when the structured action
enum is allowed. Enforce `lotus-idea.ai-action-content-policy.v1` in the domain
before claim verification, return only canonical server-owned labels, and keep
rejected raw labels out of persistence, audit attributes, and API responses.
This is an Idea-owned deterministic output-governance boundary, not ownership
of provider execution, prompts, RAG, or AI runtime infrastructure.

AI explanation text is also untrusted input. Enforce
`lotus-idea.ai-claim-grounding-policy.v1` after deterministic source-product and
action verification. Accepted advisor-visible narrative must be server-rendered
from ordered verified claims and must carry source-safe product/version, as-of,
freshness, and quality references. Blocked output returns no grounded claims.
Replace blocked provider prose with deterministic server-owned explanation text
before the domain result reaches API projection. Keep submitted narrative out of
accepted, blocked, fallback, replay, and conflict responses and persistence;
bind its digest and the grounding policy into output integrity so replay
conflicts remain exact. A blocked status alone is not sanitization.
This policy belongs to the internal `app.domain.ai_explanation` capability and
does not justify a separate runtime or transfer AI infrastructure ownership from
`lotus-ai`.

AI explanation replay identity must include
`lotus-idea.ai-output-integrity.v1`. Commit to ordered explanation, claim,
action, workflow/evaluator, and policy content; persist only the source-safe
digest/version; return the same values through the governed evaluation API;
and fail PostgreSQL hydration on column/JSON/hash mismatch. Pre-v1 rows are
explicitly unverifiable and must never be described as retroactive content
proof. Retention follows the Idea regulated-advisory lifecycle policy.

AI workflow output trust is governed by
`lotus-idea.ai-execution-provenance-policy.v1`. Local/test may accept only an
explicit `unattested_local_test_fixture`; demo, staging, and production reject
unattested workflow output before candidate lookup or persistence and accept
only a complete producer output bundle with a verified run receipt.
Deterministic fallback remains allowed. Signed
run/model attestation issuance and key distribution belong to `lotus-ai`; the
producer contract was completed under `sgajbi/lotus-ai#113`. Live
provider/model approval and runtime truth remain external and do not become
Idea authority.
Idea consumes the exact producer envelope through `app.integration`, discovers
keys only at the fixed well-known path, verifies Ed25519 signatures and
deterministic input/output bindings, maps verified output through the
application use case, and atomically persists a bounded receipt. Run id and
replay nonce remain unique across restart. Producer and consumer mainline/CI
evidence exists, so readiness reports the verifier as available without a
missing-mainline-proof claim. The capability-owned signed-attestation v2
`source_contract` binds separate producer and consumer repository/ref/SHA-256
collections plus canonical collection digests. Isolated CI validates only an
explicit `idea_consumer_only` non-proof posture. Unknown fields and execution,
model-risk approval, deployment, production, Workbench, publication, or
promotion claims fail closed. Source-contract evidence still clears no
live-runtime, Workbench, or promotion blocker.

Idea also independently verifies and atomically persists the bounded
`lotus-ai:ProviderRetentionConfirmation:v1` receipt with attested explanation
lineage. Run, candidate tenant, provider, mode, and model identities must match;
confirmation/reference/nonce replay is fenced. The receipt reports provider
posture only and never authorizes bank lifecycle actions or substitutes for
Report/Archive conformance. Provider-native evidence and approvals remain
external blockers under `sgajbi/lotus-ai#115`.

The producer/consumer contract foundations are merged and mainline-proven as of
2026-07-12: Lotus AI `51a8e8e` (run `29179866214`), Lotus Report `59385c5`
(run `29179900038`), Lotus Archive `e5e9253` (run `29179849407`), and Lotus Idea
`f496c442` (run `29179489433`). Their repo-authored wikis are synchronized.
This clears branch-local contract delivery only. It does not clear provider-native
confirmation, managed-key/production-store proof, bank privacy/legal/model-risk
approval, live bank lifecycle authority, or production-authorized purge blockers.
Slice 06 lifecycle-authority consumption is now contract-bound to
`lotus-platform/platform-contracts/lifecycle-authority/` through
`contracts/integrations/lifecycle-authority-consumer.v1.json`. The existing data-lifecycle gate
pins and, when the sibling platform repository is available, verifies the decision, key-discovery,
and producer-certification artifact digests. This is consumer interoperability evidence only;
bank legal/privacy governance remains the substantive authority and production certification stays
blocked.
Idea scheduled lifecycle review run `29180046362` also passed on `f496c442`
with PostgreSQL 18, source-safe proof validation, provenance attestation, and
artifact upload. That artifact is review-only and `not_certified`; it is not
production purge or privacy-authority evidence.

Provider-bound AI metadata uses the closed
`lotus-idea.ai-metadata-envelope.v1` policy in
`src/app/domain/ai_metadata_policy.py`. Request DTOs expose only approved
`channel` and `audience` fields; the domain revalidates purpose and closed
values before application lookup or persistence. Do not add generic metadata
maps, denylists, client/portfolio identifiers, or free-form values. Future
Lotus AI adapters may receive only this validated mapping. Lineage and logs may
retain field names and policy version, never raw values. This is design
modularity inside the Idea deployable; introduce a runtime boundary only with
measured workload, failure-isolation, ownership, or operability evidence.

Non-AI operator workflow operations proof is limited to source-safe dashboard
and alert visibility over implemented source-ingestion, outbox delivery,
downstream realization, runtime trust telemetry, and implementation-proof
readiness. Outbox state, oldest due age, configuration, and collection gauges
are derived on scrape from the bounded readiness projection and remain
separate from operation-event traffic. It does not certify live source ingestion,
external broker publication, downstream execution outcomes, Gateway/Workbench
behavior, data-mesh certification, or supported-feature promotion.

Implementation-proof readiness is an aggregate blocker view. It should help
operators find missing proof; it must not be presented as full live journey
proof while blockers remain.

Treat inbound correlation and trace headers as untrusted input. The shared
observability sanitizer preserves only product-safe diagnostic identifiers and
replaces blank, overlong, portfolio-like, token-like, or malformed values before
response, log, or downstream propagation.

## Repo-Native Commands

Use repo-native commands before ad hoc command sequences.

Fast local checks:

```powershell
make lint
make typecheck
make test-unit
make documentation-contract-gate
make implementation-truth-gate
make foundation-structure-gate
make supported-features-gate
```

`make foundation-structure-gate` is the foundation-posture guard introduced by RFC-0002 Slice 2. It keeps
the supported-feature registry in foundation-only posture, requires README,
repo context, RFC index, and wiki support truth to agree, and reuses the
architecture boundary gate so domain/API modularity does not drift while later
slices add product behavior.

Focused Python checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_downstream_client.py
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy --config-file mypy.ini
```

Proof and contract gates commonly touched by RFC-0002 work:

```powershell
make endpoint-certification-gate
make openapi-quality-gate
make data-mesh-contract-gate
make downstream-realization-contract-gate
make downstream-route-source-contract-proof-gate
make outbox-broker-source-contract-proof-gate
make runtime-trust-telemetry-test-execution-contract-gate
make source-ingestion-runtime-execution-contract-gate
make canonical-opportunity-source-proofs
make source-ingestion-scheduled-worker-check
make quality-scorecard-gate
make repository-hygiene-gate
make runtime-dependency-closure-gate
make github-security-posture-check
```

Advise and Manage route source contracts are declaration evidence only. The
capability-owned `app.application.downstream_realization.route_source_contract`
module binds sibling contract, route, and service sources by repository/ref and
SHA-256. Aggregate and downstream readiness may attach a valid current artifact
as supporting evidence, but must preserve `advise_live_contract_proof_missing`
and `manage_live_contract_proof_missing` until an owning runtime supplies a
governed serving-and-acceptance receipt. Do not infer route execution from
source files, Make targets, or sibling contract status.

Current repo-native aggregate command posture:

1. `make install` creates the development virtual environment with
   `requirements/runtime-resolved.lock.txt` as a constraint, so CI and local
   validation exercise the same governed runtime transitive dependency pins
   while still installing dev tooling.
2. `make ci` is the broad local aggregate command for lint, typecheck,
   contract gates, OpenAPI, migrations, tests, coverage, and dependency audit.
   It is not Docker, PostgreSQL runtime, image-scan, SBOM, or release-evidence
   proof by itself. Its lint lane includes `runtime-dependency-closure-gate`
   so release SBOM inputs cannot silently fall back to direct-only runtime
   dependency evidence.
3. `make ci-release` is the governed full-lane local command. It runs `make ci`
   plus `postgres-integration-gate`, `docker-build`, `container-runtime-smoke`,
   `container-image-scan`, and `release-sbom`. Cite it only when the required
   local PostgreSQL and Docker prerequisites were actually available and run.
4. `make ci-contract-gate` blocks drift if the full-lane command omits those
   PostgreSQL or container/release proof families.
5. GitHub workflow YAML should keep calling repo-native targets rather than
   reimplementing opaque inline proof.

PostgreSQL evidence:

```powershell
make postgres-integration-gate
```

Run it only with a disposable PostgreSQL URL configured through the repo's
expected environment variable.

The app-owned `docker-compose.yml` is independently operable: it provisions
PostgreSQL 18, mounts the named volume at the major-version-supported
`/var/lib/postgresql` path, executes a one-shot migration dependency, and starts
API/optional worker roles against one explicit database URL. Local migration
history is pending-only, advisory-lock serialized, transactional, and bound to
version/name/content checksums so repeated Compose startup is safe and drift
fails closed. Direct `uvicorn` without a database remains an explicitly
ephemeral local/test path. Canonical Workbench automation consumes this app
contract and must not replace its persistence or migration ownership.

Deployment migrations are a separate production-like control. Use
`contracts/operations/lotus-idea-deployment-migrations.v1.json` and
`make deployment-migration-contract-gate` as contract truth. Protected
execution runs `scripts/run_deployment_migrations.py` from an exact signed and
attested mainline image digest through
`.github/workflows/deployment-migration-evidence.yml`; it must never run as API
or worker startup behavior. The application use case delegates through the
deployment-migration port to the PostgreSQL adapter, which owns the advisory
transaction lock, PostgreSQL 18 check, strict durable-history prefix,
name/content drift rejection, pending-only apply, explicit fingerprinted
legacy adoption, bounded rollback, and atomic history/event writes. Migration
events are database-enforced append-only.

The database URL is a runtime deployment secret only. It must not be accepted
as a CLI argument or appear in image build inputs, logs, evidence, or
attestations. Evidence binds the main ref, commit, CI run, exact image digest,
environment class, change reference, deployment actor, migration-bundle digest,
and version transition. `make migrate` and `make migrate-rollback` remain
local/disposable fixture tools, not deployment authority. Direct workflow use
is restricted to the governed disposable lifecycle-review and DR-seed paths;
new production-like workflows must use the protected exact-image workflow.

This is design and operability modularity inside the existing deployable. The
API and optional worker continue to share one Idea-owned PostgreSQL database.
Do not add a separately deployed long-running migration service or split the
database without concrete workload, failure-isolation, ownership, or operability
evidence. The app-local one-shot Compose migration job is startup orchestration,
not a new runtime boundary. The implemented production workflow
is still non-certifying until a protected environment run, approved change,
same-digest rollout health proof, mainline validation, and retained attestation
exist. Issue `#375` is the durable tracker. Protected staging and production
environments now exist with protected-branch rules, and production requires
reviewer approval. No environment-scoped database secret, governed target,
approved connectivity path, or live rollout evidence exists. The workflow uses the same GitHub-hosted
`ubuntu-latest` execution plane as other Lotus apps; a private runner is not a
current prerequisite. Database reachability must use an approved encrypted
path and must not be obtained by broadly exposing PostgreSQL.

PostgreSQL disaster-recovery evidence uses distinct disposable source and
target databases:

```powershell
make disaster-recovery-contract-gate
make postgres-disaster-recovery-seed
make postgres-disaster-recovery-drill
make postgres-disaster-recovery-resume
make disaster-recovery-proof-gate
```

`LOTUS_IDEA_DR_SOURCE_DATABASE_URL` and
`LOTUS_IDEA_DR_TARGET_DATABASE_URL` are runtime-only secret inputs and must
never appear in command arguments or evidence. The fixture refuses a non-empty
database. Logical backup evidence is real restore proof but always carries
`pitrProof=false`; production certification requires provider-owned physical
base-backup plus WAL evidence. Use `LOTUS_IDEA_RECOVERY_POSTURE=draining`,
`restoring`, `degraded`, or `normal` during cutover. Every non-normal or invalid
value fails readiness and durable writes before mutation.

The scheduled DR workflow must install a PostgreSQL client with the same major
version as its service database and verify both before backup. `pg_restore`
must receive an explicit target database; `PGDATABASE` alone does not select
restore mode. Backup/restore adapters must translate subprocess failures into
phase-specific diagnostics while redacting host, database, user, passfile, and
password values. Do not claim a DR workflow from contract tests alone: execute
it on `main`, inspect the uploaded evidence, and retain `not_certified` until
provider-owned physical/PITR, encryption, failover, and authorization evidence
exists.

Wiki check before merge when docs/wiki truth changed:

```powershell
..\lotus-platform\automation\Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-idea
```

Publish wiki only after merge to `main`:

```powershell
..\lotus-platform\automation\Sync-RepoWikis.ps1 -Publish -Repository lotus-idea
```

## Validation And CI Expectations

Every implementation slice should carry code, tests, contracts, docs/wiki truth,
and command evidence proportionate to risk.

Minimum local validation for a backend slice:

1. focused unit/integration tests for touched behavior,
2. `make typecheck`,
3. `make lint` or the relevant subset plus the affected contract gates,
4. `make documentation-contract-gate` when docs/context/wiki changed,
5. `make implementation-truth-gate` when current-state claims changed,
6. `make supported-features-gate` when support posture is mentioned,
7. `git diff --check`.

Run broader gates when shared infrastructure, API contracts, persistence,
security, CI workflows, or documentation surfaces are touched.

GitHub Actions remain the source of merge-check truth. Local green checks are
necessary but not enough for final closure.

Do not mark an RFC/support/docs context change complete until the durable truth
is on `main`, CI is green, wiki source is synchronized, and branch hygiene is
clean.

## GitHub Issue Learning Loop

When fixing a GitHub issue, inspect adjacent code for the same pattern.

Recent issue-derived patterns to preserve:

1. bounded PostgreSQL projections should replace whole-store snapshots for
   narrow read paths and aggregate readiness diagnostics,
2. inbound JSON body limits must be enforced on the actual ASGI body stream,
   not only `Content-Length`,
3. outbound HTTP retry/backoff must be centralized and idempotency-gated,
4. GitHub Security posture must be checked live before claiming current state,
5. deterministic runtime trust telemetry tests are `test_execution` evidence,
   must use explicit in-memory/non-durable posture, and must clear no runtime or
   certification blocker; product-level and aggregate readiness must stay
   semantically aligned,
6. conversion intent idempotency must have one owning key at the
   application/domain boundary; never allow repository replay evidence and the
   persisted governed intent to diverge,
7. repo-native aggregate CI commands must either include heavyweight
   PostgreSQL/Docker/release proof families or clearly name a separate full-lane
   command; do not let remote-only YAML proof become an invisible local gap,
8. inbound correlation and trace identifiers are untrusted input; pass them
   through the shared observability sanitizer before response, log, or
   downstream propagation,
9. caller-supplied capability, role, and entitlement headers are simulation
   inputs in local/test; production-like profiles require the shared trusted
   caller-context provenance guard before those headers can authorize routes,
10. aggregate proof artifacts must be generated from clean source before they
    can clear implementation-readiness blockers; dirty-tree or missing
    `sourceTreeDirty` provenance is diagnostic-only and must not add evidence
    refs or remove blockers.
11. PostgreSQL mutation paths need optimistic same-candidate guards and
    database idempotency-collision retry; full-snapshot mutation helpers must
    not silently overwrite stale state or leak raw primary-key collisions,
12. PostgreSQL snapshot replacement write helpers belong in
    `app.infrastructure.postgres_snapshot_writes`; do not add new
    snapshot/detail insert SQL back to `postgres_repository.py`. Preserve the
    distinction between full snapshot/admin/test/DR behavior and ordinary
    bounded request-path mutations/projections,
13. persisted AI explanation lineage writes need both API-level idempotency and
    domain request-id replay protection; same-key replay/conflict and
    distinct-key request-id conflict must remain separately tested,
14. AI explanation evaluation must use the single governed workflow-pack
    contract in `app.domain.ai_governance`: public request identity
    `lotus-ai:idea-explanation:v1` + version `v1` + evaluator
    `lotus-ai:governed-verifier:v1` maps deliberately to the proof identity
    `idea_explanation.pack@v1`; arbitrary caller-supplied pack identities must
    fail closed with product-safe `invalid_ai_workflow_pack` before candidate
    lookup or lineage persistence,
15. privileged operator run-once mutations need explicit operator run identity
   and idempotency before event claims or external side effects,
16. release evidence artifacts must name their scope, target artifact or
    dependency source, generator, path, and non-proof boundary before being cited
    as release proof,
17. runtime dependency SBOM evidence must come from the resolved runtime
    dependency closure in `requirements/runtime-resolved.lock.txt`, not from
    direct-only runtime requirements or an ambiguous CI environment; the
    supported-name `requirements/requirements.txt` exists only as a gated
    mirror for GitHub Dependency Graph support,
18. Python dependency updates must move root pins and runtime lock evidence
    through the governed `make dependency-refresh` path. Dependabot must not
    open a separate `/requirements` lock-only stream; lock refreshes should
    regenerate both `requirements/runtime-resolved.lock.txt` and
    `requirements/requirements.txt` from the active runtime closure before
    merge validation. Routine Dependabot version-update PRs are paused with
    `open-pull-requests-limit: 0` while RFC implementation is active; security
    alerts and security-update posture remain governed through the GitHub
    Security tab and `make github-security-posture-check`,
19. GitHub Actions shell commands that interpolate runtime environment values
    such as `${GITHUB_REPOSITORY}` or `${GITHUB_RUN_ID}` must quote the whole
    composed argument so workflow lint remains clean and CI signal evidence
    jobs do not accumulate avoidable ShellCheck annotations.
20. Docker build and scan evidence must be paired with bounded packaged-runtime
    startup and health-surface smoke proof before claiming release image
    confidence,
21. generated proof and quality evidence must be reproducible from current
    gate rules or be documented as on-demand evidence rather than current proof,
22. ignored report-only artifacts must not be cited as durable current-state
    proof unless a deterministic committed-artifact drift gate exists,
23. documentation should record the durable rule, not only the one-off fix,
24. supportability, readiness, health-state, and data-quality vocabulary must
    not be treated as freshness-current evidence unless a source-owned freshness
    field explicitly uses governed freshness vocabulary.
25. dashboard and alert source-contract validation should be pattern-backed with a
    machine-readable contract, concrete Grafana/Prometheus/runbook artifacts,
    proof gates, drift tests, and explicit non-proof boundaries. Runtime
    certification additionally requires environment-bound provisioning, query,
    rule-evaluation, delivery, and deployment evidence; do not rely on a metric
    catalog or static files alone for operator visibility claims.
26. mutating workflow idempotency must be true in both runtime behavior and
    OpenAPI contract truth. Routes that require `Idempotency-Key` should use the
    shared `app.api.idempotency` route list and validation helpers, and
    `make api-idempotency-boundary-gate` must fail optional or defaulted
    `Idempotency-Key` OpenAPI headers for certified idempotent mutations.
27. Docker runtime images should install the resolved runtime dependency lock
    before copying application source, then install the local service package
    with `--no-deps` after `COPY src`; `.dockerignore` must keep generated
    coverage, SBOM, quality-report, and proof-output artifacts out of Docker
    build context while explicitly re-including governed runtime assets that a
    Dockerfile copies. The scheduled worker contract must verify its complete
    image file closure, including the manifest and imported helper scripts;
    `make ci-contract-gate` must catch source-before-dependency-install
    ordering, dependency reinstall drift, Docker-context generated-artifact
    parity drift, and declared-but-unpackaged worker assets.
28. release images must be commit-tagged, CI-published only, signed, attested,
    and promoted by digest. Because an image cannot embed its own final
    registry digest without changing that digest, `lotus.image-identity.v1`
    separates OCI build identity from registry/deployment identity. The
    Dockerfile must carry OCI labels for service version, commit SHA, branch,
    build timestamp, repo URL, CI run ID, build ID, identity contract, and
    runtime release-manifest binding; it must never carry a fake self-digest.
    `/version` must expose null digest fields for unpublished local/PR images
    and the runtime-bound digest pair for published deployments. Production-like
    readiness fails closed when that pair is missing, malformed, partial, or
    mismatched. `release-evidence.json` must capture the registry digest,
    digest deployment reference, keyless signature subject, provenance
    attestation, SBOM attestation, scan evidence, and same-digest promotion
    policy. Main Releasability must run the exact digest image and cross-check
    OCI labels, `/version`, all subjects, and the Kubernetes reference through
    `make release-image-identity-contract-gate`; Docker ARG/ENV names must
    reject secret-like build inputs.
    Local Compose exposes the same seven non-secret identity inputs through
    `LOTUS_IDEA_BUILD_*`; canonical Workbench automation must populate them
    from exact Idea source/runtime truth. Default `unknown`/`local` values are
    diagnostic local posture only and cannot satisfy cross-repository proof.
    Compose must also configure the distinct Advise, Manage, and Report
    realization base/path pairs. Generic source-read URLs are not realization
    configuration; the CI Compose runtime contract blocks that substitution.
29. duplicate-implementation controls now split report-only evidence from
    blocking enforcement. `make duplicate-implementation-inventory` scans exact
    first-party function-body duplicates across `src/app` and `scripts`, writes
    no artifacts, and reports the inventory for review. `make
    duplicate-implementation-gate` runs the same scanner with
    `--fail-on-duplicates`, is wired into `make lint`, and blocks exact
    duplicate implementation clusters above the current zero-cluster baseline.
    The first follow-through consolidations moved repeated
    proof source-safety traversal into `scripts/proof_source_safety.py` and
    live-proof generator timeout/output plumbing and generated-at UTC parsing into
    `scripts/proof_generator_io.py`, and centralized proof timestamp,
    make-target evidence, and cross-repository file-evidence checks in
    `src/app/application/source_safe_cross_repo_proof.py`, plus AST call-name
    parsing in `scripts/ast_gate_helpers.py` and Core live-proof base URL
    resolution in `scripts/proof_generator_io.py`, removing known
    duplicate function-body clusters while preserving family-specific proof
    policy and generator argument behavior.
30. Report-only maintainability baselines are issue-discovery inputs, not
    permission to stop at the first local fix. When a Slice 19 hardening issue
    comes from a near-threshold proof, readiness, run-once, operator, or API
    orchestration function, run `make quality-baseline` with the blocking
    `make maintainability-gate` and `make duplicate-implementation-gate`, then
    inspect siblings in the same impact/lens family. Fix a high-confidence
    sibling in the same bounded batch or create a GitHub issue with exact
    function, line count, route/proof ownership, acceptance criteria, and
    no-promotion boundaries. Issues `#601`, `#603`, `#606`, `#609`, `#618`,
    `#620`, and `#623` are the current
    pattern: `build_service_capacity_baseline` moved from 130 to 64 lines,
    `post_outbox_delivery_run_once` moved from 129 to 71 lines, and
    `record_review_action` moved from 127 to 54 lines, and
    `evaluate_mandate_health_signal` moved from 127 to 15 lines while preserving
    source-safe blockers, entitlement semantics, no-supported-feature posture,
    and runtime topology. The same rule applies to test-support infrastructure:
    `FakePostgresCursor.execute` moved out of the largest-function list by
    delegating SQL families to named fake handlers while preserving row,
    transaction, `rowcount`, idempotency, and assertion semantics. The
    follow-through fake row helper split `row_for_insert` into table-owned row
    builders while preserving JSONB unwrapping, strict column/value validation,
    and unknown-table failure behavior. AI workflow-pack fixtures apply the
    same rule: keep public fixture helpers stable, move large source-contract
    and runtime-execution fake file catalogs behind capability-owned constants,
    and test the non-claim boundaries for external-publication authority,
    downstream authority, live provider, and supported-feature promotion. Issue
    `#625` carries the same bounded-helper pattern into the production
    concentration-risk signal evaluator: keep the public evaluator stable,
    split concentration source validation, issuer coverage, duplicate and
    materiality decisions, and candidate assembly into domain-owned helpers,
    and do not introduce a generic signal framework or unsupported
    concentration calculation / trade / rebalance authority. Issue `#633`
    applies the pattern to the bond-maturity Core adapter: keep the public
    `fetch_bond_maturity_evidence` port behavior stable, split Core
    `PortfolioMaturitySummary:v1` / `HoldingsAsOf:v1` source-fact validation
    and DTO assembly into adapter-owned helpers, preserve fail-closed source
    authority and currentness semantics, and do not implement Core changes,
    live Core certification, runtime topology, Gateway/Workbench, or supported
    feature claims. Issue `#636` applies the same proof-boundary rule to the
    Core portfolio-state runtime execution contract: keep
    `core_portfolio_state_runtime_execution_is_valid` as the stable public
    fail-closed validator, split proof envelope, request receipt, source
    receipt, source posture, hash identity, non-proof claims, and closure
    checks into proof-owned helpers, and do not treat the refactor as Core
    issue `sgajbi/lotus-core#790`, data-mesh, Gateway/Workbench, production,
    or supported-feature evidence.
31. Route-owned runtimes must consume their own cleanup hooks. Source-ingestion
    run-once builds Core HTTP clients through `SourceIngestionRuntime`; the API
    path must close the runtime after accepted or source-unavailable execution
    and must not rely on worker-only cleanup semantics. The same pattern applies
    to route-owned publisher adapters: outbox-delivery run-once must close the
    broker publisher it constructs after accepted, replayed, failed, or
    conflicting execution paths. Cleanup failures are supportability signals,
    not product outcomes: route-owned `close()` failures must be bounded to
    source-safe suppressed operation events and must not replace already
    computed completed, replayed, conflict, or blocked run-once responses.
32. Run-once source-ingestion manifests are intentionally small bounded
    operator actions. `maxItems` and raw `workItems` must stay at or below the
    code-owned 100-item ceiling; larger ingestion requires a separately
    designed chunked or scheduled workflow with capacity evidence.
33. Operation metric source-authority vocabulary must be code-owned. Runtime
    `OperationEvent`, operation metric contracts, operator workflow contracts,
    dashboards, and alert proof gates must consume the same governed
    `OPERATION_EVENT_SOURCE_AUTHORITIES` set instead of duplicating partial
    allowlists.
34. Keep context holistic. Detailed GitHub issue closure evidence belongs in
    `docs/architecture/GITHUB-ISSUE-CLOSURE-MATRIX.md` and is enforced by
    `make github-issue-closure-matrix-gate`; this context file should retain
    durable patterns, boundaries, commands, and routing rules instead of
    becoming a repeated per-issue evidence dump.
35. Data-lifecycle controls must cover every access path and terminal phase,
    not only the primary mutation. Direct detail and downstream lookups must
    exclude erased/purged aggregates; new delivery claims must share the
    lifecycle lock; erasure must pseudonymize both prior audit actors and the
    erasure operation itself; purge must recover tenant authority from the
    immutable terminal control after payload scope is redacted; and trust
    telemetry must separate active products from tombstone posture. Persist
    sanitized correlation and trace on the immutable operation rather than
    treating request logs as durable audit. Pin these
    invariants with real PostgreSQL restart and concurrency tests.
36. Retention references are authority-bearing contract values. Never accept a
    caller-chosen non-blank value as policy. Map only versioned, governed
    external references to local policy, fail closed for unknown values, and
    keep legal/privacy approval outside Lotus Idea.
37. Blocker-clearing proof must declare exactly one evidence class:
    `source_contract`, `test_execution`, `ci_execution`, `runtime_execution`,
    `deployment`, or `production_certification`. File presence, Make target
    text, and workflow narrative are source-contract evidence, not execution.
    CI execution evidence must bind the repository, trusted workflow and job,
    run id and attempt, exact commit and ref, successful conclusion, and
    uploaded artifact digest. Keep this taxonomy in a domain package and each
    proof builder in its own application capability package; do not create a
    separate runtime service without workload or failure-isolation evidence.
    Cross-repository source contracts must also close top-level and nested
    fields, bind each producer/consumer authority by repository/ref/SHA-256,
    bind the ordered authority collection to a canonical digest, and name any
    consumer-only validation scope as an invalid full proof. Do not infer
    mainline certification eligibility from file presence or token scans.
38. Durable repository proof is owned by the bounded
    `app.application.durable_repository_proof` package, with contract, JUnit
    receipt mapping, and builder modules. Its entrypoints live under
    `scripts/persistence/`, and repository hygiene blocks the retired flat
    paths. The two aggregate persistence blockers require an exact-main,
    digest-bound PostgreSQL CI receipt with the complete governed assertion
    set; source files, Make targets, job names, PR refs, stale/future receipts,
    and mismatched commits fail closed. This evidence does not certify a
    deployed production database or promote a supported feature.
    Generic artifact-digest normalization, JUnit assertion extraction, and
    receipt JSON loading are shared through `app.application.ci_execution_evidence`
    and `scripts.proof_generator_io`; capability packages retain only their
    own trusted workflow, assertion, blocker, and no-claim policy.
39. Source-ingestion v2 evidence is `runtime_execution` only when the
    capability-owned `source_ingestion_runtime_evidence` policy validates
    actual application-use-case results. Require exact current Core product
    refs, accepted/replayed-only decisions, one persisted-record receipt per
    work item, source-evidence hash reconciliation, source-safe scope binding,
    durable storage, and current aggregate provenance. Self-asserted success
    booleans, summary counts, in-memory runs, mixed decisions, missing records,
    unknown fields, and claim inflation clear no blocker. Keep the generator
    and gate under `scripts/source_ingestion/`; repository hygiene prohibits
    the retired flat v1 paths. This is design modularity within the existing
    API/worker deployable and shared Idea PostgreSQL boundary, not a new
    service or database.
40. Integration and E2E API clients must be created through
    `tests.support.http.managed_test_client`. The autouse integration and E2E
    fixtures own application lifespan and deterministic client shutdown per test;
    direct FastAPI or Starlette `TestClient` construction is blocked by
    `make test-client-lifecycle-gate` through `make lint`. This prevents
    cumulative event-loop socket exhaustion on Windows and ensures shutdown
    hooks are exercised without scattering cleanup logic across test modules.
41. Platform-mesh event contracts, declared consumers, source-manifest entries,
    and generated catalog entries are `source_contract` evidence. They may add
    provenance to outbox readiness but must not clear
    `platform_mesh_event_publication_proof_missing` or claim runtime execution,
    event publication, a publication receipt, deployment, production
    certification, downstream delivery, or supported-feature promotion. Keep
    this proof family under capability-owned `outbox/platform_mesh/` packages;
    repository hygiene prohibits the retired flat publication-proof paths.
42. Lotus AI workflow-pack phase specs, registry seed declarations, bindings,
    queue policy, supportability source, and tests are `source_contract`
    evidence. Keep this family under capability-owned
    `ai_workflow_pack_registration/` application, script, and test packages.
    A valid artifact adds provenance only and must retain
    `workflow_pack_runtime_contract_not_certified`; it cannot claim runtime
    registry observation, deployment, production certification, provider
    execution, Workbench proof, client publication, or feature promotion.
43. A sibling Report contract and static route declaration are
    `source_contract` evidence, not live intake proof. Keep the application
    policy, thin generator, gate, and focused tests under capability-owned
    `report/` packages. A valid artifact adds provenance only, clears no
    blocker, and must preserve `lotus_report_live_intake_route_proof_missing`.
    Live proof requires machine-verifiable serving, authorization, tenant
    isolation, and request-execution evidence from the owning Report runtime.
    Never infer materialization, render, archive, publication, certification,
    or supported-feature posture from route declarations.
44. A sibling Report materialization contract is also `source_contract`
    evidence, even when that sibling contract declares an implemented route or
    records report-owned execution claims. Keep this family under the
    capability-owned `report/` application, script, and test packages. The v2
    artifact may add a source-safe evidence reference, but it clears no blocker
    and must preserve materialization execution, rendered-output creation,
    archive-record creation, retention/legal-hold, client-publication,
    certification, and promotion posture. Its validator rejects additional
    runtime or authority claim fields. Only machine-verifiable execution
    evidence from the owning Report/Render/Archive runtime can change those
    blockers; source declarations must never be projected into a current target
    route, readiness status, or supportability status.
45. The Idea Report consumer may submit the Report materialization route only
    after resolving the evidence pack's persisted candidate record. Project
    only the trusted `portfolio_id`; do not add raw scope to audits, public
    DTOs, or persisted evidence packs. Require all source summaries to carry
    the same valid business date and require the candidate tenant to match the
    server-configured local/test Report fixture before HTTP I/O. The fixture
    uses only `tenant-sg` / `APAC` / `json`, never browser-supplied identity or
    scope, and fails closed outside `local` and `test` until `#380` production
    identity prerequisites are available. This consumer mapping is not Report
    job, Render, Archive, publication, or supported-feature evidence.
46. Platform source-manifest and generated-catalog inclusion are
    `source_contract` claims. Keep this family under capability-owned
    `data_mesh/` application, script, and test packages. Bind each authoritative
    sibling platform input by repository, ref, and SHA-256, reject unknown
    fields, and allow a valid current artifact to satisfy only
    `platform_source_manifest_inclusion_missing` and
    `platform_catalog_inclusion_missing`. It cannot prove platform runtime
    publication, mesh certification, producer activation, policy
    certification, Gateway/Workbench discovery, deployment, production
    certification, or supported-feature promotion. This remains design
    modularity inside the existing Lotus Idea deployable.
47. Deterministic workflow lint must not depend on GitHub pull-request diff
    availability. Configure the pinned actionlint action with a blocking local
    reporter. CI signal evidence must consume only authoritative upstream job
    conclusions from the native GitHub Actions `needs` context, discard all job
    outputs, and avoid a same-run jobs API dependency. Failed, cancelled, or
    malformed upstream results remain hard failures and must never be converted
    into ignored or synthetic success evidence.

Recent GitHub issue categories should keep being worked category-wise so
repeated defect patterns are fixed once and pinned with tests or gates:

1. Migration/data durability coverage: GitHub issue `#274` was fixed by PR
   `#280` by expanding migration contract coverage for downstream submission
   state, resource lookup indexes, and rollback truth.
2. CI lane hygiene and release evidence: GitHub issue `#275` was fixed by PR
   `#280` by keeping artifact-producing implementation-proof readiness
   generation out of fast `make lint` while preserving explicit release/review
   evidence commands.
3. Repo context truth: GitHub issue `#278` was fixed by PR `#280` by curating
   this file to current mainline issue posture instead of branch-local closure
   claims.
4. Runtime supply-chain evidence: GitHub issue `#279` is addressed by the
   runtime-resolved lock plus `runtime-dependency-closure-gate`, so release
   SBOM and dependency audit evidence cover transitive runtime dependencies
   rather than only direct requirements. The gate also keeps the GitHub
   Dependency Graph requirements manifest mirrored to the resolved runtime lock
   so Security-tab graph updates stay parseable.
5. Operator observability source contract: GitHub issues `#282` and `#412` are
   addressed by the non-AI operator workflow operations contract and proof
   gates, which validate source-safe dashboard, alert-rule, runbook, and
   fixture artifacts over implemented telemetry. Static evidence clears no
   aggregate blocker and does not prove provisioning/query execution, rule
   loading/evaluation/delivery, deployment, or production behavior.
6. Aggregate operator workflow proof consumption: GitHub issue `#292` is
   addressed by a distinct `operator-workflows-operations` implementation-proof
   readiness capability, CLI/env/API proof-artifact consumption, and regression
   tests that add the source-contract proof reference while retaining operator
   dashboard/alert runtime, live-source, external-broker, downstream execution,
   Gateway/Workbench, data-mesh, and supported-feature blockers unless their
   owning runtime or authority proof artifacts are also present.
7. Outbox delivery operability: GitHub issue `#297` is addressed by durable
   outbox failure timing and next-attempt eligibility state. Failed rows below
   the retry limit are not claimable until `next_attempt_at_utc` is due,
   expired lease recovery remains immediate, retry backoff is deterministic and
   capped, PostgreSQL readiness counts only due failed rows as
   delivery-ready, and tests cover immediate no-reclaim behavior plus
   first/last failure timestamp preservation across retry leases.
8. Signal-evaluation least privilege: GitHub issue `#301` is addressed by
   requiring both advisor role and `idea.signal.evaluate` capability in the
   shared signal API support helper, adding role-only/capability-only/wrong
   role/wrong capability/scoped-denial tests, and extending
   `make signal-api-contract-gate` so future signal-route slices cannot
   reintroduce role-or-capability authorization.
   The same least-privilege pattern is now applied to adjacent advisor-facing
   candidate detail and review queue reads: both routes require the published
   `idea.*` read capability plus the allowed product role, regression tests
   reject advisor role-only requests with product-safe 403 responses, and
   `make caller-context-contract-gate` blocks future API modules from pairing
   `allowed_roles` with an `idea.*` capability and the weaker
   `require_capability` helper.
9. OpenAPI caller-context publication: GitHub issue `#302` is addressed by
   adding `app.api.caller_context_openapi` as the centralized generated-OpenAPI
   contract for protected caller-context requirements, publishing
   `LotusCallerContext` security plus `x-lotus-caller-context` required
   capability/role/provenance metadata, and extending
   `make endpoint-certification-gate` so certified endpoints with `idea.*`
   capabilities cannot omit matching OpenAPI caller-context publication.
10. Downstream submission idempotency lookup: GitHub issue `#303` is addressed
    by moving `PostgresIdeaRepository.downstream_submission_by_idempotency_key`
    to a bounded `idea_downstream_submission` primary-key query, reusing a
    shared row decoder, and adding PostgreSQL query-shape tests that prove the
    replay/conflict precheck avoids candidate, outbox, conversion, report
    evidence-pack, and AI-lineage tables.
11. Review/conversion idempotency prechecks: GitHub issue `#317` is addressed
    by moving `PostgresIdeaRepository.precheck_review_mutation` and
    `precheck_conversion_mutation` to a bounded `idea_idempotency_record`
    lookup plus candidate-detail projection for the associated candidate only.
    Review, feedback, and conversion-intent replay/conflict decisions must not
    hydrate whole repository snapshots or unrelated outbox/downstream tables.
12. Review/feedback trusted entitlement scope: GitHub issues `#318` and `#386`
    are addressed by binding review-action and feedback mutation actor scope to
    trusted `X-Caller-Tenant-Ids`, `X-Caller-Book-Ids`,
    `X-Caller-Portfolio-Ids`, and `X-Caller-Client-Ids` headers. Review and
    feedback request bodies expose neither `accessScope` nor `authorizedScope`;
    the application loads persisted candidate scope and the domain evaluates it
    against trusted caller entitlements. Missing, partial, or mismatched headers
    fail closed across every dimension with product-safe permission denial and
    no raw portfolio/client disclosure.
    Audience-specific queue routing from GitHub issue `#385` makes
    advisor, portfolio-manager, and compliance audience part of the domain,
    application, repository, PostgreSQL, snapshot, and API contracts. Business
    queues select only their responsible review posture. The operator endpoint
    returns aggregate support-exception counts by audience and never ranks work
    or grants review/compliance authority. Process-local and PostgreSQL readiness
    counts apply the same audience predicate. This remains design modularity
    inside the existing service, not a separate queue process.
13. Dirty aggregate proof rejection: GitHub issue `#306` is addressed by
    requiring aggregate proof provenance to carry `sourceTreeDirty=false`
    before `aggregate_proof_artifact_is_current()` can return true. Dirty or
    missing dirty-flag provenance now preserves blockers, suppresses the
    artifact evidence ref, and remains diagnostic-only until regenerated from
    clean source.
14. PostgreSQL readiness degradation: GitHub issue `#307` is addressed by
    returning product-safe `503 degraded` readiness with
    `durable_repository_unavailable` when a production-like runtime has a
    configured PostgreSQL URL that cannot initialize. Readiness must not leak
    DSNs, hostnames, credentials, driver errors, or raw connection details.
15. Downstream submission OpenAPI ProblemDetails truth: GitHub issue `#308` is
    addressed by publishing downstream submission 404/409/503 runtime
    `ProblemDetails` codes under both `application/json` and
    `application/problem+json`, using shared merged metadata for multi-code
    statuses, and extending the OpenAPI ProblemDetails gate so signal and
    workflow routes cannot reintroduce media-type drift.
12. Resilience retry control: GitHub issue `#286` is addressed by fixed central
   jitter in `DownstreamJsonClient` computed backoff delays, deterministic
   jitter injection in tests, and no change to retry attempts, retryable status
   codes, valid `Retry-After` handling, POST idempotency rules, or adapter-local
   retry-loop boundaries.
13. PostgreSQL review-queue performance: GitHub issue `#287` is addressed by
   narrow expression indexes for the advisor review queue tenant/book/
   portfolio/client access-scope JSONB predicates, migration rollback coverage,
   `migration_contract_gate.py` required-index enforcement, and PostgreSQL
   queue tests that prove scoped count/page reads retain eligibility filters,
   stable ordering, and `LIMIT`/`OFFSET` bounds without changing advisory
   workflow ownership or API semantics.
14. Dependency update atomicity: GitHub issue `#289` is addressed by removing
    the separate `/requirements` Dependabot stream, grouping Python root updates
    as dependency-closure root changes, adding `make dependency-refresh` to
    install from root pins and regenerate both runtime lock files, and protecting
   the workflow through security/CI contract tests. Routine Dependabot
   version-update PRs are paused during RFC delivery; dependency suggestions are
   manually regenerated or cherry-picked into the active implementation branch
   before normal repo-native gates. Existing install,
   runtime-closure, audit, Docker, SBOM, and release evidence gates remain
   strict.
15. Lifecycle vocabulary authority: GitHub issue `#290` is addressed by
   quarantining downstream-authority lifecycle statuses from caller-settable
   lifecycle transitions. The API request contract uses a caller-settable
   lifecycle enum that excludes `accepted` and `executed`, the domain graph no
   longer permits new transitions into those downstream-authority statuses, and
   the application command rejects them before repository mutation or outbox
   emission. Conversion outcomes and downstream submissions remain the
   source-authority paths for downstream acceptance posture.
15. Idempotency OpenAPI truth: GitHub issue `#291` is addressed by the shared
    idempotency OpenAPI contract override and boundary gate, which require
    certified mutating idempotency routes to publish `Idempotency-Key` as a
    required header with no default while preserving product-safe runtime
    validation behavior.
16. CI signal feedback-time truth: GitHub issue `#293` is addressed by keeping
    report-only CI signal evidence source-safe while distinguishing workflow
    feedback time from longest individual job duration. `criticalPathSeconds`
    now uses first-job-start to last-job-completion wall-clock time, with
    `workflowWallClockSeconds` recording the same feedback-time basis and
    `longestJobName`/`longestJobSeconds` retaining the optimization signal.
    `thresholdEnforced` remains false and no duration threshold is promoted.
17. Docker cache-aware release builds: GitHub issue `#295` is addressed by
    moving resolved runtime dependency installation ahead of `COPY src`,
    installing the local package afterward with `--no-deps`, and extending the
    release-evidence contract/tests to reject source-before-dependency-install
    ordering or dependency reinstall drift. Docker build, runtime smoke,
    container scan, and runtime SBOM evidence remain intact.
18. Docker build context parity: GitHub issue `#310` is addressed by aligning
    `.dockerignore` with generated/local artifact policy for coverage XML,
    release SBOM, generated quality reports, and proof output, while extending
    `make ci-contract-gate` to reject Docker-context generated-artifact parity
    drift. This does not rewrite the Dockerfile or require deleting local proof
    artifacts before every Docker build.
19. Source-ingestion run-once resource lifecycle: GitHub issue `#312` is
    addressed by closing `SourceIngestionRuntime` from the operator run-once API
    after both accepted and source-unavailable batch executions. Configuration
    blockers that never construct a runtime remain unchanged, and the route does
    not certify live Core ingestion or supported-feature readiness.
    The same issue-derived pattern is applied to outbox delivery: the
    outbox-delivery run-once API now closes its route-owned broker publisher
    after execution begins, preventing HTTP client resource leakage without
    certifying live broker publication. GitHub issue `#314` extends the pattern
    by making cleanup best-effort and observable: source-ingestion runtime close
    failures emit `runtime_cleanup_failed`, outbox publisher close failures emit
    `publisher_cleanup_failed`, and both use `suppressed` operation events
    without masking completed, replayed, conflict, or bounded blocked product
    responses.
20. Source-ingestion run-once batch ceiling: GitHub issue `#313` is addressed
    by enforcing a code-owned 100-item ceiling over both manifest `maxItems` and
    raw `workItems`, returning `source_ingestion_batch_limit_exceeded` before
    Core calls or repository mutation. Larger ingestion remains a future
    chunked/scheduled workflow with capacity evidence, not a run-once manifest
    escalation.
21. Duplicate implementation inventory: GitHub issue `#296` is addressed by a
    repo-native `make duplicate-implementation-inventory` command that reports
    exact duplicate function-body clusters across `src/app` and `scripts`
    without writing artifacts. The initial baseline
    scanned 1,750 functions at the six-line threshold and reported 31 exact
    clusters, including the known proof source-safety validation helper
    families. The first follow-through refactors centralize proof source-safety
    traversal in `scripts/proof_source_safety.py` and live-proof generator
    timeout/output plumbing plus generated-at UTC parsing in
    `scripts/proof_generator_io.py`, then consolidate proof timestamp
    validation, make-target evidence checks, and cross-repository file-evidence
    checks through
    `src/app/application/source_safe_cross_repo_proof.py`, and centralize AST
    call-name parsing for contract gates in `scripts/ast_gate_helpers.py`, and
    centralize Core live-proof base URL resolution in
    `scripts/proof_generator_io.py`, and centralize Advise/Manage proof
    evidence request construction in `scripts/proof_request_builders.py`, and
    centralize mutating API reason-code validation in
    `app.api.request_validation`, and centralize bounded API telemetry count
    buckets in `app.api.telemetry_buckets`, and centralize caller-supplied
    signal response DTO projection in `app.api.signal_models.SignalEvaluationResponse`,
    and centralize application-layer portfolio-only signal review scopes in
    `app.application.access_scope`, and centralize source-reference/access-scope
    write-side payload projection in `app.ports.evidence_payloads`, and
    centralize API persistence-summary response projection in
    `app.api.persistence_summary`, and centralize API review access-scope DTOs
    in `app.api.access_scope_models`, and centralize blocked signal-result
    construction in `app.domain.signal_evaluation.blocked_signal_result`, and
    centralize optional proof-artifact JSON object loading in
    `app.runtime.proof_artifact_files`, and centralize source-product proof
    payload text-sequence normalization in
    `app.application.source_product_proof_values`, and centralize outbox
    contract forbidden-text traversal in `scripts.contract_text_guards`, and
    centralize operations-contract payload, operation, and label validation in
    `scripts.operations_contract_validators`; GitHub issue `#614` keeps the
    report-only quality baseline aligned with the blocking scanners by using
    the same pass/ellipsis-only protocol-stub classifier before reporting
    executable function rows and by emitting POSIX-normalized report paths for
    deterministic Windows/Linux evidence. The current local generated quality
    baseline reports 9,252 executable source/test/script function rows, and the
    current duplicate implementation gate reports 0 exact duplicate clusters
    across 2,953 source/script functions. GitHub issue `#309` promotes the same
    deterministic scanner to a blocking `make duplicate-implementation-gate`
    with `--fail-on-duplicates`, wired into `make lint` while preserving
    `make duplicate-implementation-inventory` as the no-artifact report-only
    evidence command.
    `make ci-contract-gate` protects the report-only/blocking target split,
    strict flag, and `make lint` lane placement.
22. Operation metric source-authority vocabulary drift: GitHub issue `#311` is
    addressed by moving the operation-event source-authority set into
    `src/app/observability/logging.py`, accepting every code-owned
    `SourceSystem` label plus `lotus-idea` and aggregate `source-owned`, and
    rejecting ungoverned labels before logs or metrics are emitted. The
    operation metric contract, operator workflow operations contract, and
    dashboard/alert proof checks now validate against the same runtime-owned
    vocabulary so future observability changes cannot reintroduce partial
    hardcoded allowlists.
23. Trusted Core tenant propagation: GitHub issue `#335` is addressed by
    requiring exactly one trusted caller tenant for Core-backed source routes,
    carrying that value through API DTO mapping, application commands, Core
    source request ports, and the infrastructure adapter, and requiring
    `tenantId` in the source-ingestion worker manifest. Core live-proof CLIs
    require `--tenant-id` and pass it through the same request ports; the
    signal API contract gate protects both routes and certification scripts.
    Successful Core-backed candidates retain tenant in access scope and stable
    candidate identity; generated ingestion identity is tenant-bound as well.
    The adapter no longer hard-codes `default`, and `unknown` remains only a
    non-Core unconstrained portfolio-scope sentinel that is never sent to Core.
    Tenant A/B propagation and identity tests, worker/proof tests, and
    fail-closed missing, ambiguous, untrusted-header, and request-body override
    tests protect the boundary. This is design modularity within the existing
    process and does not justify a new runtime service.
24. Caller-context ProblemDetails truth: GitHub issue `#336` is addressed by
    using `ProblemDetailsHTTPException` for shared caller-context dependency
    failures and preserving approved status, code, title, detail, and bounded
    diagnostic category through the global HTTP handler. Blank entitlement
    headers return `400 invalid_request`; missing trusted provenance returns
    `403 permission_denied`; runtime responses use
    `application/problem+json`, carry the sanitized `X-Correlation-Id`, and do
    not expose raw header or scope values. Generated OpenAPI injects both
    caller-boundary examples under `application/json` and
    `application/problem+json` for every protected operation. Representative
    signal, lifecycle, review, AI, report, and readiness tests protect the
    cross-route behavior; the caller-context contract gate protects the
    exception, handler, OpenAPI, and media-type layers. Unrelated framework
    exceptions retain the generic `request_rejected` fallback. This is a
    shared in-process API boundary, not a separately scalable runtime service.
25. Governed outbox dead-letter recovery: GitHub issue `#337` is addressed by
    the `app.domain.outbox.recovery` bounded module, application use case,
    `OutboxRecoveryRepository` port, in-memory/PostgreSQL adapters, migration
    `004`, and operator routes. Recovery preserves original failure history,
    creates a new fenced lease, permits one publication attempt, and leaves
    poison or unsupported events quarantined. PostgreSQL resolves the opaque
    support reference through an exact immutable SHA-256 expression index; it
    does not scan or lock an arbitrary recent-row window. The shared delivery
    claim qualifies its `RETURNING` projection so the real PostgreSQL
    `UPDATE ... FROM` path remains executable. `make outbox-recovery-contract-gate`
    blocks bounded-scan regressions, and the required PostgreSQL runtime lane
    proves dead-lettering, connection reload, exact recovery claim, durable
    audit replay, and migration rollback/reapply. This is design modularity
    within the existing process, not a new recovery service or broker claim.
    blocks sensitive response fields and unbounded re-drive regression. This is
    design modularity inside the existing deployable service; no workload,
    failure-isolation, ownership, or operability evidence justifies another
    runtime service. Broker, consumer, mesh, Gateway/Workbench, and supported
    feature proof remain separate blockers.
26. Candidate lifecycle/review-posture compatibility: GitHub issue `#330` is
    addressed by `app.domain.candidate_state` policy
    `idea-candidate-state-v1`. `IdeaCandidate` construction, PostgreSQL JSON
    rehydration, lifecycle transitions, and every review action use one golden
    compatibility matrix. Terminal transitions normalize to non-actionable
    posture; contradictory legacy rows are copied to
    `idea_candidate_state_quarantine`, excluded from queue/readiness as
    `invalid_state`, and blocked on new writes by migration `005`. Review API
    conflicts expose stable ProblemDetails plus source-safe candidate state and
    policy telemetry. This is internal design modularity in the existing
    process; no workload, isolation, ownership, or operability evidence
    justifies a separate runtime service.
27. Review and feedback resource identity: GitHub issue `#327` is addressed by
    `ReviewMutationIdentity`, application prechecks before domain mutation, and
    repeated in-memory/PostgreSQL adapter enforcement. `reviewId` and
    `feedbackId` bind candidate, evidence, actor, event, reasons, and time
    independently of `Idempotency-Key`. Equivalent content under a new key
    replays; changed content returns `review_identity_conflict`. PostgreSQL
    claims resource identity before candidate/audit/outbox writes and retries a
    collision from fresh state. `make review-identity-contract-gate` prevents
    ordering and API-contract regression. This remains internal design
    modularity; no runtime split is justified.
28. Conversion outcome identity and lifecycle: GitHub issue `#326` is addressed
    by `idea-conversion-outcome-v1`, application prechecks, repeated provider
    enforcement, and migration `006`. `conversionOutcomeId` is independent of
    `Idempotency-Key`; `sourceEventVersion` orders one intent stream; terminal
    corrections are append-only and linked. PostgreSQL claims identity/version
    before audit/outbox effects and retries a collision from fresh state.
    Contradictory legacy streams are preserved in the source table, copied to
    quarantine, denied a current posture, and excluded from readiness. `make
    conversion-outcome-contract-gate` prevents layer, atomicity, migration, and
    OpenAPI regression. This remains internal design modularity; downstream
    services retain outcome authority and no runtime split is justified.
29. Outbox event lineage: GitHub issue `#328` is addressed by the
    framework-neutral `EventLineageContext`, shared API request mapper, typed
    application commands, repository ports, in-memory/PostgreSQL adapters,
    migration `007`, and publisher envelope. Correlation and trace are required
    and distinct; causation is optional and valid only for a parent event or
    workflow. Request retries with a new trace replay the original durable
    event without rewriting lineage. Bounded system calls derive deterministic
    non-null lineage, while legacy rows are sanitized without event deletion.
    `make outbox-event-contract-gate` and `make outbox-consumer-contract-gate`
    protect all seven mutation families and consumer replay semantics. This is
    design modularity inside the existing runtime; no broker, consumer,
    Gateway/Workbench certification, supported-feature promotion, or runtime
    split is justified.
30. Outbox supportability telemetry: GitHub issue `#329` is addressed by the
    bounded readiness age projection, scrape-time collector, code-owned alert
    thresholds, fixed-label contract, actual-state dashboard panels, sustained
    Prometheus rules, and `promtool` healthy/breach fixtures. Collection
    failure is explicit, request-volume telemetry stays separate, and no event
    or private-banking identity becomes a metric label. This remains internal
    design modularity; no separately scalable runtime is justified.
31. Supported-feature promotion reconciliation: GitHub issue `#331` is
    addressed by `app.application.supported_feature_promotion`, which owns the
    structured registry and 90-day review-freshness policy used by both the CLI
    gate and implementation-proof readiness. Invalid or stale evidence cannot
    count as promoted; API and generated artifacts project the typed result,
    and `make supported-feature-promotion-contract-gate` prevents independent
    status counters or hard-coded output from returning. This is internal
    design modularity with no runtime split or current feature promotion.
32. Durable downstream handoff recovery: GitHub issue `#334` is addressed by
    a claim-before-call state machine, lease-fenced finalization, deterministic
    opaque support references, append-only audit history, and operator-only
    reconciliation. Timeout, 5xx, malformed response, transport ambiguity,
    lease loss, and local finalization failure never trigger an automatic
    second external call. PostgreSQL serializes claims with conflict-tolerant
    insert plus exact locked lookup; the required real-database lane proves
    concurrency, restart, connection-failure recovery, and exact mutation
    replay. Keep domain, provider, orchestration, transport, and API modules
    separate inside the current runtime; no service split or downstream
    authority claim is justified.

Recently closed by PR `#273` and mainline validation:

1. GitHub issues `#250` through `#272` were fixed by PR `#273`, merged to
   `main` at `41ac1524a4d4a06a64c88236ff7095cb60d7e1f6`, validated by green
   GitHub mainline checks and local `make ci`, and closed with issue evidence
   on 2026-07-01.
2. The fixed categories included Docker/runtime hardening, GitHub Security-tab
   posture, CI/release evidence, source-authority freshness semantics,
   bounded repository queries, downstream retry/idempotency, request-size and
   correlation header controls, stale PostgreSQL snapshot protection, outbox
   operator identity, coverage enforcement, and SBOM/runtime-artifact binding.

Do not close or claim issue progress until implementation, meaningful tests,
docs/context truth, merge to `main`, CI evidence, and QA or issue-closure
evidence exist. Keep issue count under control by fixing classes of defects
rather than isolated symptoms.

## RFC And Documentation Rules

RFCs are the governed implementation plan. The active suite lives under
`docs/rfcs/`.

Before RFC, documentation, wiki, context, contract, supported-features,
API-governance, migration, or CI-workflow work, run stranded-truth
reconciliation:

```powershell
git fetch origin --prune
git branch -r --no-merged origin/main
```

Inspect unmerged remote branches that touch durable governance paths and
classify them as `must-merge`, `cherry-pick`, `superseded`, `delete`, or
`active`.

Do not strand durable truth on side branches.

Every RFC slice that exposes behavior must update, as applicable:

1. endpoint certification,
2. OpenAPI evidence,
3. operation events and observability contracts,
4. data-mesh contracts,
5. supported-feature posture,
6. runbooks and wiki source,
7. repository context when local implementation patterns changed,
8. tests that prove both success and fail-closed behavior.

Endpoint implementation quality and endpoint certification status are
independent controls. Public business/operator operations marked
`implemented_not_certified` must still carry the same capability,
caller-context, product-safe error, operation-event, integration-test, and
OpenAPI evidence required of certified operations. They must additionally
declare machine-readable external certification blockers and preserve
`certificationStatus=not_certified` plus
`supportedFeaturePromoted=false` in ledger and generated success examples.
`planned` and `not_applicable` are not valid substitutes for an implemented
public operation.

For certified readiness and supportability endpoints, schema-valid examples
are insufficient. Prefer a deterministic no-I/O API response factory over a
parallel hand-written Swagger object, and compare the complete code-owned
default response against both the endpoint ledger and generated OpenAPI.
Issue `#526` applies this contract to AI explanation readiness so claim
grounding fields and model-risk runtime blockers cannot drift independently.
Repository-dependent values remain explicit factory inputs rather than
normalized-away differences.

For any certified endpoint with materially different executable success
families, publish one complete named example per family from a DTO-validated
code-owned factory and require exact factory, endpoint-ledger, and generated
OpenAPI equality. Preserve explicit nulls and control fields; when framework
generation drops them, apply a bounded post-generation injection from that
same factory. Public enum values require an executable constructor, route
outcome, and behavioral test. Issue `#529` applies this contract to all six AI
explanation evaluation success families and removes two legacy verifier states
that had no executable behavior.

Issue `#545` applies the same contract to candidate-state APIs. Keep lifecycle
`accepted` and idempotent `replayed` modes in one capability-owned factory, and
keep evidence replay `matched`, `hash_mismatch`, `stale_source`, and `expired`
modes in the same candidate-state package. The endpoint ledger, generated
OpenAPI, DTO serialization, and cited integration behavior must remain exactly
equal. Degraded supportability postures that intentionally return HTTP 200 are
not optional examples. Preserve no-source-payload, no-downstream-authority, and
no-supported-feature-promotion fields. This is internal design modularity; no
runtime split is justified without workload, failure-isolation, ownership, or
operability evidence.

Issue `#548` applies the contract to the high-cash signal family. The caller
and source-backed evaluation routes must each publish candidate-created,
blocked, suppressed, and not-eligible modes from application-backed,
DTO-serialized factories. Evaluate-and-persist must additionally distinguish
accepted, replayed, and duplicate-candidate decisions, while blocked,
suppressed, and not-eligible outcomes retain `persistence=null`. Keep the
factory under `app.api.examples.high_cash_signal`, keep the endpoint gate as a
thin parity adapter, and cite HTTP behavior for every mode. Do not hand-code
cash weight, candidate identity, evidence hash, retry decisions, or response
projection in documentation fixtures. Core remains the source authority, and
this contract proof does not certify live source runtime or promote support.

Issue `#551` applies the same contract to the low-income /
liquidity-shortfall signal family. Keep caller and Core-backed
`candidate_created`, `blocked`, `suppressed`, and `not_eligible` modes in
`app.api.examples.low_income_signal`; build them through the existing
application use cases and serialize the real response DTO. Candidate examples
must retain both governed Core cash-movement and cashflow-projection source
products while redacting route and content-hash fields. Use
`app.api.examples.signal_evaluation` only for source-reference fixture and DTO
serialization mechanics shared across signal families; domain thresholds,
source evidence, outcome selection, and authority boundaries stay with each
capability owner. Require exact factory/OpenAPI/ledger/test parity and HTTP
proof for every mode, including source runtime cleanup. This is internal design
modularity, not evidence for a signal microservice or supported-feature
promotion.

Issue `#555` applies the same contract to the bond-maturity / reinvestment
review family. Keep caller and Core-backed `candidate_created`, `blocked`,
`suppressed`, and `not_eligible` modes in
`app.api.examples.bond_maturity_signal`; build them through the application
use cases and serialize the real response DTO. Preserve both Core holdings and
maturity-summary lineage in candidate examples while redacting source routes
and hashes. Core remains authoritative for holdings and maturity facts; Idea
must not infer schedules, recommend replacement products, decide suitability,
or claim execution authority. Require exact factory/OpenAPI/ledger/test parity
and HTTP proof for every mode. This is internal design modularity and does not
justify a signal microservice or supported-feature promotion.

## Supported-Feature Promotion Rule

The supported-feature registry is source truth for support posture.
`features[]` is reserved for implemented supported-feature entries only.
Planned capability posture belongs under `planned_capabilities[]`; planned or
not-applicable records under `features[]` must not clear implementation-proof
readiness blockers or imply support.

Do not promote a feature unless the implementation has:

1. code,
2. tests,
3. source authority proof,
4. API/OpenAPI certification,
5. operation and security evidence,
6. runtime proof artifacts,
7. docs and wiki truth,
8. CI proof on the branch and after merge,
9. explicit promotion decision.

Internal API foundations, proof-readiness diagnostics, generated proof
artifacts, or route-proof consumption are not enough by themselves.

## Private-Banking Domain Correctness Rules

Use private-banking vocabulary precisely:

1. "candidate" means a reviewable idea, not advice,
2. "evidence" means source-provenanced support for why the candidate exists,
3. "intent" means a local request to hand off reviewed posture, not downstream
   acceptance,
4. "outcome" must come from the owning downstream source authority,
5. "ready" must not be used as a synonym for certified support unless the
   supporting proof says so,
6. "supportability" is an internal posture, not a client-facing guarantee.

Never imply:

1. suitability approval,
2. mandate approval,
3. compliance sign-off,
4. performance methodology certification,
5. risk methodology certification,
6. rebalance authority,
7. order execution,
8. report rendering or archive authority,
9. externally publishable client material,
10. data-mesh certification,
11. supported-feature promotion.

## Known Constraints And Open Gaps

Current gaps remain explicit:

1. no promoted supported features,
2. no full live source certification,
3. no certified data product,
4. no full Gateway/Workbench product proof,
5. no downstream execution/materialization proof,
6. no certified external broker publication,
7. no platform mesh certification,
8. no external-publication authority,
9. bounded service/workflow SLIs, burn alerts, and dashboard exist, but no
   production load/soak, PostgreSQL saturation, resource, cost, or back-pressure
   certification,
10. no AI provider-runtime certification,
11. no full production identity-provider integration, signed caller assertion,
    or Workbench entitlement-denied proof for caller-context authorization,
12. no production multi-process PostgreSQL concurrency certification beyond
    adapter-level stale-write/idempotency proof and local real-PostgreSQL
    two-connection review/feedback identity, downstream-submission claim
    collision, and erasure-versus-delivery serialization proof,
13. no full container-filesystem SBOM; release evidence includes
    runtime-dependency SBOM, Trivy image scan, registry digest capture, keyless
    image signature, and provenance/SBOM attestations,
14. no bank-approved jurisdiction policy, live bank lifecycle-authority
    producer/key-discovery proof, Report/Archive/AI retention conformance, or
    production authorized purge certification. Production-like consumers now
    verify and durably fence signed decisions; a bounded scheduled expiry
    review and synthetic PostgreSQL proof also exist. Neither control grants
    privacy or legal authority.

These gaps are acceptable only while current-state surfaces keep them visible.

## Branch, PR, And Merge Posture

Keep commits small, meaningful, and truthful.

Do not squash if repo policy or user direction requires preserving commit
history.

Do not open a PR before the active user constraint allows it.

Before PR or merge, rerun stranded-truth reconciliation for durable governance
paths, run the relevant repo-native gates, inspect GitHub checks, fix forward,
and keep branch hygiene clean.

After merge to `main`, publish wiki changes when source wiki changed, then
delete merged local and remote branches.

## Context Maintenance Rule

Update this document when:

1. repository ownership changes,
2. product boundary changes,
3. source-authority assumptions change,
4. dominant implementation patterns change,
5. runtime configuration families change,
6. repo-native commands or CI gates change,
7. API, persistence, security, observability, or integration posture changes,
8. supported features become implementation-backed,
9. repeated GitHub issue lessons should become durable guidance.

Keep this file curated. Avoid appending every slice detail. Link to RFCs,
runbooks, quality scorecards, and contracts for detailed history.

## AI Product Research Rule

Before external Slice 09 certification or later AI-assisted product design, read
`docs/LOTUS_IDEA_BLUEPRINT.md` and
`docs/research/advisor-intelligence-product-differentiation.md`. Refresh its
dated primary-source research, state a falsifiable differentiation hypothesis,
and define deterministic anchors, source authority, evaluation, failure,
fallback, human review, and operability evidence before implementation.

Treat the charter's candidate capabilities as research hypotheses. They do not
change current implementation truth, runtime ownership, or supported-feature
status. AI workflow execution remains owned by `lotus-ai`; `lotus-idea`
retains deterministic opportunity, evidence, lifecycle, review, feedback, and
conversion-intent truth.

## Service SLO And Capacity Rule

Service/workflow SLOs are distinct from mesh data-product SLOs. Measure HTTP
traffic only by method, route template, and status class; workflows only by
governed workflow/outcome; dependencies only by code-owned dependency identity;
and PostgreSQL only by bounded operation/outcome. Never use tenant, client,
portfolio, candidate, event, request, idempotency, correlation, or trace
identity as a metric label.

Treat one dependency call including bounded retries as one logical SLI event.
Keep dependency failure separate from Lotus Idea saturation. Replays are valid
idempotent workflow outcomes; conflicts and configuration blocks must not be
silently converted into service failures. Do not claim pool saturation when the
runtime exposes only an injected/direct PostgreSQL connection.

Dependency-failure capacity evidence must name a closed source-failure class.
For source-ingestion fault proof, accept only exclusive `source_unavailable`
aggregate evidence or the governed `source_dependency_unavailable` Problem
Details code. Reject entitlement denial, mixed failures, generic blocked
responses, and configuration or capacity blockers. Recovery requires an
explicit completed/replayed status and zero counts for every governed source
failure class. A boolean "expected failure" assertion is not evidence.

Observed dependency recovery and qualified dependency recovery are separate
states. Only an artifact from the manual main-only
`service-dependency-recovery-evidence.yml` workflow may remove the dependency
attestation blocker, and only after `gh attestation verify` pins the dedicated
signer, trusted repository, `refs/heads/main`, and exact commit. Require a
classified fault sample, a clean recovery sample, zero errors/conflicts, and a
protected production-like environment. Never accept a local artifact,
caller-selected profile, or serialized verification claim as qualification.

Capacity evidence must include the contract-gated scenario vocabulary from
`service_capacity_baseline.SCENARIOS`, including `downstream_submission`.
Downstream capacity may target only the allowlisted conversion-intent or report
evidence-pack submission routes for a pre-seeded synthetic resource. Keep the
path and idempotency keys transient and out of artifacts. This measures Idea's
intent-handoff behavior only; it does not make Idea authoritative for
suitability, execution, report rendering/archive, or downstream outcomes. Do
not claim downstream load coverage until canonical automation seeds and proves
the synthetic resource.

Use `make downstream-capacity-seed` to create the governed synthetic handoff
resource. The CLI must remain layered through
`app.application.downstream_capacity_seed`, the narrow seed port, and
`HttpDownstreamCapacitySeed`; it must call existing public APIs instead of
writing repository tables directly. Preserve the `capacity-synthetic-*` scope,
deterministic replay identity, exact confirmation, bounded/source-safe response
handling, atomic manifest, and seed-only non-certifying posture. Workload
consumption must validate schema, commit, branch, synthetic claim, and route.
Platform/Workbench canonical automation integration is separate evidence and
must not be inferred from the Idea-local command.

Steady-state load/soak evidence must use
`app.application.service_capacity_workload.execute_paced_capacity_soak` with
exactly API, source ingestion, outbox delivery, downstream submission, and
PostgreSQL scenarios. Require equal sample volume and concurrency, at least
1,000 samples per scenario, and at least 3,600 seconds between each scenario's
first and last monotonic sample offsets. Process lifetime is not observation
span; never qualify a burst followed by idle waiting. Keep dependency fault and
recovery in its dedicated attested workflow so expected source failure does not
pollute steady-state error budgets.

Only the manual main-only `service-load-soak-evidence.yml` producer may clear
the load/soak attestation blocker. It must run in the protected capacity
environment, seed only the governed synthetic downstream resource, pass
`service-load-soak-proof-gate` before attestation, and sign the exact source-safe
artifact. Consumer verification must pin repository, signer workflow, main
ref, and exact commit. Keep the producer as orchestration over existing ports
and adapters; no separate runtime service is justified by evidence collection.

Capacity probes must cross a narrow port and return bounded aggregates only.
Keep request and response bodies, URLs, DSNs, credentials, caller assertions,
and business identifiers transient inside infrastructure adapters. Require an
explicit mutation switch for operator workflows and an additional confirmation
for production. Treat observed PostgreSQL connection utilization as posture,
not proof that saturation thresholds or load shedding were exercised. Never
accept caller-asserted saturation, resource, or cost booleans. Threshold behavior
requires dedicated-target identity, bounded connections, explicit
acknowledgement, guaranteed release, and recovery to normal. Certification
additionally requires GitHub artifact-attestation verification pinned to the
governed signer workflow, `refs/heads/main`, and exact source commit. A local
or unattested proof cannot clear the production-like blocker.

Resource evidence must cross the narrow process-resource probe port and use
only bounded CPU, memory, and paired file-descriptor aggregates. Keep metrics
URLs and raw scrapes transient. Treat process telemetry as resource
observation, not cost attribution, billing reconciliation, horizontal-scale
certification, or evidence for a runtime split. Those claims require
separately governed, attested production-like and billing artifacts.
Production-like resource proof must be collected concurrently with the paced
load/soak run: require at least 61 samples spanning 3,600 seconds, fail if
either workload or resource collection fails, validate each artifact before
separate attestation, and pin repository, signer workflow, main ref, and exact
commit during consumption. A verified resource receipt may clear only
`production_like_resource_attestation_missing`.

Aggregate capacity evidence may reference a validated resource baseline only
when commit and branch provenance match. Platform issue `lotus-platform#495`
owns billing adapters, allocation, decimal reconciliation, and protected
attestation. Idea consumes only the source-safe platform artifact through a
narrow verifier that pins repository, signer, main ref, commit, and digest and
binds its resource digest/run id to Idea's already attested resource proof.
Keep `cost_attribution_evidence_missing` until matching protected evidence is
executed; schema-valid or branch-local JSON cannot clear it. Lotus Idea must
not implement official billing adapters, allocation, or cost reconciliation.

Durable PostgreSQL repositories expose capacity through a narrow repository
port. Nonessential source-ingestion and outbox operator runs must evaluate that
posture before constructing external clients or publishers: `warning` remains
allowed, while `shed` and `unavailable` fail closed. Do not apply this guard to
health, readiness, lifecycle authority, recovery, reconciliation, or
data-lifecycle controls. Keep threshold stress/recovery certification separate
from implementation-backed metrics and policy behavior.

The contract, dashboard, and alert artifacts remain `not_certified` until
representative load/soak, dependency-failure, PostgreSQL saturation,
production-like resource, and platform-owned cost evidence exists. No runtime
service split follows from adding observability; workload or failure-isolation
evidence must justify it.

## Source Runtime Evidence Boundary

Runtime source proof may clear a source blocker only when a closed evidence
contract binds the exact authoritative source receipt to the actual application
use-case result. When that use case creates or mutates an Idea aggregate, the
contract must also bind accepted or replayed durable Idea persistence. Never
fabricate a persistence receipt for an authoritative read-only operation. Shared
`application/source_runtime_evidence/` code owns only source-neutral receipt,
digest, and closed-contract mechanics. Capability packages own their source
authority, product identity, domain outcome, blockers, and non-proof claims.

For Performance underperformance, use
`application/performance_underperformance_runtime_evidence/` and its matching
automation package. Require current
`lotus-performance:ReturnsSeriesBundle:v1` evidence, benchmark context, one
deterministic review candidate, and PostgreSQL reload/replay proof. Fail closed
for source substitution, stale or temporally mismatched evidence, missing
benchmark context, non-candidate outcomes, conflicts, in-memory storage,
unknown claims, or receipt tampering. Lotus Idea creates review candidates; it
does not own official returns, benchmark assignment, attribution, or
performance methodology. This design modularity remains inside the existing
Idea deployable and database until runtime evidence justifies a split.

For Core benchmark-assignment readiness, use
`application/core_benchmark_assignment_runtime_evidence/` and its matching
automation package. Route automation through the named application use case and
Core source port. Bind pseudonymous tenant/portfolio scope, exact as-of date,
reporting currency, evaluation time, and the complete current
`lotus-core:BenchmarkAssignment:v1` receipt through canonical digests. Reject
unknown fields, source substitution, scope/digest mismatch, stale or future
evidence, inactive or ineffective assignments, and missing identity/version.
The operation is read-only: it does not persist an Idea, assign a benchmark, or
claim Performance methodology, deployment, production, publication, or support.
Keep this as design modularity within the existing deployable; no independently
scalable runtime boundary is justified.

For Core-backed missing-benchmark review, use
`application/core_missing_benchmark_runtime_evidence/` and its matching
automation and test packages. The named application use case must perform one
Core fetch and preserve the exact evidence or stable source error. Closed v2
receipts bind pseudonymous tenant/book/portfolio/client/evaluation and
correlation/trace scope, source authority, source time and freshness,
assignment identity/effectiveness/status/version posture, deterministic
candidate or ready-assignment no-opportunity output, and cross-receipt digests.
Reject unknown fields, stale/future evidence, scope or assignment drift,
diagnostic conflict, claim inflation, and recomputed-digest semantic tampering.
The stable `LOTUS_IDEA_MISSING_BENCHMARK_LIVE_PROOF` environment name and
`make missing-benchmark-live-proof-contract-gate` accept v2 only; repository
hygiene prohibits the retired flat v1 paths. This clears only the named Core
missing-benchmark source blocker. Performance readiness, mesh,
Gateway/Workbench, publication, deployment, production, and promotion remain
blocked. No API, persistence, database, migration, or runtime-service split is
introduced.

For Performance benchmark-readiness evidence, use
`application/performance_benchmark_readiness.py`,
`application/performance_benchmark_readiness_runtime_evidence/`, and their
matching capability-owned automation and tests. The named application use case
must perform exactly one `ReturnsSeriesBundle:v1` fetch and preserve the exact
Performance evidence or a stable source error. Closed v2 request, source, and
evaluation receipts bind pseudonymous tenant/book/portfolio/client/evaluation
and correlation/trace scope to the exact source product/version/route,
as-of/generated time, calculation and input hashes, response portfolio,
benchmark context, coverage counts and ratio, freshness, data quality, and
deterministic review-required or no-opportunity posture. Reject unknown fields,
raw identifiers, stale/future evidence, scope/time/hash/count drift, malformed
or contradictory benchmark context, diagnostic drift, digest tampering, and
recomputed-digest semantic tampering. The stable
`LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF` environment name,
output filename, readiness CLI argument, and
`make missing-benchmark-performance-readiness-proof-contract-gate` accept v2
only; retired flat v1 paths are prohibited. This clears only the named
Performance readiness blocker. It does not assign benchmarks, calculate
official returns, certify methodology, persist an Idea, certify data mesh,
prove Gateway/Workbench behavior, approve publication, certify deployment or
production, or promote support.

For Core portfolio-state readiness, use
`application/core_portfolio_state_runtime_evidence/` and its matching
automation package. Route generation through the named read-only application
use case and Core source port. Bind pseudonymous request scope to the complete
current `lotus-core:PortfolioStateSnapshot:v1` receipt, including response
scope, request fingerprint, snapshot identity, source hashes, restatement,
reconciliation, evidence time, policy, correlation, and applied/dropped
sections. Reject unknown fields, scope/time/hash drift, incomplete
reconciliation, dropped sections, and tampering. Never fabricate Idea
persistence or missing Core trust metadata. Treat request `evaluatedAtUtc` as
the request boundary and top-level proof `generatedAtUtc` as the post-fetch
observation boundary: a synchronous Core receipt may be generated between them,
but evidence later than artifact finalization fails closed. Core issue `#790`
owns producer acceptance and downstream proof. This remains design modularity
inside the existing deployable with no new database or runtime service.

For Core bond-maturity readiness, use
`application/bond_maturity_runtime_evidence/` and its matching automation and
test packages. Route generation through the named read-only application use
case and `CoreBondMaturitySourcePort`. Bind pseudonymous request scope to the
exact current `lotus-core:PortfolioMaturitySummary:v1` receipt and upstream
`HoldingsAsOf:v1` content identity. Require exact horizon, non-projected mode,
contractual instrument maturity-date basis, supported/complete/current posture,
zero missing maturity dates, zero unsupported lifecycle features, complete
reconciliation, snapshot/policy/correlation identity, consistent hashes, and
valid evidence time. Treat a supported empty window as completed with no
opportunity; require an in-window next date for a positive count. Reject caller
summary booleans, source substitution, unknown fields, partial/stale evidence,
scope or date/count inconsistency, and re-digested tampering. Never infer call,
put, amortization, structured-note, lockup, or expiry schedules, and never claim
product recommendation or reinvestment advice. Bound synchronous source receipt
time by post-fetch artifact `generatedAtUtc`, not pre-I/O request evaluation;
evidence later than artifact finalization remains invalid. Core issue `#792`
owns producer acceptance and downstream proof. This is design modularity inside the existing
deployable, with no new database or runtime service.

## Cross-Links

Central context:

1. `../lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `../lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `../lotus-platform/context/CONTEXT-REFERENCE-MAP.md`
4. `../lotus-platform/context/PROCEDURAL-MEMORY-INDEX.md`
5. `../lotus-platform/context/LOTUS-SKILL-ROUTING-MAP.md`
6. `../lotus-platform/context/playbooks/ENTERPRISE-BACKEND-REFACTORING-INSTRUCTIONS.md`
7. `../lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`

Repository-local anchors:

1. `README.md`
2. `docs/LOTUS_IDEA_BLUEPRINT.md`
3. `docs/rfcs/README.md`
4. `docs/operations/api-certification.md`
5. `docs/operations/implementation-proof-readiness.md`
6. `docs/operations/downstream-realization-readiness.md`
7. `docs/runbooks/service-operations.md`
8. `docs/architecture/CODEBASE-REVIEW-PLAYBOOK.md`
9. `docs/architecture/CODEBASE-REVIEW-LEDGER.md`
10. `quality/quality_scorecard.md`
11. `supported-features/supported-features.json`
12. `wiki/Home.md`
13. `docs/operations/service-slo-capacity.md`
14. `docs/research/advisor-intelligence-product-differentiation.md`

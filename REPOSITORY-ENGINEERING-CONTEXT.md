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

The repository now contains certified internal API foundations, deterministic
signal policies, caller-supplied evaluation APIs, persistence and migration
support, PostgreSQL repository projections, source-ingestion foundations,
outbox delivery foundations, downstream submission foundations, runtime
readiness diagnostics, implementation-proof artifact generation, GitHub
Security governance, and repo-native CI guardrails.

No externally supported product feature is promoted yet.

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
3. source-adapter and live-proof foundations for selected Core, Risk,
   Performance, Advise, and Manage evidence families,
4. durable repository support with PostgreSQL migrations and source-safe
   migration rollback/reapply proof,
5. evidence replay, idempotency, safe audit, operation events, and bounded
   problem-details behavior,
6. advisor queue, candidate detail, downstream realization readiness, outbox
   readiness, and runtime trust telemetry projections that avoid whole-store
   snapshot hydration on PostgreSQL,
7. downstream conversion/report submission foundations that record local
   submission posture and never grant downstream source authority,
8. source-safe outbox event publication foundations with retry/dead-letter
   state, idempotent operator run-once identity, and bounded broker proof
   artifacts,
9. AI explanation foundations with deterministic evidence, API-idempotent
   lineage storage, model-risk operations evidence, and no provider-runtime
   certification,
10. implementation-proof readiness diagnostics that aggregate blockers instead
    of promoting support.

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
Caller-supplied signal APIs must also validate source refs against the route's
governed source contract before candidate creation: wrong `sourceSystem` or
wrong `productId` is `400 invalid_request`, and rejection telemetry must use
the expected source authority instead of the caller-supplied mismatched
authority.
Bounded source-fetching signal APIs may exist only when they call an explicit
source-port/adapter, enforce caller entitlement scope before runtime dependency
construction, return product-safe dependency failures, and preserve source
authority. High-cash, low-income, bond-maturity, missing-benchmark,
concentration-risk, high-volatility, drawdown-review, underperformance, and
allocation-drift `evaluate-from-source` APIs are internal foundations inside
the existing runtime; they do not certify live source support, persist
candidates, create a separate runtime service, prove Gateway/Workbench
behavior, certify a data product, or promote a supported feature. Low-income
source-backed evaluation
consumes only Core-owned cash movement and cashflow projection evidence and
must not infer income needs, funding advice, treasury instructions, planning
suitability, or client-ready communication. Bond-maturity source-backed
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
High-volatility source-backed evaluation consumes only Lotus Risk-owned
`RiskMetricsReport:v1` volatility evidence and must not calculate volatility,
VaR, tracking error, approve risk methodology, recommend trades, create
rebalance actions, or promote risk/product support.
Drawdown-review source-backed evaluation consumes only Lotus Risk-owned
`DrawdownAnalyticsReport:v1` evidence and must not calculate drawdown, approve
risk methodology, recommend trades, create rebalance actions, or promote
risk/product support.
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
Missing-risk-profile source-backed evaluation consumes only Lotus Advise-owned
`AdvisoryPolicyEvaluationRecord:v1` risk-profile diagnostic posture and must
not approve risk profiling, determine suitability, approve policy/proposals,
publish client communication, certify a typed risk-profile data product, or
promote Advise/product support.

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
   operator helpers.

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
10. `app.api.outbox_delivery_readiness_models` for outbox delivery readiness
   and run-once response DTOs behind the existing
   `app.api.outbox_delivery_readiness` route surface,
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
14. `app.api.review_queue_models` for advisor review queue and review queue
   readiness response DTOs behind the existing `app.api.review_queues` route
   surface,
15. `app.api.signal_api_support` for caller context, scope checks, source-ref
   rendering, and signal outcome mapping,
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
4. downstream realization readiness-count projection,
5. outbox delivery readiness projection,
6. runtime trust telemetry aggregate projection,
7. advisor queue readiness aggregate projection.

When adding another read path or aggregate diagnostic, first ask whether the
query needs a bounded projection contract. Avoid `snapshot()` for narrow
PostgreSQL reads unless the provider is process-local, the request needs
in-memory-only policy state such as snoozes, or the flow is still explicitly
legacy.

For mutation workflows, preserve idempotency, audit, operation events, source
authority, and supportability posture. Do not bypass repository mutation
methods just to optimize a write path.
Review-action and feedback API route orchestration is intentionally centralized
in `app.api.review_workflow_operations` as design modularity inside the
existing `lotus-idea` process. Do not split this into a separate runtime
service, worker, or queue boundary without measured workload, failure-isolation,
ownership, security, or operability evidence.
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
5. `LOTUS_IDEA_REPORT_REALIZATION_BASE_URL`,
6. `LOTUS_IDEA_REPORT_REALIZATION_SUBMIT_PATH`,
7. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_TIMEOUT_SECONDS`,
8. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_MAX_CONNECTIONS`,
9. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_MAX_KEEPALIVE_CONNECTIONS`,
10. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_POOL_TIMEOUT_SECONDS`,
11. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_MAX_ATTEMPTS`,
12. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_INITIAL_BACKOFF_SECONDS`,
13. `LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_MAX_BACKOFF_SECONDS`.

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

Readiness endpoints are diagnostic foundations. They report aggregate blockers
and source-of-truth refs. They are not support, certification, or live journey
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
source-safe readiness evidence. They are not certified data products and do not
promote supported features.

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

These are foundation controls, not production identity-provider proof.
Route-level capability checks consume caller-context headers inside the service
boundary. In `demo`, `staging`, and `production` profiles, privileged
`X-Caller-*` role, capability, and entitlement headers are rejected unless the
request also carries `X-Lotus-Trusted-Caller-Context` matching
`LOTUS_IDEA_TRUSTED_CALLER_CONTEXT_TOKEN`. This is a bounded trusted-ingress
provenance marker for service-to-service propagation; it is not an
identity-provider integration, signed assertion, Workbench entitlement proof,
client-publication proof, or supported-feature promotion.

Caller-supplied opportunity signal routes and advisor-facing candidate detail /
review queue reads require both the product role and the explicit `idea.*`
capability published for the route. `app.api.signal_api_support` requires
advisor role plus `idea.signal.evaluate` before evaluating source-owned
evidence, and `src/app/api/candidate_detail.py` and
`src/app/api/review_queues.py` require advisor/operator role plus the read
capability before returning source-safe candidate or queue data. The signal API
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

## Observability And Operability

Operation events are the primary supportability surface. They must stay
bounded, source-safe, and low-cardinality.

Use route templates rather than raw paths in diagnostics.

Use correlation and trace headers across outbound calls when available.

Metrics and operation-event vocabulary are governed by
`contracts/observability/lotus-idea-operation-metrics.v1.json`.

AI model-risk operations proof is limited to implemented AI explanation
telemetry. It does not certify `lotus-ai` runtime execution, provider calls,
Workbench behavior, data-mesh certification, or supported-feature promotion.

Non-AI operator workflow operations proof is limited to source-safe dashboard
and alert visibility over implemented source-ingestion, outbox delivery,
downstream realization, runtime trust telemetry, and implementation-proof
readiness operation events. It does not certify live source ingestion,
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
make slice2-structure-gate
make supported-features-gate
```

`make slice2-structure-gate` is the RFC-0002 Slice 2 closure guard. It keeps
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
make downstream-route-contract-proof-gate
make outbox-broker-proof-contract-gate
make runtime-trust-telemetry-proof-contract-gate
make source-ingestion-live-proof-contract-gate
make source-ingestion-scheduled-worker-check
make quality-scorecard-gate
make repository-hygiene-gate
make runtime-dependency-closure-gate
make github-security-posture-check
```

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
5. runtime trust telemetry proof must not clear aggregate certification blockers
   while declared product coverage remains incomplete; product-level blockers
   and aggregate readiness must stay semantically aligned,
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
12. persisted AI explanation lineage writes need both API-level idempotency and
    domain request-id replay protection; same-key replay/conflict and
    distinct-key request-id conflict must remain separately tested,
13. AI explanation evaluation must use the single governed workflow-pack
    contract in `app.domain.ai_governance`: public request identity
    `lotus-ai:idea-explanation:v1` + version `v1` + evaluator
    `lotus-ai:governed-verifier:v1` maps deliberately to the proof identity
    `idea_explanation.pack@v1`; arbitrary caller-supplied pack identities must
    fail closed with product-safe `invalid_ai_workflow_pack` before candidate
    lookup or lineage persistence,
14. privileged operator run-once mutations need explicit operator run identity
   and idempotency before event claims or external side effects,
15. release evidence artifacts must name their scope, target artifact or
    dependency source, generator, path, and non-proof boundary before being cited
    as release proof,
16. runtime dependency SBOM evidence must come from the resolved runtime
    dependency closure in `requirements/runtime-resolved.lock.txt`, not from
    direct-only runtime requirements or an ambiguous CI environment; the
    supported-name `requirements/requirements.txt` exists only as a gated
    mirror for GitHub Dependency Graph support,
17. Python dependency updates must move root pins and runtime lock evidence
    through the governed `make dependency-refresh` path. Dependabot must not
    open a separate `/requirements` lock-only stream; lock refreshes should
    regenerate both `requirements/runtime-resolved.lock.txt` and
    `requirements/requirements.txt` from the active runtime closure before
    merge validation. Routine Dependabot version-update PRs are paused with
    `open-pull-requests-limit: 0` while RFC implementation is active; security
    alerts and security-update posture remain governed through the GitHub
    Security tab and `make github-security-posture-check`,
18. GitHub Actions shell commands that interpolate runtime environment values
    such as `${GITHUB_REPOSITORY}` or `${GITHUB_RUN_ID}` must quote the whole
    composed argument so workflow lint remains clean and CI signal evidence
    jobs do not accumulate avoidable ShellCheck annotations.
19. Docker build and scan evidence must be paired with bounded packaged-runtime
    startup and health-surface smoke proof before claiming release image
    confidence,
20. generated proof and quality evidence must be reproducible from current
    gate rules or be documented as on-demand evidence rather than current proof,
21. ignored report-only artifacts must not be cited as durable current-state
    proof unless a deterministic committed-artifact drift gate exists,
22. documentation should record the durable rule, not only the one-off fix,
23. supportability, readiness, health-state, and data-quality vocabulary must
    not be treated as freshness-current evidence unless a source-owned freshness
    field explicitly uses governed freshness vocabulary.
24. dashboard and alert certification should be pattern-backed with a
    machine-readable contract, concrete Grafana/Prometheus/runbook artifacts,
    proof gates, drift tests, and explicit non-proof boundaries; do not rely on
    a metric catalog alone for operator visibility claims.
25. mutating workflow idempotency must be true in both runtime behavior and
    OpenAPI contract truth. Routes that require `Idempotency-Key` should use the
    shared `app.api.idempotency` route list and validation helpers, and
    `make api-idempotency-boundary-gate` must fail optional or defaulted
    `Idempotency-Key` OpenAPI headers for certified idempotent mutations.
26. Docker runtime images should install the resolved runtime dependency lock
    before copying application source, then install the local service package
    with `--no-deps` after `COPY src`; `.dockerignore` must keep generated
    coverage, SBOM, quality-report, and proof-output artifacts out of Docker
    build context; `make ci-contract-gate` must catch source-before-dependency-
    install ordering, dependency reinstall drift, and Docker-context
    generated-artifact parity drift.
27. release images must be commit-tagged, CI-published only, signed, attested,
    and promoted by digest. The Dockerfile must carry OCI labels for service
    version, commit SHA, branch, build timestamp, repo URL, CI run ID, and image
    digest metadata; `/version` must expose the same runtime build metadata as
    `/metadata`; `release-evidence.json` must capture the registry digest,
    digest deployment reference, keyless signature subject, provenance
    attestation, SBOM attestation, scan evidence, and same-digest promotion
    policy; Docker ARG/ENV names must reject secret-like build inputs.
28. duplicate-implementation controls now split report-only evidence from
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
28. Route-owned runtimes must consume their own cleanup hooks. Source-ingestion
    run-once builds Core HTTP clients through `SourceIngestionRuntime`; the API
    path must close the runtime after accepted or source-unavailable execution
    and must not rely on worker-only cleanup semantics. The same pattern applies
    to route-owned publisher adapters: outbox-delivery run-once must close the
    broker publisher it constructs after accepted, replayed, failed, or
    conflicting execution paths. Cleanup failures are supportability signals,
    not product outcomes: route-owned `close()` failures must be bounded to
    source-safe suppressed operation events and must not replace already
    computed completed, replayed, conflict, or blocked run-once responses.
29. Run-once source-ingestion manifests are intentionally small bounded
    operator actions. `maxItems` and raw `workItems` must stay at or below the
    code-owned 100-item ceiling; larger ingestion requires a separately
    designed chunked or scheduled workflow with capacity evidence.
30. Operation metric source-authority vocabulary must be code-owned. Runtime
    `OperationEvent`, operation metric contracts, operator workflow contracts,
    dashboards, and alert proof gates must consume the same governed
    `OPERATION_EVENT_SOURCE_AUTHORITIES` set instead of duplicating partial
    allowlists.
31. Keep context holistic. Detailed GitHub issue closure evidence belongs in
    `docs/architecture/GITHUB-ISSUE-CLOSURE-MATRIX.md` and is enforced by
    `make github-issue-closure-matrix-gate`; this context file should retain
    durable patterns, boundaries, commands, and routing rules instead of
    becoming a repeated per-issue evidence dump.

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
5. Operator observability certification: GitHub issue `#282` is addressed by
   the non-AI operator workflow operations contract and proof gates, which
   certify source-safe dashboard/alert artifacts over implemented operation
   telemetry while preserving live-source, external-broker, downstream
   execution, Gateway/Workbench, data-mesh, and supported-feature blockers.
6. Aggregate operator workflow proof consumption: GitHub issue `#292` is
   addressed by a distinct `operator-workflows-operations` implementation-proof
   readiness capability, CLI/env/API proof-artifact consumption, and regression
   tests that clear only operator dashboard/alert blockers while retaining
   live-source, external-broker, downstream execution, Gateway/Workbench,
   data-mesh, and supported-feature blockers unless their owning proof artifacts
   are also present.
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
12. Review/feedback trusted entitlement scope: GitHub issue `#318` is addressed
    by binding review-action and feedback mutation actor scope to trusted
    `X-Caller-Tenant-Ids`, `X-Caller-Book-Ids`,
    `X-Caller-Portfolio-Ids`, and `X-Caller-Client-Ids` headers, requiring
    request `authorizedScope` to stay within those entitlements, and applying
    domain review/feedback checks against the persisted candidate access scope
    instead of caller-supplied request `accessScope`. Missing or mismatched
    entitlement headers fail closed with product-safe permission denial and no
    raw portfolio/client disclosure.
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
    `scripts.operations_contract_validators`; the current measured baseline
    ignores pass/ellipsis-only protocol stubs, scans 1,607 executable function
    bodies, and reports 0 exact duplicate clusters. GitHub issue `#309`
    promotes the same deterministic scanner to a blocking
    `make duplicate-implementation-gate` with `--fail-on-duplicates`, wired into
    `make lint` while preserving `make duplicate-implementation-inventory` as
    the no-artifact report-only evidence command.
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
8. no client-ready publication,
9. no production capacity or back-pressure certification,
10. no AI provider-runtime certification,
11. no full production identity-provider integration, signed caller assertion,
    or Workbench entitlement-denied proof for caller-context authorization,
12. no production multi-process PostgreSQL concurrency certification beyond
    adapter-level stale-write and idempotency-collision proof,
13. no full container-filesystem SBOM; release evidence includes
    runtime-dependency SBOM, Trivy image scan, registry digest capture, keyless
    image signature, and provenance/SBOM attestations,
14. no deterministic freshness check for committed architecture boundary
    report evidence.

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
2. `docs/rfcs/README.md`
3. `docs/operations/api-certification.md`
4. `docs/operations/implementation-proof-readiness.md`
5. `docs/operations/downstream-realization-readiness.md`
6. `docs/runbooks/service-operations.md`
7. `docs/architecture/CODEBASE-REVIEW-PLAYBOOK.md`
8. `docs/architecture/CODEBASE-REVIEW-LEDGER.md`
9. `quality/quality_scorecard.md`
10. `supported-features/supported-features.json`
11. `wiki/Home.md`

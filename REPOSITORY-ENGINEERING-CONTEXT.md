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

## Current Implementation Map

The codebase is organized around stable internal bounded modules before any
runtime modularity:

1. `src/app/domain/`: domain vocabulary, policies, lifecycle, evidence,
   scoring, feedback, conversion, report evidence, outbox, and idempotency
   invariants.
2. `src/app/application/`: use-case orchestration, proof-readiness builders,
   source ingestion, downstream submission, outbox delivery, AI explanation,
   and readiness diagnostics.
3. `src/app/api/`: FastAPI routes, DTOs, shared route metadata, caller-context
   binding, idempotency header validation, product-safe problem details, and
   signal API support.
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
6. `app.api.signal_api_support` for caller context, scope checks, source-ref
   rendering, and signal outcome mapping,
7. `app.api.temporal_validation` for API timestamp awareness and UTC query
   validation.

Use public domain and infrastructure APIs:

1. import cross-module domain objects through `app.domain`,
2. use public proof-readiness helpers from
   `app.application.implementation_proof_capability_updates`,
3. use `app.infrastructure.postgres_codecs` for PostgreSQL row, JSON, datetime,
   and domain serialization behavior,
4. do not couple tests or application code to protected private helpers across
   modules.

For durable reads, prefer bounded projections over whole repository snapshots:

1. advisor queue page projection,
2. candidate-detail projection,
3. downstream conversion/report lookup projection,
4. downstream realization readiness-count projection,
5. outbox delivery readiness projection,
6. runtime trust telemetry aggregate projection.

When adding another read path, first ask whether the query needs a bounded
projection contract. Avoid `snapshot()` for narrow PostgreSQL reads unless the
provider is process-local or the flow is still explicitly legacy.

For mutation workflows, preserve idempotency, audit, operation events, source
authority, and supportability posture. Do not bypass repository mutation
methods just to optimize a write path.

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
make supported-features-gate
```

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
   narrow read paths,
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
   caller-context provenance guard before those headers can authorize a route,
10. PostgreSQL mutation paths need optimistic same-candidate guards and
   database idempotency-collision retry; full-snapshot mutation helpers must
   not silently overwrite stale state or leak raw primary-key collisions,
11. persisted AI explanation lineage writes need both API-level idempotency and
    domain request-id replay protection; same-key replay/conflict and
    distinct-key request-id conflict must remain separately tested,
12. privileged operator run-once mutations need explicit operator run identity
   and idempotency before event claims or external side effects,
13. release evidence artifacts must name their scope, target artifact or
    dependency source, generator, path, and non-proof boundary before being cited
    as release proof,
14. runtime dependency SBOM evidence must come from the resolved runtime
    dependency closure in `requirements/runtime-resolved.lock.txt`, not from
    direct-only runtime requirements or an ambiguous CI environment; the
    supported-name `requirements/requirements.txt` exists only as a gated
    mirror for GitHub Dependency Graph support,
15. Python dependency updates must move root pins and runtime lock evidence
    through the governed `make dependency-refresh` path. Dependabot must not
    open a separate `/requirements` lock-only stream; lock refreshes should
    regenerate both `requirements/runtime-resolved.lock.txt` and
    `requirements/requirements.txt` from the active runtime closure before
    merge validation,
16. Docker build and scan evidence must be paired with bounded packaged-runtime
    startup and health-surface smoke proof before claiming release image
    confidence,
17. generated proof and quality evidence must be reproducible from current
    gate rules or be documented as on-demand evidence rather than current proof,
18. ignored report-only artifacts must not be cited as durable current-state
    proof unless a deterministic committed-artifact drift gate exists,
19. documentation should record the durable rule, not only the one-off fix,
20. supportability, readiness, health-state, and data-quality vocabulary must
    not be treated as freshness-current evidence unless a source-owned freshness
    field explicitly uses governed freshness vocabulary.
21. dashboard and alert certification should be pattern-backed with a
    machine-readable contract, concrete Grafana/Prometheus/runbook artifacts,
    proof gates, drift tests, and explicit non-proof boundaries; do not rely on
    a metric catalog alone for operator visibility claims.
22. mutating workflow idempotency must be true in both runtime behavior and
    OpenAPI contract truth. Routes that require `Idempotency-Key` should use the
    shared `app.api.idempotency` route list and validation helpers, and
    `make api-idempotency-boundary-gate` must fail optional or defaulted
    `Idempotency-Key` OpenAPI headers for certified idempotent mutations.
23. Docker runtime images should install the resolved runtime dependency lock
    before copying application source, then install the local service package
    with `--no-deps` after `COPY src`; `make ci-contract-gate` must catch
    source-before-dependency-install ordering and dependency reinstall drift.
24. duplicate-implementation controls start as measured report-only inventory,
    not a noisy merge blocker. `make duplicate-implementation-inventory`
    scans exact first-party function-body duplicates across `src/app` and
    `scripts`, identifies known proof-helper clusters, writes no artifacts, and
    should be used to guide shared-helper consolidation before any strict
    threshold is promoted. The first follow-through consolidations moved repeated
    proof source-safety traversal into `scripts/proof_source_safety.py` and
    live-proof generator timeout/output plumbing and generated-at UTC parsing into
    `scripts/proof_generator_io.py`, and centralized proof timestamp,
    make-target evidence, and cross-repository file-evidence checks in
    `src/app/application/source_safe_cross_repo_proof.py`, plus AST call-name
    parsing in `scripts/ast_gate_helpers.py` and Core live-proof base URL
    resolution in `scripts/proof_generator_io.py`, removing known
    duplicate function-body clusters while preserving family-specific proof
    policy and generator argument behavior.

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
8. Resilience retry control: GitHub issue `#286` is addressed by fixed central
   jitter in `DownstreamJsonClient` computed backoff delays, deterministic
   jitter injection in tests, and no change to retry attempts, retryable status
   codes, valid `Retry-After` handling, POST idempotency rules, or adapter-local
   retry-loop boundaries.
9. PostgreSQL review-queue performance: GitHub issue `#287` is addressed by
   narrow expression indexes for the advisor review queue tenant/book/
   portfolio/client access-scope JSONB predicates, migration rollback coverage,
   `migration_contract_gate.py` required-index enforcement, and PostgreSQL
   queue tests that prove scoped count/page reads retain eligibility filters,
   stable ordering, and `LIMIT`/`OFFSET` bounds without changing advisory
   workflow ownership or API semantics.
10. Dependency update atomicity: GitHub issue `#289` is addressed by removing
   the separate `/requirements` Dependabot stream, grouping Python root updates
   as dependency-closure root changes, adding `make dependency-refresh` to
   install from root pins and regenerate both runtime lock files, and protecting
   the workflow through security/CI contract tests. Existing install,
   runtime-closure, audit, Docker, SBOM, and release evidence gates remain
   strict.
11. Lifecycle vocabulary authority: GitHub issue `#290` is addressed by
   quarantining downstream-authority lifecycle statuses from caller-settable
   lifecycle transitions. The API request contract uses a caller-settable
   lifecycle enum that excludes `accepted` and `executed`, the domain graph no
   longer permits new transitions into those downstream-authority statuses, and
   the application command rejects them before repository mutation or outbox
   emission. Conversion outcomes and downstream submissions remain the
   source-authority paths for downstream acceptance posture.
12. Idempotency OpenAPI truth: GitHub issue `#291` is addressed by the shared
    idempotency OpenAPI contract override and boundary gate, which require
    certified mutating idempotency routes to publish `Idempotency-Key` as a
    required header with no default while preserving product-safe runtime
    validation behavior.
13. CI signal feedback-time truth: GitHub issue `#293` is addressed by keeping
    report-only CI signal evidence source-safe while distinguishing workflow
    feedback time from longest individual job duration. `criticalPathSeconds`
    now uses first-job-start to last-job-completion wall-clock time, with
    `workflowWallClockSeconds` recording the same feedback-time basis and
    `longestJobName`/`longestJobSeconds` retaining the optimization signal.
    `thresholdEnforced` remains false and no duration threshold is promoted.
14. Docker cache-aware release builds: GitHub issue `#295` is addressed by
    moving resolved runtime dependency installation ahead of `COPY src`,
    installing the local package afterward with `--no-deps`, and extending the
    release-evidence contract/tests to reject source-before-dependency-install
    ordering or dependency reinstall drift. Docker build, runtime smoke,
    container scan, and runtime SBOM evidence remain intact.
15. Duplicate implementation inventory: GitHub issue `#296` is addressed by a
    repo-native `make duplicate-implementation-inventory` command that reports
    exact duplicate function-body clusters across `src/app` and `scripts`
    without writing artifacts or enforcing thresholds. The initial baseline
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
    `app.runtime.proof_artifact_files`;
    the current measured baseline scans 1,612 functions and reports 6 exact
    clusters.
    `make ci-contract-gate` protects the target wiring while strict duplicate
    blocking remains unpromoted.

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
13. no full container-image SBOM or registry attestation,
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
7. `quality/quality_scorecard.md`
8. `supported-features/supported-features.json`
9. `wiki/Home.md`

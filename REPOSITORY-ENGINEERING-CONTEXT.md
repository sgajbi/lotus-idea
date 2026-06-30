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
9. AI explanation foundations with deterministic evidence, lineage storage,
   model-risk operations evidence, and no provider-runtime certification,
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
7. GitHub Security posture checks,
8. Dependabot/security-update governance,
9. CodeQL default setup governance,
10. secret scanning and push protection where GitHub reports them enabled.

These are foundation controls, not production identity-provider proof.
Route-level capability checks currently consume caller-context headers inside
the service boundary; production-like use still requires trusted ingress or
authenticated caller-context provenance before those headers can be treated as
authority.

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
make github-security-posture-check
```

Current repo-native aggregate command posture:

1. `make ci` is useful local aggregate evidence, but it must not be cited as
   PostgreSQL runtime, Docker build, image scan, SBOM, or release-evidence
   proof unless those families are explicitly included in the command model at
   the time of validation.
2. Until the governed full-lane command is aligned, cite and run the explicit
   heavy proof targets when the slice depends on PostgreSQL runtime behavior or
   container/release evidence.
3. GitHub workflow YAML should keep calling repo-native targets rather than
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
   inputs until bound to trusted ingress, signed assertion, service identity, or
   another authenticated provenance control,
10. PostgreSQL mutation paths need explicit same-candidate concurrency guards;
   full-snapshot mutation helpers must not silently overwrite stale state,
11. persisted AI explanation lineage writes need API-level idempotency in
   addition to domain request-id replay protection,
12. privileged operator run-once mutations need explicit operator run identity
   and idempotency before event claims or external side effects,
13. generated proof and quality evidence must be reproducible from current
   gate rules or be documented as on-demand evidence rather than current proof,
14. documentation should record the durable rule, not only the one-off fix.

Current open issue priorities that should shape the next implementation slices:

1. GitHub issue `#272`: bind SBOM/container/release evidence to runtime
   artifacts before claiming release proof.
2. GitHub issue `#270`: add container startup/health smoke evidence before
   release image confidence claims.
3. GitHub issue `#267`: bind caller-context authorization headers to trusted
   ingress before production-like use.
4. GitHub issue `#266`: guard PostgreSQL idea mutations against stale snapshot
   writes.
5. GitHub issue `#268`: require API idempotency for AI explanation lineage
   writes.
6. GitHub issue `#263`: align repo-native command coverage with PostgreSQL and
   Docker release proof gates or document a governed light/full split.
7. GitHub issue `#260`: require aggregate provenance for source-ingestion live
   proof consumption.
8. GitHub issue `#269`: keep architecture boundary report evidence
   synchronized with current gate rules.

Issues `#271`, `#265`, `#264`, `#262`, `#261`, and `#259` have branch-local
fixes and validation evidence, but they must not be claimed closed until merged
to `main`, CI is green, and QA or issue-closure evidence exists.

Close or claim issue progress only after implementation, tests, docs/context
truth, and validation evidence exist. Keep issue count under control by fixing
classes of defects rather than isolated symptoms.

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
11. no trusted-ingress proof for caller-context authorization headers,
12. no PostgreSQL same-candidate stale-write guard across all mutations,
13. no API-level idempotency contract for AI explanation lineage writes,
14. no release-artifact-bound SBOM/container proof,
15. no deterministic freshness check for committed architecture boundary
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

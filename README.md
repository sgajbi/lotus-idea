# lotus-idea

`lotus-idea` is the Lotus opportunity intelligence and idea lifecycle domain
service for private-banking workflows. It turns source-owned evidence into
reviewable opportunity candidates, evidence packs, scores, review queues,
feedback records, conversion intent, and readiness posture.

Service profile: `domain-service`

| Start with | Use it for |
| --- | --- |
| [REPOSITORY-ENGINEERING-CONTEXT.md](REPOSITORY-ENGINEERING-CONTEXT.md) | Current implementation truth, repo-local rules, and issue-derived patterns. |
| [docs/rfcs/README.md](docs/rfcs/README.md) | RFC slice index and completion posture. |
| [wiki/Home.md](wiki/Home.md) | Authored GitHub wiki source. |
| [LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md](../lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md) | Governing banking-grade engineering contract. |

## Current Posture

`lotus-idea` is in RFC-0002 foundation implementation. Internal API,
persistence, readiness, source-ingestion, outbox, AI-governance, downstream
intent, Gateway/Workbench read-path, and data-mesh proof foundations exist, but
no externally supported product feature is promoted.

The supported-feature registry remains foundation-only. Feature promotion
requires implementation-backed source certification, Gateway/Workbench proof,
contracts, OpenAPI evidence, tests, documentation, wiki source, CI evidence on
`main`, and clean branch hygiene.

| Area | Current truth | Promotion blocker |
| --- | --- | --- |
| Opportunity policies | Bounded foundations exist for high cash, concentration risk, underperformance, allocation drift, bond maturity, volatility, drawdown, suitability gaps, risk-profile gaps, mandate/restriction review, income gaps, and missing benchmark review. | Live source certification, data-mesh proof, Workbench proof, and supported-feature registration remain blocked. |
| Lifecycle and review | Candidate persistence, replay, review actions, feedback, queues, scoring, and audit-oriented state transitions are implemented as internal foundations. Lifecycle and review posture use one versioned compatibility policy with terminal-state normalization and durable legacy quarantine. | Client publication and official advisory workflow ownership remain out of scope. |
| Downstream intent | Conversion intent, source-versioned append-only outcome history, policy-valid current posture, report evidence-pack requests, outbox records, and Advise/Manage/Report route-proof consumption are bounded foundations. | Execution, report rendering, archive authority, and downstream materialization proof remain external; quarantined outcome history does not count as ready. |
| AI-adjacent support | Explanation readiness, lineage-store proof, workflow-pack registration/runtime proof consumption, and model-risk operations evidence are governed. | `lotus-idea` does not own AI infrastructure, provider calls, RAG runtime, or model operations. |
| Data mesh | Proposed product and consumer contracts, mesh policy proof, platform onboarding proof consumption, and runtime trust telemetry exist. | Data-product certification and supported-feature promotion remain blocked. |

The long-form implementation ledger is deliberately not in this README. Use
[docs/rfcs/README.md](docs/rfcs/README.md),
[docs/architecture/CODEBASE-REVIEW-LEDGER.md](docs/architecture/CODEBASE-REVIEW-LEDGER.md),
and [quality/quality_scorecard.md](quality/quality_scorecard.md) for detailed
slice evidence.

## Product Boundary

`lotus-idea` owns:

- opportunity detection policy over source-owned evidence,
- idea candidate lifecycle, scoring, ranking, review workflow, and feedback,
- evidence packs, rationale, source references, replay posture, and audit state,
- conversion intent and outcome tracking for reviewed opportunities,
- idea data-product declarations, trust telemetry, and readiness posture,
- bounded orchestration contracts for Gateway, Workbench, Advise, Manage,
  Report, Render, Archive, and AI-adjacent proof consumption.

`lotus-idea` does not own:

- portfolio accounting, holdings, transactions, client master, or product master,
- official performance, risk, suitability, compliance, mandate, or tax decisions,
- rebalance execution, order routing, trade approval, or portfolio actions,
- report rendering, report archive authority, or client communication authority,
- AI infrastructure, provider runtime, RAG platform, or model operations,
- client-ready publication or supported product claims before promotion evidence.

## Architecture At A Glance

```mermaid
flowchart LR
    Sources["Source authorities<br/>Core / Performance / Risk / Advise / Manage / Report"]
    Idea["lotus-idea<br/>policy, lifecycle, evidence, review, conversion intent"]
    Store["Repository<br/>process-local or PostgreSQL"]
    Gateway["lotus-gateway<br/>bounded read publication"]
    Workbench["lotus-workbench<br/>bounded read proof"]
    Downstream["Advise / Manage / Report / Render / Archive<br/>review-gated realization"]

    Sources -->|"source refs, freshness, evidence"| Idea
    Idea -->|"idempotent state, audit, replay"| Store
    Idea -->|"queue/detail read contracts"| Gateway
    Gateway --> Workbench
    Idea -->|"conversion/report intent, outbox posture"| Downstream
```

Runtime composition stays one service until workload, failure-isolation,
ownership, and operability evidence justify a separately scalable process
boundary. Current refactors are design modularity improvements inside the
existing deployable service.

| Package | Responsibility |
| --- | --- |
| `src/app/api/` | FastAPI routes, DTOs, caller context, idempotency, route metadata, and API boundary helpers. |
| `src/app/application/` | Use-case orchestration for signal evaluation, lifecycle, review, feedback, conversion, readiness, replay, and proof updates. |
| `src/app/domain/` | Framework-free domain models, policies, scoring, lifecycle rules, persistence records, idempotency, audit, replay, and outbox state. |
| `src/app/ports/` | Repository, source-service, downstream, and publisher protocols. |
| `src/app/infrastructure/` | Source adapters, PostgreSQL repository, migrations, codecs, HTTP clients, and outbox publisher adapter. |
| `src/app/middleware/` | Correlation, trusted hosts, CORS, request-size limits, JSON write controls, and security headers. |
| `src/app/observability/` | Structured logging, metrics, tracing, correlation, and operation events. |
| `contracts/` | Data-mesh, SLO, access, evidence-policy, downstream, trust telemetry, and readiness contracts. |
| `docs/` and `wiki/` | RFCs, operator runbooks, architecture standards, demo posture, and GitHub wiki source. |

### Request Path

Every caller-supplied opportunity signal follows the same internal path:

```text
External consumer
  -> FastAPI route/controller -> request DTO mapper (`to_command`)
  -> application use case -> framework-free domain policy and candidate model
  -> source/repository port -> infrastructure adapter
  -> PostgreSQL, source API, cache, queue, or downstream API
```

`app.api.signal_api_support.evaluate_caller_supplied_signal` owns the shared
authorization, entitlement-scope, source-contract, operation-event, and response
boundary for caller-supplied signals. Source-backed routes retain their
route-owned adapter lifecycle because runtime construction, failure mapping, and
cleanup have different operational semantics. This is design modularity inside
one deployable service; it is not evidence for a signal microservice split.

## Data Mesh Posture

`lotus-idea` is data-mesh-first, but certification is intentionally blocked
until runtime behavior and source authority are proven.

Authoritative contract files:

- [contracts/domain-data-products/lotus-idea-products.v1.json](contracts/domain-data-products/lotus-idea-products.v1.json)
- [contracts/domain-data-products/lotus-idea-consumers.v1.json](contracts/domain-data-products/lotus-idea-consumers.v1.json)
- [contracts/domain-data-products/mesh-readiness.v1.json](contracts/domain-data-products/mesh-readiness.v1.json)
- [docs/operations/mesh-readiness.md](docs/operations/mesh-readiness.md)
- [Lotus Data Mesh Standard](../lotus-platform/docs/standards/Lotus%20Data%20Mesh%20Standard.md)

Repo-owned mesh policy proof validates SLO, access, evidence, and readiness
contracts only. Platform onboarding proof validates catalog visibility only.
Neither proof certifies supported features, Workbench behavior, client
publication, or external data-product activation by itself.

## Quick Start

Install dependencies:

```powershell
make install
```

Run fast local checks:

```powershell
make lint
make typecheck
make test-unit
```

Run the service locally:

```powershell
uvicorn app.main:app --reload --port 8330
```

Run with PostgreSQL after applying migrations:

```powershell
$env:LOTUS_IDEA_DATABASE_URL = "postgresql://lotus_idea:lotus_idea@localhost:5432/lotus_idea"
make migrate
uvicorn app.main:app --reload --port 8330
```

Run the Docker profile:

```powershell
docker compose up --build
```

Compose is runtime-parity evidence for local validation. It is not production
deployment evidence, Workbench proof, data-product certification, client
publication, or supported-feature promotion. Post-merge Main Releasability is
the only registry-publish path: it builds the image under the Git commit SHA,
pushes it to GHCR, records the registry digest in `release-evidence.json`,
generates the runtime-dependency SBOM, passes the Trivy image scan, signs the
digest with keyless Cosign, and publishes provenance and SBOM attestations.

## Validation And CI Lanes

```mermaid
flowchart LR
    Feature["Feature Lane<br/>lint, typecheck, unit tests, fast gates"]
    PR["PR Merge Gate<br/>integration, coverage, Docker, Postgres proof"]
    Main["Main Releasability<br/>release truth after merge"]
    Wiki["Wiki publication<br/>after source merge"]

    Feature --> PR --> Main --> Wiki
```

Common gates:

| Command | Use it for |
| --- | --- |
| `make lint` | Formatting, linting, hygiene, documentation, quality, implementation-truth, architecture, API-boundary, observability, and contract fast gates. |
| `make typecheck` | `mypy` over the service. |
| `make test-unit` | Unit tests; override `UNIT_TESTS` for focused work. |
| `make test-integration` | Integration tests; override `INTEGRATION_TESTS` for focused work. |
| `make test-e2e` | Deterministic end-to-end tests; override `E2E_TESTS` for focused work. |
| `make documentation-contract-gate` | README, repo context, docs, wiki, demo, and evidence-surface contract truth. |
| `make implementation-truth-gate` | Blocks overclaims about support, certification, live source proof, Workbench, and client readiness. |
| `make slice2-structure-gate` | Enforces RFC-0002 Slice 2 foundation-only posture, documentation truth, and architecture-boundary agreement. |
| `make quality-scorecard-gate` | Keeps quality posture aligned with implementation truth. |
| `make supported-features-gate` | Ensures supported-feature registry entries are implementation-backed only. |
| `make endpoint-certification-gate` | Validates endpoint certification evidence and OpenAPI caller-context truth. |
| `make check` | Local PR-grade lane for routine feature work. |
| `make ci-release` | Broad release evidence including implementation proof, Postgres, Docker, smoke, scan, and SBOM evidence. |

The built image carries OCI labels for service version, Git commit, Git branch,
build timestamp, repository URL, CI run ID, and image digest metadata. The
runtime `/version` endpoint returns the same build metadata as `/metadata` for
release inventory and deployment diagnostics.

For README, wiki, RFC, context, contract, CI, or supported-feature edits, run
stranded-truth reconciliation first:

```powershell
git fetch origin --prune
git branch -r --no-merged origin/main
```

Classify unmerged durable-truth branches as `must-merge`, `cherry-pick`,
`superseded`, `delete`, or `active` before claiming closure.

## Runtime And Operations

`LOTUS_IDEA_RUNTIME_PROFILE` defaults to `local`. Only `local` and `test`
allow process-local writes and caller-header simulation. Production-like
profiles require `LOTUS_IDEA_DATABASE_URL` and fail closed when durable writes,
trusted caller provenance, or source authority are not configured.

Operator entrypoints:

- `/health`, `/health/live`, `/health/ready`, `/metrics`, and `/docs`
- `/metadata` and `/version`
- `/api/v1/source-ingestion/readiness` and `/api/v1/source-ingestion/run-once`
- `/api/v1/outbox-delivery/readiness`, run-once, dead-letter inspection, and governed re-drive
- `/api/v1/review-queues/advisor/readiness`
- `/api/v1/ai-explanations/readiness`
- `/api/v1/downstream-realization/readiness`
- `/api/v1/implementation-proof/readiness`
- `/api/v1/data-mesh/readiness`
- `/api/v1/data-mesh/trust-telemetry/runtime-preview`
- `/api/v1/data-mesh/trust-telemetry/runtime-snapshot`

Operator details live in
[docs/runbooks/service-operations.md](docs/runbooks/service-operations.md),
[docs/operations/observability.md](docs/operations/observability.md),
[docs/operations/persistence.md](docs/operations/persistence.md),
[docs/operations/outbox-dead-letter-recovery.md](docs/operations/outbox-dead-letter-recovery.md), and
[wiki/Operations-Runbook.md](wiki/Operations-Runbook.md).

## Ecosystem Boundaries

Upstream authorities:

- `lotus-core`: portfolio state, holdings, instruments, benchmark assignments,
  clients, products, cashflow, maturity, and mandate facts.
- `lotus-performance`: returns, attribution, active-return posture, benchmark
  context, and performance-health evidence.
- `lotus-risk`: risk metrics, concentration, volatility, drawdown, scenario,
  and mandate-risk posture.
- `lotus-advise`: suitability, policy evaluation, proposal, risk-profile, and
  advisory journey context.
- `lotus-manage`: model portfolio, rebalance workflow, mandate, restriction,
  and action-register context.
- `lotus-report`: report-pack and commentary context after review-gated intent.
- `lotus-ai`: provider-neutral AI workflow, prompt governance, model evaluation,
  RAG, and explanation assistance.

Downstream consumers:

- `lotus-gateway` publishes bounded read paths only after exact route evidence.
- `lotus-workbench` consumes bounded queue/detail proof; full panel proof remains
  blocked until backend truth is certified.
- `lotus-advise`, `lotus-manage`, and `lotus-report` consume review-gated
  conversion or report intent, not portfolio, suitability, rebalance, or report
  authority.
- `lotus-render` and `lotus-archive` remain downstream realization authorities,
  not `lotus-idea` responsibilities.

## Governance

Local gates keep claims grounded:

| Control | Gate |
| --- | --- |
| Support and certification truth | `make implementation-truth-gate`, `make supported-features-gate` |
| Documentation and issue closure | `make documentation-contract-gate`, `make github-issue-closure-matrix-gate` |
| API, review, and conversion-contract truth | `make api-route-metadata-gate`, `make api-problem-details-boundary-gate`, `make api-idempotency-boundary-gate`, `make candidate-state-contract-gate`, `make review-identity-contract-gate`, `make conversion-outcome-contract-gate`, `make openapi-gate` |
| Observability and AI-adjacent proof | `make source-observability-contract-gate`, `make operation-metric-contract-gate`, `make ai-model-risk-ops-contract-gate` |
| Modularity and modern code posture | `make maintainability-gate`, `make duplicate-implementation-gate`, `make private-import-boundary-gate` |
| Local evidence hygiene | `make no-sensitive-content-guard`, `make repository-hygiene-gate` |

Modernization rule: remove stale compatibility paths, legacy vocabulary, and
duplicate local patterns unless a current contract explicitly requires them.

## Documentation Map

Start here:

- [REPOSITORY-ENGINEERING-CONTEXT.md](REPOSITORY-ENGINEERING-CONTEXT.md):
  repository role, current truth, engineering patterns, commands, issue-learning
  loop, and promotion rules.
- [docs/rfcs/README.md](docs/rfcs/README.md): RFC index and slice status.
- [docs/operations/api-certification.md](docs/operations/api-certification.md):
  endpoint certification baseline and ledger rules.
- [docs/operations/supported-feature-promotion.md](docs/operations/supported-feature-promotion.md):
  support-promotion process.
- [docs/architecture/CODEBASE-REVIEW-LEDGER.md](docs/architecture/CODEBASE-REVIEW-LEDGER.md):
  modularity and issue-pattern hardening ledger.
- [docs/architecture/GITHUB-ISSUE-CLOSURE-MATRIX.md](docs/architecture/GITHUB-ISSUE-CLOSURE-MATRIX.md):
  local GitHub issue closure evidence and PR close intent.
- [quality/quality_scorecard.md](quality/quality_scorecard.md): bank-buyable
  quality posture.
- [quality/refactor_decisions.md](quality/refactor_decisions.md): design
  modularity and runtime modularity decisions.
- [wiki/Overview.md](wiki/Overview.md), [wiki/Architecture.md](wiki/Architecture.md),
  [wiki/API-Surface.md](wiki/API-Surface.md), [wiki/Integrations.md](wiki/Integrations.md),
  [wiki/Validation-and-CI.md](wiki/Validation-and-CI.md), and
  [wiki/Supported-Features.md](wiki/Supported-Features.md): authored wiki source.

Repo-local `wiki/` is the authored GitHub wiki source. The separate GitHub wiki
repository is a publication target only and should be updated through the
platform wiki sync flow after the source branch merges to `main`.

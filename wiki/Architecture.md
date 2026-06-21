# Architecture

`lotus-idea` is a separate domain service because opportunity intelligence spans
portfolio facts, performance, risk, advisory, management, reporting, AI, gateway,
and Workbench concerns.

## Source Authority

`lotus-idea` consumes official evidence and carries provenance. It does not
recompute official calculations.

| Domain | Source owner |
| --- | --- |
| Portfolio, holdings, cash, mandate, client, product facts | `lotus-core` |
| Performance and attribution | `lotus-performance` |
| Risk, concentration, volatility, stress, scenarios | `lotus-risk` |
| Proposals, suitability, advisory journey | `lotus-advise` |
| Model portfolios, rebalance, DPM actions | `lotus-manage` |
| AI workflows and model/provider execution | `lotus-ai` |
| Report packages | `lotus-report` |
| Rendering | `lotus-render` |
| Archive, retention, legal hold | `lotus-archive` |
| Product composition | `lotus-gateway` |
| User experience | `lotus-workbench` |

## Data Mesh Baseline

Repo-owned proposed mesh declarations live under `contracts/`:

1. `contracts/domain-data-products/lotus-idea-products.v1.json`
2. `contracts/domain-data-products/lotus-idea-consumers.v1.json`
3. `contracts/domain-data-products/mesh-readiness.v1.json`
4. `contracts/trust-telemetry/idea-candidate.telemetry.v1.json`
5. `contracts/mesh-slo/`
6. `contracts/mesh-access/`
7. `contracts/mesh-evidence/`

Certification is not claimed. Products stay `proposed` and the current static
telemetry is blocked until runtime implementation and platform mesh validation
exist.

The first consumer contract expansion is source-authority only. It prepares the
high-cash / idle-liquidity path around Core-owned cash and holdings products,
and records later first-wave Performance, Risk, Advise, Manage, Report, and AI
dependencies without certifying runtime behavior.

## Source-Port Foundation

RFC-0002 Slice 05 now includes the first Core source-port foundation.
`src/app/ports/core_sources.py` defines the high-cash evidence port,
`src/app/application/high_cash_signal.py` orchestrates evaluation through that
port, and `src/app/infrastructure/lotus_core_sources.py` provides a
conservative HTTP adapter over Core source-data product routes. The adapter
preserves Core source refs and does not infer cash weight from cash totals or
portfolio market values. Positive high-cash generation from live Core remains
blocked until Core reports an explicit source-owned cash-weight field and live
integration proof exists.

## Certified API Foundation

`POST /api/v1/idea-signals/high-cash/evaluate` and
`POST /api/v1/idea-signals/high-cash/evaluate-and-persist` are the first
certified internal API foundations. They evaluate caller-supplied, source-owned
Core evidence and source-reported cash weight, then return deterministic
high-cash signal posture. The persist variant requires `Idempotency-Key` and
`idea.candidate.persist`, writes only to the internal in-memory repository, and
returns `durableStorageBacked=false`. These endpoints do not retrieve live
source data, certify a data product, expose a Gateway route, or promote a
supported business feature.

API modules share the temporary process-local repository through
`src/app/api/repository_state.py`. Signal, review, feedback, queue, and
lifecycle routes must use that provider until the RFC-0002 persistence slice
introduces a database-backed repository adapter, so API modules do not create
duplicate candidate stores.

## Persistence Orchestration Foundation

The internal application layer can now evaluate high-cash evidence and persist
created candidates through the Slice 06 idempotency/audit repository contract.
Repeated requests with the same idempotency payload replay, changed payloads
conflict, and blocked, suppressed, or not-eligible evaluations do not mutate
state. The evaluate-and-persist API exposes this as an internal certified
foundation while still reporting `durableStorageBacked=false`; it is not durable
database support or a supported product workflow.

## Review Queue Projection Foundation

The internal application layer can project persisted candidate snapshots into
deterministic advisor review queues by delegating to the Slice 07 scoring and
queue policy. The projection preserves score-versioned ordering, suppression,
expiry, snooze, unsupported-evidence, and duplicate exclusions without adding a
second queue implementation. It is not yet a public API, Workbench surface,
database-backed queue product, or certified data product.

## Review Workflow Persistence Foundation

The internal application layer can apply governed advisor review actions and
feedback to repository snapshots, then persist accepted decisions, feedback
events, safe audit evidence, lifecycle history, and idempotency replay/conflict
posture through the Slice 06 repository contract. This is still an internal
in-memory foundation, not durable database support, a public API,
Gateway/Workbench functionality, or a supported review product.

## Architecture Decisions

ADRs live in `docs/architecture/adr/`:

1. `ADR-0001-lotus-idea-service-boundary.md`
2. `ADR-0002-scaffold-and-repository-foundation.md`
3. `ADR-0003-source-authority-and-data-mesh-boundaries.md`
4. `ADR-0004-ai-assisted-human-governed-decision-support.md`

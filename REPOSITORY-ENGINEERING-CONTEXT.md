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

RFC-0002 Slice 03 now implements the pure domain model and lifecycle vocabulary
in `src/app/domain/ideas.py`, with unit coverage for source provenance,
unsupported evidence, valid and invalid lifecycle transitions, review authority
boundaries, conversion gating, immutable models, and bounded scoring. It does
not add API, persistence, source adapters, data-product certification, or
supported-feature promotion.

## CI And Merge Governance

`lotus-idea` follows the Lotus rebase-only PR completion model. Do not squash
RFC, workflow, scaffold, or implementation commits; keep small commits linear
and let branch protection require the PR merge gate before `main` updates.
After every merge, delete the remote feature branch and the matching local
feature branch, then re-run branch hygiene before final closure. Durable
RFC/docs/wiki/context/contract truth is complete only when it is present on
`main`, published where required, and not stranded on a side branch.

Coverage aggregation jobs use the current approved `actions/download-artifact`
major and suppress its upstream Node deprecation noise with
`NODE_OPTIONS=--no-deprecation`. Do not downgrade action majors to quiet runner
logs; fix or document the owned warning source instead.

## Architecture And Module Map

1. `src/app/main.py`: application entrypoint, health, readiness, metadata, and
   OpenAPI surface.
2. `src/app/api/`: route modules and DTO mapping. Routes must expose explicit
   idea contracts and must not embed domain logic.
3. `src/app/application/`: use-case orchestration, source aggregation, and
   conversion workflows.
4. `src/app/domain/`: framework-free idea models, lifecycle rules, scoring
   policies, evidence policy, and deterministic governance checks.
5. `src/app/ports/`: interfaces to `lotus-core`, `lotus-performance`,
   `lotus-risk`, `lotus-advise`, `lotus-manage`, `lotus-report`, and `lotus-ai`.
6. `src/app/infrastructure/`: HTTP/database/message adapters behind ports.
7. `src/app/observability/`: correlation, logging, tracing, metrics, and audit
   event helpers.
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

## Validation And CI Expectations

`lotus-idea` follows the standard Lotus backend lane model:

1. feature lane for fast branch feedback,
2. PR merge gate for required merge readiness,
3. main releasability for post-merge truth.

Required baseline checks include lint, format check, typecheck, architecture
boundary enforcement, OpenAPI quality, supported-feature gate,
endpoint-certification gate, unit tests, integration tests, e2e tests, coverage
gate, security audit, and Docker build validation.

Every RFC slice that exposes behavior must update endpoint certification,
supported-feature registration, docs/wiki truth, observability, and regression
tests in the same change.

Data-mesh declarations are repo-owned from day one, but certification remains
`not_certified` until implementation-backed products emit runtime telemetry,
the platform source manifest includes `lotus-idea`, and platform mesh gates pass.

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

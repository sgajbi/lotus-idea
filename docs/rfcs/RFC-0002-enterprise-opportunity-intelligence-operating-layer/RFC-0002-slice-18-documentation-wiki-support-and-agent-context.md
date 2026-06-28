# RFC-0002 Slice 18: Documentation, Wiki, Support, And Agent Context

Status: Partially implemented - API certification, outbox readiness, implementation-proof, live source-proof contract, scheduled-worker proof contract, durable repository proof contract, runtime telemetry proof contract, bounded Workbench read-path proof, bounded Gateway/Workbench operational proof, bounded Gateway/Workbench discovery proof, bounded downstream route proof, bounded outbox broker proof, bounded outbox platform mesh event publication proof, mesh policy proof, AI lineage store proof, Manage mandate live proof, low-income Core cashflow live proof, missing risk-profile live proof, bond-maturity and missing-benchmark policy foundation truth, client-demo process, and downstream contract documentation synchronized

## Outcome

Update durable documentation and agent guidance to match implemented truth.

## Current Implementation Evidence

This slice is partially implemented for API certification documentation truth and
durable operating-context enforcement:

1. `docs/operations/api-certification.md` now lists the full certified internal
   foundation endpoint inventory from
   `docs/operations/endpoint-certification-ledger.json`, including high-cash
   evaluation, high-cash persistence, candidate evidence replay, lifecycle
   transition, AI explanation evaluation, advisor queue, review action,
   feedback, conversion intent, conversion outcome, report evidence-pack
   request, data-mesh-readiness, outbox-delivery-readiness, and
   implementation-proof-readiness diagnostic endpoints.
2. The certification guide records each endpoint's current foundation scope,
   required capability, and unsupported boundary so future agents do not
   promote internal API foundations as business-supported product features.
3. The guide keeps baseline health and metadata endpoints separate with
   `baseline_certified` posture.
4. README, repository context, RFC index, and wiki source are updated in the
   same slice when documentation truth changes.
5. `docs/operations/ai-governance.md` now describes the certified internal AI
   evaluator API while preserving the unsupported boundary around provider
   execution, workflow-pack runtime, certified model-risk operations,
   Gateway/Workbench proof, and supported feature promotion. The source-safe
   AI lineage store proof clears only the aggregate lineage-store blocker and
   does not certify `lotus-ai` runtime execution or external AI support.
6. `make documentation-contract-gate` now runs through `make lint` and blocks
   removal, thinning, missing anchors, or placeholder erosion across the
   required README, repository context, enterprise standard, runbook, RFC
   index, quality, evidence, and wiki surfaces future implementation agents
   depend on. It also enforces a polished proof/readiness guide profile so
   operator-facing diagnostics use current-truth tables, proof and non-proof
   boundaries, blocker sections, response-shape tables, evidence references,
   and executable examples instead of raw text dumps.
7. Focused unit coverage proves the documentation contract gate passes current
   repository truth and fails missing, thin, missing-anchor, and placeholder
   documentation surfaces, plus unpolished operator diagnostics without
   required headings, tables, or command examples.
8. `docs/operations/implementation-proof-readiness.md`, README, repository
   context, demo claims, operations runbooks, and wiki source now describe the
   certified internal implementation-proof readiness diagnostic, including the
   outbox-delivery proof family, and preserve its no-external-publication and
   no-supported-feature-promotion boundaries.
9. `docs/operations/downstream-realization-readiness.md`, README, repository
   context, API certification docs, demo claims, operations runbooks, RFC
   index, quality scorecard, and wiki source now describe the certified
   internal downstream realization readiness diagnostic with a polished
   operator-facing structure: current truth, proof boundary, blockers,
   response shape, evidence, and executable example.
10. `docs/operations/implementation-proof-readiness.md` now uses the same
    polished operator-facing structure and is protected by the documentation
    contract gate, making implementation proof posture readable for business,
    engineering, operations, release, and demo reviewers without overclaiming
    live proof, certified live broker runtime, downstream delivery, or
    supported-feature promotion.
11. `docs/demo/README.md`, `docs/demo/client-demo-operating-process.md`,
    `docs/demo/client-facing-lotus-idea-brief.md`,
    `docs/demo/client-demo-pack.template.md`, `docs/demo/demo-claims.md`, and
    `wiki/Demo-Readiness.md` now give client, sales, marketing, product,
    operations, and engineering reviewers a polished process for explaining
    what Lotus is doing, which claims are implementation-backed, and which
    boundaries remain blocked before any client-facing pack is marked
    client-ready.
12. README, repository context, `docs/operations/api-certification.md`,
    `docs/operations/persistence.md`, `docs/operations/observability.md`, RFC
    index, quality scorecard, and wiki source now describe the certified
    internal outbox delivery readiness diagnostic, bounded run-once operator
    action, and HTTP publisher adapter foundation while preserving the boundary
    that no certified live broker runtime, downstream delivery, platform mesh
    event certification, Gateway/Workbench proof, or supported-feature
    promotion exists.
13. README, repository context, `docs/operations/downstream-realization-readiness.md`,
    `docs/operations/api-certification.md`, quality guides, RFC evidence, and
    wiki source now describe the governed downstream contract plan and
    `make downstream-realization-contract-gate` while preserving the boundary
    that no downstream route existence, downstream execution, or
    supported-feature promotion exists.
13. README, repository context,
    `docs/operations/downstream-realization-readiness.md`,
    `docs/operations/implementation-proof-readiness.md`, quality scorecard,
    RFC evidence, and wiki source now describe bounded Advise proposal and
    Manage action route-proof generation, aggregate consumption, and
    `make downstream-route-contract-proof-gate`, while preserving the boundary
    that valid artifacts clear only route-foundation blockers and do not grant
    suitability, policy approval, mandate/rebalance authority, execution,
    client communication, or supported-feature promotion.
13. README, repository context, `docs/operations/source-ingestion-run-once.md`,
    `docs/operations/api-certification.md`, observability and persistence
    guides, quality scorecard, RFC evidence, and wiki source now describe the
    certified internal `POST /api/v1/source-ingestion/run-once` operator action
    while preserving the boundary that bounded live Core source-ingestion proof
    is proof evidence only, not live Core source certification, scheduled worker
    deploy-contract proof through that endpoint, certified long-running
    scheduled runtime, Gateway/Workbench proof, or supported-feature promotion.
14. README, repository context, `docs/operations/source-ingestion-run-once.md`,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs,
    RFC evidence, and wiki source now describe the live source-proof artifact
    contract, aggregate source-safe `blockReasonCounts`, and
    `make source-ingestion-live-proof-contract-gate`, while preserving the
    boundary that a valid artifact clears only the live-Core blocker and does
    not promote source ingestion as a supported feature.
15. README, repository context, `docs/operations/source-ingestion-run-once.md`,
    `docs/operations/api-certification.md`, `docs/operations/observability.md`,
    `docs/operations/implementation-proof-readiness.md`, demo claims, quality
    docs, RFC evidence, and wiki source now describe the scheduled worker
    entrypoint, Compose worker profile, deploy-proof artifact contract, and
    `make source-ingestion-scheduled-worker-check`, while preserving the
    boundary that a valid artifact clears only the scheduled-worker deploy-proof
    blocker and does not promote source ingestion as a supported feature.
16. README, repository context, `docs/operations/persistence.md`,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs,
    RFC evidence, and wiki source now describe the durable repository proof
    artifact contract and `make durable-repository-proof-contract-gate`, while
    preserving the boundary that a valid artifact clears only aggregate
    proof-readiness storage blockers and does not configure runtime storage,
    replace PostgreSQL runtime proof, certify production storage, or promote a
    supported feature.
17. README, repository context, `docs/operations/implementation-proof-readiness.md`,
    `docs/operations/mesh-readiness.md`, quality gate docs, RFC evidence, and
    wiki source now describe the runtime trust telemetry proof artifact contract
    and `make runtime-trust-telemetry-proof-contract-gate`, while preserving the
    boundary that a valid artifact clears only the aggregate candidate-snapshot
    blocker and does not certify the platform mesh or promote support.
18. README, repository context, API certification docs, demo claims, RFC
    evidence, and wiki source now describe `lotus-workbench` PR #391 as
    bounded read-only Workbench queue/detail rendering through Gateway, while
    preserving the boundary that full live proof, entitlement-denied proof,
    mutation affordances, downstream realization, data-product certification,
    and supported-feature promotion remain blocked.
19. README, repository context,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs, RFC
    evidence, and wiki source now describe the Workbench read-path proof
    artifact contract and `make workbench-read-path-proof-contract-gate`, while
    preserving the boundary that a valid artifact clears only
    `workbench_gateway_bff_consumption_proof_missing` and does not certify a
    full Workbench panel, canonical demo runtime, or supported feature.
20. README, repository context,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs, RFC
    evidence, and wiki source now describe the Gateway/Workbench operational
    proof artifact and `make gateway-workbench-operational-proof-contract-gate`,
    while preserving the boundary that a valid artifact clears only
    `gateway_workbench_proof_missing` for source-ingestion and outbox-delivery
    proof families and does not certify Workbench product proof, browser proof,
    canonical demo runtime, data-product discovery, or supported features.
21. README, repository context,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs, RFC
    evidence, and wiki source now describe the Gateway/Workbench discovery
    proof artifact and `make gateway-workbench-discovery-proof-contract-gate`,
    while preserving the boundary that a valid artifact clears only
    `gateway_workbench_discovery_proof_missing` for data-mesh and runtime trust
    telemetry proof families and does not certify data-mesh products, activate
    producer products, certify full Workbench product behavior, or promote
    supported features.
21. README, repository context,
    `docs/operations/implementation-proof-readiness.md`, RFC evidence, and
    wiki source now describe that the live implementation-proof readiness API
    consumes configured source-ingestion live, source-ingestion scheduled-worker,
    durable repository, runtime trust telemetry, and Workbench read-path proof
    artifact paths, records validated source-safe artifact refs in capability
    evidence, and preserves the boundary that only matching aggregate blockers
    are cleared and no certification or supported-feature promotion is implied.
21. README, repository context,
    `docs/operations/implementation-proof-readiness.md`,
    `docs/operations/persistence.md`, quality gate docs, RFC evidence, and wiki
    source now describe the bounded outbox broker proof artifact, its aggregate
    blocker-clearance scope, and its remaining external-publication,
    downstream-consumer, mesh-event, Gateway/Workbench, and supported-feature
    boundaries.
22. README, repository context,
    `docs/operations/implementation-proof-readiness.md`, RFC evidence, demo
    claims, and wiki source now describe the bounded outbox platform mesh event
    publication proof artifact, its default generated output, its aggregate
    blocker-clearance scope, and its remaining external broker publication,
    downstream delivery, Gateway/Workbench, client-ready publication, and
    supported-feature boundaries.
23. README, repository context,
    `docs/operations/implementation-proof-readiness.md`,
    `docs/operations/mesh-readiness.md`, service runbooks, quality gate docs,
    RFC evidence, and wiki source now describe default platform mesh onboarding
    proof generation and aggregate consumption while preserving the boundary
    that missing sibling evidence is a non-proof artifact and no platform mesh
    certification, active product declaration, Gateway/Workbench discovery, or
    supported-feature promotion is implied.
24. README, repository context,
    `docs/operations/implementation-proof-readiness.md`,
    `docs/operations/mesh-readiness.md`, quality gate docs, RFC evidence, and
    wiki source now describe default mesh policy proof generation and aggregate
    consumption while preserving the boundary that local SLO/access/evidence
    policy proof clears only repo-owned policy blockers and does not certify
    the platform mesh, activate products, prove Gateway/Workbench discovery, or
    promote supported features.
25. `docs/demo/README.md` now gives client-demo teams a governed entry point
    for explaining what Lotus Idea is doing, choosing the right process
    artifact, tying claims to proof, and keeping unsupported autonomy,
    suitability, execution, publication, downstream materialization, and
    certified data-product claims out of client material.
26. README, repository context, `docs/operations/implementation-proof-readiness.md`,
    service runbooks, quality gate docs, RFC evidence, demo claims, and wiki
    source now describe bounded Manage mandate live proof while preserving the
    boundary that a valid artifact clears only the portfolio-scoped Manage
    source blocker and does not prove mandate performance or risk health, Core
    portfolio state, data-mesh certification, Workbench support, client
    publication, supported features, rebalance authority, action authority,
    order creation, execution, or settlement.
27. README, repository context, `docs/operations/implementation-proof-readiness.md`,
    RFC evidence, demo claims, and wiki source now describe bounded low-income
    Core cashflow live proof while preserving the boundary that a valid
    artifact clears only the low-income Core cashflow source blocker and does
    not certify client income needs, funding advice, treasury instruction,
    suitability, planning objectives, data mesh, Workbench behavior, client
    publication, or supported-feature promotion.
28. README, repository context, RFC evidence, demo claims, and wiki source now
    describe the bounded bond-maturity / reinvestment policy foundation while
    preserving the boundary that no live Core maturity source contract, data
    mesh certification, Workbench product proof, client publication, product
    recommendation, reinvestment advice, or supported-feature promotion exists.

This documentation slice does not promote any supported feature. It records
bounded Workbench read-path proof, Gateway/Workbench operational proof, and
Gateway/Workbench discovery proof only; it does not add full
Gateway/Workbench live proof, data-product certification, downstream
realization, live source certification, or certified long-running scheduled
runtime proof. The bond-maturity / reinvestment update records only
deterministic policy and source-port truth; it does not prove source-backed
generation or promote a client-ready reinvestment journey.

## Required Work

1. Update README, repository context, API docs, operations docs, data-product
   docs, model-risk docs, demo docs, supported features, and wiki source.
2. Run wiki check-only validation.
3. Update `lotus-platform` scaffold/context or skill routing only if reusable
   Lotus guidance changed.
4. Record explicit no-change decisions for platform context, wiki, or skills
   where no update is required.

## Wiki Page Standard

The repo-local wiki source must include current-state pages for:

1. Home,
2. Overview,
3. Architecture,
4. Getting Started,
5. Development Workflow,
6. Validation And CI,
7. RFC Index,
8. Integrations,
9. Supported Features,
10. Operations Runbook,
11. Security And Governance,
12. Demo Readiness,
13. Roadmap.

Pages must summarize and route to source docs. They must not duplicate RFC
mechanics or promote planned target-state behavior as supported capability.

## Acceptance Gate

1. Docs describe actual endpoints, modules, fields, proof artifacts, and
   constraints.
2. Wiki summarizes and routes to source docs without stale duplication.
3. Supported features are implementation-backed.
4. Future agents can pick up the repository without rediscovering boundaries.

# RFC-0002 Slice 18: Documentation, Wiki, Support, And Agent Context

Status: Partially implemented - API certification, outbox readiness, implementation-proof, live source-proof contract, scheduled-worker proof contract, durable repository proof contract, runtime telemetry proof contract, bounded Workbench read-path proof, and downstream contract documentation synchronized

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
   execution, certified AI lineage-store proof, Gateway/Workbench proof, and supported
   feature promotion.
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
11. README, repository context, `docs/operations/api-certification.md`,
    `docs/operations/persistence.md`, `docs/operations/observability.md`, RFC
    index, quality scorecard, and wiki source now describe the certified
    internal outbox delivery readiness diagnostic, bounded run-once operator
    action, and HTTP publisher adapter foundation while preserving the boundary
    that no certified live broker runtime, downstream delivery, platform mesh
    event certification, Gateway/Workbench proof, or supported-feature
    promotion exists.
12. README, repository context, `docs/operations/downstream-realization-readiness.md`,
    `docs/operations/api-certification.md`, quality guides, RFC evidence, and
    wiki source now describe the governed downstream contract plan and
    `make downstream-realization-contract-gate` while preserving the boundary
    that no downstream route existence, downstream execution, or
    supported-feature promotion exists.
13. README, repository context, `docs/operations/source-ingestion-run-once.md`,
    `docs/operations/api-certification.md`, observability and persistence
    guides, quality scorecard, RFC evidence, and wiki source now describe the
    certified internal `POST /api/v1/source-ingestion/run-once` operator action
    while preserving the boundary that no live Core source certification,
    scheduled worker deploy-contract proof through that endpoint, certified
    long-running scheduled runtime, Gateway/Workbench proof, or supported-feature
    promotion exists.
14. README, repository context, `docs/operations/source-ingestion-run-once.md`,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs,
    RFC evidence, and wiki source now describe the live source-proof artifact
    contract and `make source-ingestion-live-proof-contract-gate`, while
    preserving the boundary that a valid artifact clears only the live-Core
    blocker and does not promote source ingestion as a supported feature.
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

This documentation slice does not promote any supported feature. It records
bounded Workbench read-path proof only; it does not add full
Gateway/Workbench live proof, data-product certification, downstream
realization, live source certification, or certified long-running scheduled
runtime proof.

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

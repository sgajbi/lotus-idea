# RFC-0002 Slice 18: Documentation, Wiki, Support, And Agent Context

Status: Partially implemented - API certification, outbox readiness, implementation-proof, and downstream contract documentation synchronized

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
   execution, durable AI lineage, Gateway/Workbench proof, and supported
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

This documentation slice does not promote any supported feature. It does not
add Gateway/Workbench proof, durable persistence, data-product certification,
downstream realization, or live source ingestion.

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

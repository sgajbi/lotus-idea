# RFC-0002 Slice 18: Documentation, Wiki, Support, And Agent Context

Status: Partially implemented - API certification documentation synchronized

## Outcome

Update durable documentation and agent guidance to match implemented truth.

## Current Implementation Evidence

This slice is partially implemented for API certification documentation truth:

1. `docs/operations/api-certification.md` now lists the full certified internal
   foundation endpoint inventory from
   `docs/operations/endpoint-certification-ledger.json`, including high-cash
   evaluation, high-cash persistence, lifecycle transition, AI explanation
   evaluation, advisor queue, review action, feedback, conversion intent,
   conversion outcome, report evidence-pack request, and data-mesh-readiness
   diagnostic endpoints.
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

This documentation slice does not promote any supported feature. It does not
add Gateway/Workbench proof, durable persistence, data-product certification,
downstream realization, or live source ingestion.

## Required Work

1. Update README, repository context, API docs, operations docs, data-product
   docs, model-risk docs, demo docs, supported features, and wiki source.
2. Run wiki check-only validation.
3. Update `lotus-platform` context or skill routing only if reusable Lotus
   guidance changed.
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

# RFC-0002 Slice 18: Documentation, Wiki, Support, And Agent Context

Status: Planned

## Outcome

Update durable documentation and agent guidance to match implemented truth.

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

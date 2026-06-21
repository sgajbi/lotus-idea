# RFC-0002 Slice 10: Certified APIs, OpenAPI, And Gateway Contract

Status: Planned

## Outcome

Expose certified `lotus-idea` APIs and Gateway routes for supported behavior.

## Required Work

1. Implement route families approved by prior slices.
2. Add complete OpenAPI descriptions, examples, error cases, degraded cases,
   unsupported-evidence cases, idempotency behavior, and entitlement behavior.
3. Update endpoint certification ledger.
4. Add `lotus-gateway` contracts and routes without Gateway-side idea
   generation or ranking.

## Acceptance Gate

1. OpenAPI quality gate passes.
2. Endpoint certification passes for every supported endpoint.
3. Gateway contract tests prove source-owned `lotus-idea` truth is preserved.
4. No alias or stale endpoint remains without explicit time-boxed justification.

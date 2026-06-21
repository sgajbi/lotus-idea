# ADR-0001: lotus-idea Service Boundary

Status: Accepted

Date: 2026-06-21

## Context

The Lotus ecosystem already contains source services for portfolio facts,
performance, risk, advisory proposals, model portfolio management, reporting,
rendering, archiving, AI infrastructure, gateway composition, and Workbench UI.

The proposed idea capability crosses several of those domains. If it is placed
inside one existing service, it will either duplicate other services'
calculations or make one workflow service the hidden owner of cross-domain
opportunity lifecycle.

## Decision

Create `lotus-idea` as a separate Lotus domain service.

`lotus-idea` owns opportunity detection policy, idea candidate identity, scoring,
ranking, lifecycle state, review state, governed evidence, feedback, and
conversion intent.

`lotus-idea` consumes source-owned evidence from `lotus-core`,
`lotus-performance`, `lotus-risk`, `lotus-advise`, `lotus-manage`,
`lotus-report`, and `lotus-ai`.

## Consequences

Positive:

1. idea lifecycle has one source of truth,
2. advisory and portfolio-management workflows can consume the same reviewed
   idea evidence,
3. `lotus-ai` remains a shared AI capability rather than a business workflow
   owner,
4. risk, performance, and core calculations stay source-owned.

Tradeoffs:

1. initial integration work is broader than adding a feature to one existing
   app,
2. contracts must be explicit before UI or workflow implementation,
3. source authority must be enforced through tests and API certification.

## Guardrails

`lotus-idea` must not own official performance, risk, suitability, compliance,
mandate, execution, report-rendering, archive, or AI-provider decisions.

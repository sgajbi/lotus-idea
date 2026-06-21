# RFC-0001: Repository Foundation And Service Boundary

Status: Draft

Owner: lotus-idea

Created: 2026-06-21

## Summary

Create the governed `lotus-idea` repository foundation as a public Lotus
service, with branch protection, ADRs, RFCs, source wiki, CI lane posture,
supported-feature discipline, and platform registrations before business feature
implementation begins.

## Business Outcome

Lotus needs a clean service boundary for wealth opportunity intelligence so
future client demos show a credible enterprise build path instead of a feature
hidden inside `lotus-advise`, `lotus-manage`, or `lotus-ai`.

This RFC establishes the foundation only. It does not implement idea generation,
scoring, review, conversion, AI explanations, UI panels, or report output.

## Scope

In scope:

1. scaffold `lotus-idea` from Lotus platform automation,
2. create public GitHub repository,
3. protect `main`,
4. register the repository in platform registries,
5. create README, repository context, wiki source, ADRs, and RFC suite,
6. keep supported features empty until implementation exists,
7. run baseline validation.

Out of scope:

1. business endpoints beyond scaffold health/metadata,
2. database schema,
3. idea detection or scoring logic,
4. Workbench panels,
5. downstream conversion implementation,
6. AI workflow integration.

## Source Authority And Dependency Map

`lotus-platform` owns scaffolding, platform registries, CI lane policy,
repository standards, wiki sync automation, and bank-buyable governance.

`lotus-idea` owns only repository-local truth created in this RFC.

## Architecture Decisions

This RFC depends on:

1. `ADR-0001-lotus-idea-service-boundary.md`
2. `ADR-0002-scaffold-and-repository-foundation.md`
3. `ADR-0003-source-authority-and-data-mesh-boundaries.md`
4. `ADR-0004-ai-assisted-human-governed-decision-support.md`

## Data Contracts

No implementation-backed business data products are introduced by this RFC.
Repo-owned data-mesh declarations may exist as proposed contracts only; they
must remain `not_certified` until a later implementation slice provides runtime
behavior, source-manifest inclusion, live telemetry, and platform certification.

## API Impact

Only scaffold health, readiness, metadata, and metrics surfaces are in scope.
Any idea business endpoint requires a later RFC.

## Security And Privacy

The repository must inherit scaffold security posture:

1. no secrets in source,
2. no sensitive demo data,
3. security audit target,
4. protected `main`,
5. CI gate definitions,
6. supported-feature gate.

## Observability And Support

Scaffold observability files and operations docs are accepted as baseline only.
Business metrics, audit events, and SLOs are deferred to later RFCs.

## Test And Certification Plan

Required validation:

1. `make install`
2. `make lint`
3. `make typecheck`
4. `make openapi-gate`
5. `make check`
6. platform context validation after generated platform registry changes
7. GitHub repository and branch-protection verification

## Documentation And Wiki

This RFC creates or updates:

1. `README.md`
2. `REPOSITORY-ENGINEERING-CONTEXT.md`
3. `docs/architecture/`
4. `docs/rfcs/`
5. `wiki/`
6. `supported-features/supported-features.json`

## Required Slices

1. Platform/scaffold improvement slice: generate service from platform scaffold
   and keep platform registries synchronized.
2. Cleanup/refactor slice: replace generic scaffold docs with service-specific
   truth.
3. Implementation proof slice: verify local validation and GitHub setup.
4. Hardening/review slice: check repo status, branch protection, supported
   features, wiki source, and RFC completeness.
5. Final closure slice: commit and push foundation truth; record any remaining
   validation gaps.

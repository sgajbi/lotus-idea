# Codebase Review Playbook

This playbook keeps lotus-idea cleanup and refactoring work tied to measured
bank-buyable controls instead of ad hoc file churn.

## Review Units

Use pattern-based review units before file-by-file review:

1. API route orchestration and error mapping.
2. Application service use-case boundaries.
3. Domain lifecycle, review, scoring, and evidence invariants.
4. Repository query shape, idempotency, replay, and audit persistence.
5. Runtime composition, readiness, and operator diagnostics.
6. CI, documentation, wiki, supported-features, and quality evidence gates.

## Status Model

| Status | Meaning |
| --- | --- |
| `Candidate` | Pattern identified; no implementation change has landed yet. |
| `Hardened` | A scoped fix landed with code, tests, and validation evidence. |
| `Refactor Needed` | Risk remains and needs a later scoped implementation slice. |
| `Signed Off` | Scope has implementation, tests, local gates, remote evidence, and no open same-pattern findings. |

## Evidence Standard

Every `Hardened` or `Signed Off` entry must name the affected code, the
behavior preserved or changed, tests run, quality gates run, and whether the
slice changed design modularity only or also changed runtime modularity.

Do not use this playbook to justify a new runtime service. lotus-idea should
first reduce design-time complexity through cohesive internal modules and stable
interfaces. Introduce a separate process, service, queue, or independently
scalable deployment boundary only when workload isolation, failure isolation,
ownership, security, or operability evidence justifies the runtime cost.

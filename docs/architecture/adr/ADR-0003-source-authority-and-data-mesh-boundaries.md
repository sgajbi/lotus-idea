# ADR-0003: Source Authority And Data Mesh Boundaries

Status: Accepted

Date: 2026-06-21

## Context

Idea generation depends on signals from multiple domain services. Banking-grade
implementation requires a source-authority map so `lotus-idea` can explain why
an idea exists without duplicating official calculations.

## Decision

`lotus-idea` will use data-mesh style contracts for all material inputs and
outputs.

Input products are consumer contracts from source-owned services. Output
products are producer contracts from `lotus-idea`, including candidate ideas,
review queues, evidence packs, feedback, suppression decisions, and conversion
outcomes.

Each persisted or emitted idea must carry:

1. source system,
2. source endpoint or data product,
3. source record identity,
4. as-of date or calculation timestamp,
5. calculation provenance,
6. freshness policy,
7. evidence version,
8. lifecycle version.

## Consequences

`lotus-idea` can be audited and demoed as an orchestration service with clear
source provenance. It also avoids silent drift from official performance, risk,
core, advisory, and portfolio-management calculations.

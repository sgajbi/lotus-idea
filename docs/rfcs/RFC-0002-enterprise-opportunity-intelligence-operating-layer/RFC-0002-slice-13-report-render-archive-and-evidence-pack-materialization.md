# RFC-0002 Slice 13: Report, Render, Archive, And Evidence-Pack Materialization

Status: Planned

## Outcome

Materialize reviewed idea evidence through reporting, rendering, and archiving
services where product claims require documentable proof.

## Required Work

1. Define reportable idea evidence package.
2. Integrate with `lotus-report` for report package intake.
3. Integrate with `lotus-render` for deterministic render projections.
4. Integrate with `lotus-archive` for archive metadata, retention, legal hold
   posture, retrieval refs, and access audit.

## Acceptance Gate

1. Only reviewed idea evidence can be materialized.
2. Rendered output matches source evidence and review state.
3. Archive refs preserve lineage and access posture.
4. Client-ready publication remains blocked unless explicitly supported and
   proven.

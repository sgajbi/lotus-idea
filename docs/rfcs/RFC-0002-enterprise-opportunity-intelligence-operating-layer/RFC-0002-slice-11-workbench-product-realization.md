# RFC-0002 Slice 11: Workbench Product Realization

Status: Planned

## Outcome

Make supported opportunity intelligence visible in `lotus-workbench` through
Gateway/BFF only.

## Required Work

1. Add opportunity queue, evidence drawer, review action, feedback, and
   conversion affordances for supported roles.
2. Show source refs, reason codes, score posture, freshness, unsupported
   evidence, AI review posture, and downstream conversion status.
3. Add browser, accessibility, responsive, empty, loading, degraded, and
   entitlement-denied proof.
4. Prevent UI-side reconstruction of idea facts or score.

## Acceptance Gate

1. Workbench consumes Gateway only.
2. Browser proof covers canonical supported, unsupported, degraded, and denied
   states.
3. UI copy uses advisor-safe private-banking language.
4. No demo screenshot is promoted before API and panel validation pass.

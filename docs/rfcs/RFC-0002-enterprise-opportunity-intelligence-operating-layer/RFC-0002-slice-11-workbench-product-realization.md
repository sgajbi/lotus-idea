# RFC-0002 Slice 11: Workbench Product Realization

Status: Partially implemented - bounded Workbench read-only advisor queue/detail rendering exists; full live proof and support remain pending

Current implementation note: RFC-0002 Slice 10 now provides
`GET /api/v1/idea-candidates/{candidateId}` as a certified internal,
source-safe candidate detail API foundation for a future Workbench evidence
drawer, and `lotus-gateway` now publishes bounded read-only advisor queue and
candidate detail routes. `lotus-workbench` PR #391 merged to `main` at
`56ce0614875e8b6ecd4df259ef14a1631ea8a4ac` and implements bounded
Gateway/BFF-backed rendering for the advisor idea queue and source-safe
candidate detail. The Workbench helper forwards the required Idea caller
headers, unwraps Gateway envelopes, keeps candidate detail inside Workbench
routing, and the canonical live-validation script now requires a populated
candidate row, loaded detail fields, and observed post-navigation route
evidence before accepting the opportunities screenshot.

This is still a read-only product-surface foundation. It does not implement
review actions, feedback, conversion affordances, entitlement-denied panel
proof, full canonical live stack proof, data-product certification, demo-ready
screenshots, or supported-feature promotion.

The repo-owned Gateway/Workbench contract artifact is classified as
`source_contract`. It can record the declared queue/detail routes and bounded
read-path contract as evidence, but it clears no runtime blocker and does not
replace machine-verifiable Gateway serving, Workbench rendering, entitlement,
accessibility, or canonical front-office runtime proof.

## Outcome

Make supported opportunity intelligence visible in `lotus-workbench` through
Gateway/BFF only.

## Required Work

1. Extend the bounded read-only opportunity queue and candidate-detail panel
   into review action, feedback, and conversion affordances for supported
   roles.
2. Show source refs, reason codes, score posture, freshness, unsupported
   evidence, AI review posture, and downstream conversion status.
3. Add browser, accessibility, responsive, empty, loading, degraded, and
   entitlement-denied proof.
4. Prevent UI-side reconstruction of idea facts or score.

## Acceptance Gate

1. Workbench consumes Gateway only for Idea truth; PR #391 satisfies this for
   the bounded read-only advisor queue/detail path.
2. Browser proof covers canonical supported, unsupported, degraded, and denied
   states.
3. UI copy uses advisor-safe private-banking language.
4. No demo screenshot is promoted before API and panel validation pass.

# RFC-0002 Slice 11: Workbench Product Realization

Status: Partially implemented - bounded Gateway/Workbench queue, detail, review-action, feedback, and conversion-intent controls exist; full live proof and support remain pending

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

Gateway PR #498 merged at `eeba84510d4449c9d181671b9b68d8af24f474cb` and
publishes typed BFF routes for Idea-owned review actions, feedback, and bounded
conversion intents. Workbench PR #435 merged at
`97c57b21a9626f3f1ebcdade49252d6b599ae1dd` and adds the corresponding
candidate-panel controls. Workbench PR #438 merged at
`6212861c2bb6fe7344ad17dd391cda5a8f81a73f` and makes its BFF authority mode
explicit: `development_configured` is permitted only for local, development,
and test. The BFF strips any client-supplied Idea authority, rejects
unallowlisted Idea paths, and fails closed before Gateway for unconfigured or
non-development authority. The development fixture is not an authenticated
principal, session, or token-claims implementation. The controls record only
Idea-owned workflow state; they do not create proposals, clear restrictions,
approve suitability, or execute portfolio actions.

This remains a bounded product-surface foundation. It does not provide an
end-user identity-provider integration, entitlement-denied panel proof, full
canonical live-stack proof, data-product certification, demo-ready screenshots,
or supported-feature promotion. Workbench #436 and platform #563 own the
authenticated end-user principal/session contract; Idea #380 records the
resulting certification and promotion dependency. The Slice 11 canonical proof
remains deferred until an all-main cross-service runtime can be validated
without treating a development fixture or branch-local evidence as product
certification.

The repo-owned Gateway/Workbench contract artifact is classified as
`source_contract`. It can record the declared queue/detail routes and bounded
read-path contract as evidence, but it clears no runtime blocker and does not
replace machine-verifiable Gateway serving, Workbench rendering, entitlement,
accessibility, or canonical front-office runtime proof.

The repo-owned discovery contract artifact is also `source_contract` evidence.
It validates proposed product declarations and declared Gateway consumption,
but clears no blocker and preserves `gateway_workbench_discovery_proof_missing`.
Active catalog publication, Gateway discovery, Workbench consumption,
entitlement enforcement, and product support still require runtime evidence
from the owning applications.

## Outcome

Make supported opportunity intelligence visible in `lotus-workbench` through
Gateway/BFF only.

## Required Work

1. Bounded queue/detail review action, feedback, and conversion-intent
   affordances are implemented through Gateway/BFF only; complete the
   authenticated-principal and runtime proof needed before treating role
   authorization as product-certified.
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

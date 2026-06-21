# RFC Index

Primary RFCs:

1. `docs/rfcs/RFC-0001-repository-foundation-and-service-boundary.md`
2. `docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-enterprise-opportunity-intelligence-operating-layer.md`

RFC-0002 is the end-to-end implementation program. It includes slice files for
source mapping, platform scaffolding review, cleanup, domain model, source
contracts, signal generation, persistence, scoring, review, AI explanation,
certified APIs, Gateway, Workbench, Advise/Manage conversion,
Report/Render/Archive materialization, data products, operations, demo
readiness, live proof, documentation, hardening, and closure.

Current RFC-0002 implementation-start baseline:

1. Slice 00 is recorded as complete for source mapping and product-gap
   allocation.
2. Slice 03 implements the pure domain model and lifecycle foundation without
   API, persistence, or supported-feature promotion.
3. Slice 04 partially implements the source-authority and data-mesh baseline,
   including proposed producer contracts, consumer dependencies, blocked static
   trust telemetry, SLO/access/evidence policy files, and a repo-native
   `data-mesh-contract-gate`. Platform mesh certification remains planned.
4. Slice 05 partially implements the high-cash / idle-liquidity deterministic
   domain policy without source adapters, API, or supported-feature promotion.
5. Slice 06 partially implements internal candidate persistence records,
   evidence replay posture, idempotency conflict handling, idempotent lifecycle
   transition recording, lifecycle audit history, and snapshot recovery without
   database migrations, database-backed API state, or supported-feature
   promotion.
6. Slice 07 partially implements internal deterministic scoring, score reason
   codes, priority buckets, stable queue projection, snooze, suppression,
   deduplication, expiry, unsupported-evidence, and unscored-candidate
   exclusions plus a certified internal advisor queue API foundation without
   persisted queue state, Gateway, Workbench, or supported-feature promotion.
7. Slice 08 partially implements internal advisor review and feedback
   governance with fail-closed scope checks, review actions, safe audit events,
   source provenance, queue projection interaction, repository-backed
   persistence orchestration, and certified internal review/feedback API
   foundations without database-backed review persistence, Gateway, Workbench,
   PM/compliance/operator queue surfaces, or supported-feature promotion.
8. Slice 09 partially implements internal AI governance with redacted evidence
   envelopes, forbidden metadata rejection, deterministic fallback,
   unsupported-claim and forbidden-action verifier outcomes, safe audit events,
   and no AI downstream authority without `lotus-ai` runtime execution, API,
   Gateway, Workbench, or supported-feature promotion.
9. Slice 10 partially implements certified internal API foundations for
   high-cash evaluation, high-cash evaluate-and-persist, candidate lifecycle
   transitions, advisor queues, review actions, feedback, conversion intent,
   and conversion outcome. Gateway, Workbench, live source adapters,
   data-product certification, and supported-feature promotion remain planned.
10. Slice 12 partially implements internal conversion governance for
   review-gated conversion intent and downstream outcome tracking, with
   target-to-source-authority mapping for `lotus-advise`, `lotus-manage`, and
   `lotus-report`, plus certified internal API foundations. It does not invoke
   downstream adapters, create downstream records, or promote a supported
   feature.
11. The first opportunity journey is high cash / idle liquidity for
   `PB_SG_GLOBAL_BAL_001`.
12. The first review audience is advisor only.
13. The first downstream conversion posture is report-only evidence after
   advisor review.
14. Business features remain unsupported until later slices implement runtime
   behavior, certification, and supported-feature promotion.

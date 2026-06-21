# Roadmap

The roadmap is governed by RFC-0002 and must stay aligned to implementation evidence.

Current state:

1. repository foundation is scaffolded,
2. architecture decisions are recorded,
3. RFC-0002 defines the enterprise opportunity intelligence implementation program,
4. RFC-0002 Slice 00 records the implementation-start source map and first
   journey decisions,
5. RFC-0002 Slice 03 implements pure domain vocabulary and lifecycle primitives,
6. RFC-0002 Slice 04 partially implements source-authority and data-mesh
   baseline contracts plus a repo-native data-mesh contract gate while keeping
   mesh certification planned,
7. RFC-0002 Slice 05 partially implements the high-cash deterministic domain
   policy plus the first Core source-port and conservative HTTP adapter
   foundation,
8. RFC-0002 Slice 06 partially implements internal persistence, replay,
   idempotency, lifecycle audit history, and recovery primitives,
9. RFC-0002 Slice 07 partially implements internal deterministic scoring,
   priority buckets, stable queue projection, snooze, suppression,
   deduplication, expiry, unsupported-evidence, and unscored-candidate
   exclusions,
10. RFC-0002 Slice 08 partially implements internal advisor review and feedback
   governance with fail-closed scope checks, review actions, safe audit events,
   source provenance, and queue projection interaction,
11. RFC-0002 Slice 09 partially implements internal AI governance with redacted
    evidence envelopes, verifier/fallback controls, safe audit events, and no
    AI downstream authority,
12. RFC-0002 Slice 10 partially implements the certified internal
    `POST /api/v1/idea-signals/high-cash/evaluate` API foundation over
    caller-supplied, source-owned Core evidence,
13. RFC-0002 Slice 12 partially implements internal conversion governance for
    review-gated conversion intents, target source-authority mapping, downstream
    outcome recording, and no-authority conversion boundaries,
14. business features remain Planned.

First implementation program:

1. apply reusable scaffold improvements in `lotus-platform` when implementation
   exposes repeatable gaps,
2. normalize structure before adding product scope,
3. add source contracts and data-mesh baseline,
4. extend the current Core source-port foundation into live high-cash /
   idle-liquidity source proof after Core exposes explicit source-reported cash
   weight,
5. add database-backed persistence, source ingestion orchestration, persisted
   queue state, review, and feedback,
6. extend certified APIs into Gateway/Workbench product surfaces after live
   source adapters and durable state exist,
7. persist conversion intents/outcomes and add downstream adapter contracts only
   after source ownership and idempotency guarantees are explicit,
8. realize Advise, Manage, Report, Render, Archive, and AI integration only where source-backed,
9. prove canonical demo scenarios and publish implementation-backed documentation.

Unsupported until proved:

1. autonomous advice,
2. suitability or compliance approval,
3. order execution,
4. client communication,
5. client-ready report publication,
6. generic chatbot behavior,
7. AI-generated unsupported recommendations.

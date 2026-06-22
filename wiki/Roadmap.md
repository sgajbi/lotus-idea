# Roadmap

The roadmap is governed by RFC-0002 and must stay aligned to implementation evidence.

Current state:

1. repository foundation is scaffolded,
2. architecture decisions are recorded,
3. RFC-0002 defines the enterprise opportunity intelligence implementation program,
4. RFC-0002 Slice 00 records the implementation-start source map and first
   journey decisions,
5. RFC-0002 Slice 01 verifies the reusable platform scaffold baseline:
   generated services now start with the standard repo-local wiki page set,
   validation/CI guidance, branch-hygiene posture, and supported-feature
   anti-claim wording, with coverage in the `lotus-platform` scaffold contract
   tests,
6. RFC-0002 Slice 03 implements pure domain vocabulary and lifecycle primitives,
7. RFC-0002 Slice 04 partially implements source-authority and data-mesh
   baseline contracts plus a repo-native data-mesh contract gate while keeping
   mesh certification planned,
8. RFC-0002 Slice 05 partially implements the high-cash deterministic domain
   policy plus the first Core source-port and conservative HTTP adapter
   foundation,
9. RFC-0002 Slice 06 partially implements internal persistence, replay,
   idempotency, lifecycle audit history, recovery primitives, and high-cash
   evaluate-and-persist orchestration,
10. RFC-0002 Slice 07 partially implements internal deterministic scoring,
   priority buckets, stable queue projection, snooze, suppression,
   deduplication, expiry, unsupported-evidence, unscored-candidate exclusions,
   and repository-snapshot queue orchestration,
11. RFC-0002 Slice 08 partially implements internal advisor review and feedback
   governance plus workflow persistence with fail-closed scope checks, review
   actions, safe audit events, source provenance, idempotency replay/conflict,
   and queue projection interaction,
12. RFC-0002 Slice 09 partially implements internal AI governance with redacted
    evidence envelopes, verifier/fallback controls, safe audit events,
    certified internal AI explanation evaluator API, and no AI downstream
    authority,
13. RFC-0002 Slice 10 partially implements the certified internal
    `POST /api/v1/idea-signals/high-cash/evaluate` and
    `POST /api/v1/idea-signals/high-cash/evaluate-and-persist` API foundations
    over caller-supplied, source-owned Core evidence, plus certified internal
    lifecycle, AI explanation, advisor queue, review, feedback, conversion,
    report evidence-pack, and data-mesh-readiness endpoint foundations,
14. RFC-0002 Slice 12 partially implements internal conversion governance for
    review-gated conversion intents, target source-authority mapping, downstream
    outcome recording, and no-authority conversion boundaries,
15. RFC-0002 Slice 13 partially implements internal report evidence-pack
    request governance for reviewed report conversion intents, source summaries,
    retention refs, Report/Render/Archive authority refs, idempotency, audit,
    and a certified internal API foundation,
16. RFC-0002 Slice 18 partially synchronizes API certification documentation
    with the machine-readable endpoint certification ledger so current
    foundation endpoints, capabilities, and unsupported boundaries are visible
    to operators and future agents,
17. business features remain Planned.

First implementation program:

1. apply reusable scaffold improvements in `lotus-platform` when implementation
   exposes repeatable gaps,
2. normalize structure before adding product scope,
3. add source contracts and data-mesh baseline,
4. extend the current Core source-port foundation into live high-cash /
   idle-liquidity source proof after Core exposes explicit source-reported cash
   weight,
5. extend the current PostgreSQL source-ingestion replay/conflict recovery
   proof into scheduled source-ingestion workers, deploy migration evidence,
   live Core source-adapter proof, and durable operational procedures,
6. extend certified APIs into Gateway/Workbench product surfaces after live
   source adapters and durable state exist,
7. persist conversion intents/outcomes and add downstream adapter contracts only
   after source ownership and idempotency guarantees are explicit,
8. realize Advise, Manage, Report, Render, Archive, and AI integration only
   where source-backed; current report evidence-pack support is request truth
   only and not downstream materialization,
9. prove canonical demo scenarios and publish implementation-backed documentation.

Unsupported until proved:

1. autonomous advice,
2. suitability or compliance approval,
3. order execution,
4. client communication,
5. client-ready report publication,
6. generic chatbot behavior,
7. AI-generated unsupported recommendations.

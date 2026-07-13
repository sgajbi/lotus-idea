# Roadmap

The roadmap is governed by RFC-0002 and must stay aligned to implementation evidence.

Current summary: RFC-0002 is partly implemented through internal foundations,
operator diagnostics, and bounded publication proof. Business features remain
planned until source authority, data-mesh certification, Gateway/Workbench
proof, downstream proof, supported-feature evidence, and mainline CI all agree.

## Roadmap Decision Map

| Decision | Current answer | Evidence path |
| --- | --- | --- |
| Can a business feature be promoted? | No; all business features remain planned. | `supported-features/`, RFC-0002 slice evidence, CI gates |
| Can Gateway/Workbench be treated as complete? | No; bounded read-only queue/detail proof exists, but full product-surface proof remains gated. | [Supported Features](Supported-Features), [API Surface](API-Surface) |
| Can downstream realization be marketed as execution? | No; submission posture and route/materialization proof do not grant suitability, execution, reporting, or archive authority. | [Integrations](Integrations), [Operations Runbook](Operations-Runbook) |
| Can data mesh be claimed as certified? | No; contracts and runtime diagnostics are preparatory evidence only. | [Security and Governance](Security-and-Governance), mesh proof gates |

## Current State

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
7. RFC-0002 Slice 04 implements the pre-certification source-authority and
   data-mesh baseline contracts plus a repo-native data-mesh contract gate
   while keeping mesh certification planned,
8. RFC-0002 Slice 05 is implemented on `main` through PRs `#347` and `#348`,
   green main commit `ad88690`, and synchronized RFC/wiki evidence:
   deterministic signal policies, conservative source adapters, and governed
   source-backed APIs span Core, Risk, Performance, Advise, and Manage without
   duplicating source-owned calculations,
9. RFC-0002 Slice 06 partially implements internal persistence, replay,
   transport idempotency, review/feedback/conversion-outcome resource identity,
   source-version lifecycle and legacy-history quarantine, lifecycle audit
   history, recovery primitives, and high-cash
   evaluate-and-persist orchestration plus the manifest-backed run-once
   source-ingestion worker CLI and check-only gate. It now also includes
   durable claim-before-call downstream submission, uncertain-outcome
   quarantine/reconciliation, operator audit controls, and real PostgreSQL
   concurrency/restart proof. Protected exact-image migration automation now
   adds durable release-bound history, locking, pending-only apply, drift
   rejection, explicit legacy adoption, bounded rollback, source-safe evidence,
   and anti-bypass governance; protected execution and rollout health proof
   remain open. Repository implementation merged through PR `#373`; exact-main
   Main Releasability `29261043056`, CodeQL `29261035371`, and synchronized
   wiki publication prove the release and documentation posture without
   claiming protected environment execution. [Issue #375](https://github.com/sgajbi/lotus-idea/issues/375)
   tracks the missing protected environments, deployment runner, database
   secret, governed target, and same-digest rollout evidence,
10. RFC-0002 Slice 07 partially implements internal deterministic scoring,
   priority buckets, stable queue projection, snooze, suppression,
   deduplication, expiry, unsupported-evidence, unscored-candidate exclusions,
   candidate-created-at as-of visibility, opaque snapshot-bound continuation,
   and durable PostgreSQL repository-side queue projection with before/after
   conflict detection,
11. RFC-0002 Slice 08 partially implements internal advisor review and feedback
   governance plus workflow persistence with fail-closed scope checks, review
    actions, safe audit events, source provenance, idempotency replay/conflict,
    business-resource replay/conflict across transport keys, atomic persistence,
    and queue projection interaction,
12. RFC-0002 Slice 09 partially implements internal AI governance with redacted
    evidence envelopes, verifier/fallback controls, safe audit events,
    certified internal AI explanation evaluator API, a not-certified AI
    explanation readiness diagnostic, and no AI downstream authority,
13. RFC-0002 Slice 10 partially implements the certified internal
    `POST /api/v1/idea-signals/high-cash/evaluate` and
    `POST /api/v1/idea-signals/high-cash/evaluate-and-persist` API foundations
    over caller-supplied, source-owned Core evidence, plus certified internal
    lifecycle, AI explanation, advisor queue, review, feedback, conversion,
    report evidence-pack, AI-explanation-readiness, and data-mesh-readiness
    endpoint foundations. Advisor queue OpenAPI now publishes required
    continuation identity and stable snapshot conflict semantics, with
    bounded read-only Gateway publication for advisor queue and candidate
    detail,
14. RFC-0002 Slice 12 partially implements internal conversion governance for
    review-gated conversion intents, target source-authority mapping, downstream
    outcome history/current posture with append-only correction, no-authority
    conversion boundaries, and a certified
    downstream realization readiness contract-plan diagnostic,
15. RFC-0002 Slice 13 partially implements internal report evidence-pack
    request governance for reviewed report conversion intents, source summaries,
    retention refs, Report/Render/Archive authority refs, idempotency, audit,
    a certified internal API foundation, and operator-visible
    Report/Render/Archive blocker reporting, plus bounded `lotus-report`
    materialization proof consumption when sibling evidence is present,
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
5. extend the current manifest-backed run-once source-ingestion worker,
   check-only gate, and PostgreSQL replay/conflict recovery proof into
   certified long-running scheduled source-ingestion runtime, protected
   migration execution and rollout-health evidence, live Core source-adapter
   proof, and durable operational procedures,
6. extend the first bounded read-only Gateway publication into Workbench
   product surfaces only after certified live source-worker adapters, durable
   state, and supportability proof exist,
7. persist conversion intents/outcomes and harden downstream adapter contracts
   only after source ownership and idempotency guarantees are explicit,
8. realize Advise, Manage, Report, Render, Archive, and AI integration only
   where source-backed; current report evidence-pack support includes internal
   request truth and bounded materialization proof consumption only, not client
   publication or supported product promotion,
9. prove canonical demo scenarios and publish implementation-backed documentation.

Unsupported until proved:

1. autonomous advice,
2. suitability or compliance approval,
3. order execution,
4. client communication,
5. client-ready report publication,
6. generic chatbot behavior,
7. AI-generated unsupported recommendations.

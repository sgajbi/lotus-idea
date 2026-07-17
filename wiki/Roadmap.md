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
| Can downstream realization be marketed as execution? | No; submission posture and digest-bound Advise/Manage/Report source contracts do not prove route serving or acceptance and do not grant suitability, execution, reporting, render, or archive authority. | [Integrations](Integrations), [Operations Runbook](Operations-Runbook) |
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
9. RFC-0002 Slice 06 implements repository-owned persistence, replay,
   transport idempotency, review/feedback/conversion-outcome resource identity,
   source-version lifecycle and legacy-history quarantine, lifecycle audit
   history, recovery primitives, and high-cash
   evaluate-and-persist orchestration plus the manifest-backed run-once
   source-ingestion worker CLI and check-only gate. It now also includes
   durable claim-before-call downstream submission, uncertain-outcome
   quarantine/reconciliation, operator audit controls, and real PostgreSQL
   concurrency/restart proof. Downstream submission OpenAPI now distinguishes
   terminal `200` accepted/rejected and replay modes from the separately named
   `202 reconciliation_required` posture without transferring downstream
   authority. Application-backed advisor-queue `itemsAvailable` and
   `noItemsAvailable` OpenAPI modes now publish through the existing bounded
   queue projection; this is not a review-product or supported-feature promotion.
   Protected exact-image migration automation now
   adds durable release-bound history, locking, pending-only apply, drift
   rejection, explicit legacy adoption, bounded rollback, source-safe evidence,
   and anti-bypass governance. Managed infrastructure, external authority,
   protected execution, and rollout health certification remain tracked under
   issues `#340`, `#343`-`#345`, `#375`, and `#378`-`#380`. Repository
   implementation merged through PR `#373`; exact-main
   Main Releasability `29261043056`, CodeQL `29261035371`, and synchronized
   wiki publication prove the release and documentation posture without
   claiming protected environment execution. [Issue #375](https://github.com/sgajbi/lotus-idea/issues/375)
   tracks the governed database, encrypted connectivity, runtime secret, and
   same-digest rollout evidence; protected environments are configured and PR
   `#377` moves execution to the standard GitHub-hosted runner,
10. RFC-0002 Slice 07 partially implements internal deterministic scoring,
   priority buckets, stable queue projection, snooze, suppression,
   deduplication, expiry, unsupported-evidence, unscored-candidate exclusions,
   candidate-created-at as-of visibility, opaque snapshot-bound continuation,
   and durable PostgreSQL repository-side queue projection with before/after
   conflict detection,
11. RFC-0002 Slice 08 is implemented on `main` through PR `#387`. It provides
    audience-bound advisor, portfolio-manager,
    and compliance queues; aggregate-only operator exception posture;
    trusted-context review and feedback authorization; safe audit events;
    source provenance; transport and resource-identity replay/conflict; atomic
    persistence; and process-local/PostgreSQL queue parity. It remains an
    internal, unpromoted foundation until later product-proof gates pass.
    Exact-main SHA `d5be2390` passed Main Releasability run `29297787754` and
    CodeQL run `29297783153`,
12. RFC-0002 Slice 09 completes the Lotus Idea repository implementation for
    internal AI governance with redacted evidence envelopes,
    verifier/fallback controls, safe audit events, certified internal AI
    explanation APIs, durable source-safe lineage, a not-certified readiness
    diagnostic, and no AI downstream authority. Live provider, production
    model-risk, Gateway/Workbench, and promotion evidence remain blocked,
13. RFC-0002 Slice 10 partially implements the certified internal
    `POST /api/v1/idea-signals/high-cash/evaluate` and
    `POST /api/v1/idea-signals/high-cash/evaluate-and-persist` API foundations
    over caller-supplied, source-owned Core evidence, plus the source-backed
    high-cash route. Named OpenAPI contracts now cover all executable
    evaluation, retry, duplicate-candidate, and no-write modes. Low-income
    caller and Core-backed routes likewise publish complete candidate-created,
    blocked, suppressed, and not-eligible mode matrices with exact executable
    contract parity. Bond-maturity caller and Core-backed routes now meet the
    same contract while retaining Core maturity-data authority. Allocation-drift
    caller and Manage-backed routes also meet the same contract while retaining
    Manage, Performance, and Risk source authority. Underperformance caller and
    Performance-backed routes now meet the same contract while retaining
    Performance returns and benchmark authority. Concentration-risk caller and
    Risk-backed routes now meet the same contract while retaining Risk
    concentration and methodology authority. High-volatility caller and
    Risk-backed routes now meet the same contract while retaining Risk
    volatility, VaR, tracking-error, and methodology authority. Drawdown-review
    caller and Risk-backed routes now meet the same contract while retaining
    Risk drawdown calculation, period-selection, and methodology authority.
    Mandate-restriction caller and Advise-backed routes now meet the same
    contract while retaining Core/Manage/Advise source ownership and Advise
    policy-evaluation authority. Missing-risk-profile caller and Advise-backed
    routes now meet the same contract while retaining Advise client
    risk-profile workflow, diagnostic, risk-capacity, suitability, and policy
    authority. Missing-benchmark caller and Core-backed routes now meet the
    same contract while retaining Core benchmark-assignment and methodology
    authority. Missing-suitability caller and Advise-backed routes now meet
    the same contract while retaining Advise suitability, policy, proposal,
    sign-off, and client-publication authority. The slice also
    includes certified internal lifecycle, AI explanation, advisor queue,
    review, feedback, conversion, report evidence-pack,
    AI-explanation-readiness, and data-mesh-readiness endpoint foundations.
    Advisor queue OpenAPI now publishes required
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

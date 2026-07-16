# RFC Index

This page is the reader-friendly RFC entrypoint. The canonical detailed ledger
is [`docs/rfcs/README.md`](../docs/rfcs/README.md).

Current summary: RFC-0002 foundations are actively implemented, but final
supported-feature promotion remains blocked until implementation-backed proof,
documentation, CI, and mainline validation agree.

## RFC Reader Map

| Need | Use |
| --- | --- |
| Current slice status | `docs/rfcs/README.md` |
| Product boundary | [Overview](Overview), [Architecture](Architecture) |
| Support posture | [Supported Features](Supported-Features) |
| CI and closure proof | [Validation and CI](Validation-and-CI) |

Primary RFCs:

1. `docs/rfcs/RFC-0001-repository-foundation-and-service-boundary.md`
2. `docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-enterprise-opportunity-intelligence-operating-layer.md`

RFC-0002 is the end-to-end implementation program. It includes slice files for
source mapping, platform scaffolding review, cleanup, domain model, source
contracts, signal generation, persistence, scoring, review, AI explanation,
certified APIs, Gateway, Workbench, Advise/Manage conversion,
Report/Render/Archive materialization, data products, operations, demo
readiness, live proof, documentation, hardening, and closure.

## Detailed RFC-0002 Implementation Ledger

Current RFC-0002 implementation-start baseline:

1. Slice 00 is recorded as complete for source mapping and product-gap
   allocation.
2. Slice 01 is implemented as scaffold review evidence. The previously
   identified generated-wiki gap is already addressed in `lotus-platform`
   commit `549d290` and covered by the platform scaffold contract tests; no
   `lotus-core` change or new platform PR is required for this slice.
3. Slice 02 is partially implemented for cleanup and structure normalization:
   runtime composition providers for repository state, source ingestion, outbox
   publication, and downstream realization now live under `src/app/runtime/`,
   API routes access those helpers only through `app.api.runtime_dependencies`,
   the blocking architecture-boundary gate protects both directions of the
   API/runtime boundary, and route metadata dictionaries use the shared
   `app.api.route_metadata.RouteMetadata` contract enforced by
   `make api-route-metadata-gate`. API DTOs use shared
   `app.api.base_model.CamelModel` alias handling enforced by
   `make api-camel-model-boundary-gate`, and shared signal-family DTOs use
   `app.api.signal_models` enforced by `make api-signal-model-boundary-gate`.
   Workflow and operator `ProblemDetails`
   OpenAPI examples are now enforced by
   `make openapi-problem-details-example-gate`. Mutating workflow routes use
   shared `app.api.idempotency` validation enforced by `make
   api-idempotency-boundary-gate`. Public domain API ownership is protected by
   `make private-import-boundary-gate`, which blocks private
   `app.domain.*` helper imports. The same gate now protects the shared
   implementation-proof capability update module, so proof-readiness code uses
   public `apply_blocker_proof` and `build_capability_readiness` functions
   instead of importing private proof helpers. It also protects
   `app.infrastructure.postgres_codecs`, so the PostgreSQL repository consumes
   public row, JSON, datetime, and domain serialization APIs instead of private
   codec helpers. It remains a cleanup slice only and does not promote a
   business feature.
4. Slice 03 implements the pure domain model and lifecycle foundation with
   public domain API boundary enforcement, without API, persistence, or
   supported-feature promotion.
5. Slice 04 implements the pre-certification source-authority and data-mesh
   baseline, including proposed producer contracts, consumer dependencies,
   blocked static trust telemetry, SLO/access/evidence policy files, and a repo-native
   `data-mesh-contract-gate` that pins the bounded Lotus Risk
   `ConcentrationRiskReport:v1` dependency and protects producer provenance,
   freshness, quality, lineage, access, deprecation semantics, and consumer
   dependency freshness/provenance metadata. Platform mesh certification
   remains planned.
6. Slice 05 is implemented on `main`. PRs `#347` and `#348` merged the
   implementation and release-identity fix; main commit `ad88690` passed
   releasability and CodeQL. It began
   with high-cash / idle-liquidity and now provides deterministic,
   policy-versioned evaluation plus governed caller-supplied and source-backed
   APIs across Core, Risk, Performance, Advise, and Manage. Missing, stale,
   unauthorized, temporally inconsistent, or unsupported evidence fails closed;
   official source calculations remain with their owning services. Later-slice
   Gateway/Workbench, mesh certification, and supported-feature promotion stay
   blocked.
7. Slice 06 implements the repository-owned candidate persistence records,
   evidence replay posture, certified evidence replay API foundation,
   idempotency conflict handling, idempotent lifecycle transition recording,
   lifecycle audit history, snapshot recovery, and a central repository
   workflow port boundary. It also adds the first versioned schema/rollback
   contract, PostgreSQL migration execution CLI, tested PostgreSQL repository
   adapter foundation, opt-in API runtime wiring, and a real PostgreSQL
   high-cash persistence/replay plus first internal
   source-ingestion replay/conflict recovery, manifest-backed run-once
   ingestion worker CLI with check-only gate, and
   review/feedback/conversion/report workflow proof. Review, feedback, and
   conversion-outcome resource IDs are governed independently of HTTP idempotency keys, with
   equivalent new-key replay, changed-content conflict, and atomic PostgreSQL
   collision handling before candidate/audit/outbox writes. Conversion outcome
   streams also enforce contiguous source versions, append-only corrections,
   valid current posture, and legacy contradiction quarantine. A certified internal
   outbox-delivery-readiness diagnostic and run-once operator action now
   report aggregate backlog/status posture, durable repository posture, broker
   configuration posture, certification blockers, and source-safe operator run
   identity/idempotency posture while proving bounded configured-publisher
   orchestration without exposing raw idempotency keys, event identifiers,
   calling downstream services, or promoting a supported feature.
   Downstream handoffs now also claim durably before an external call, preserve
   uncertain outcomes without automatic retry, expose source-safe operator
   reconciliation by opaque support reference, and carry real PostgreSQL
   concurrency/restart proof. Protected exact-image migration automation adds
   release-bound history, advisory locking, pending-only apply, drift rejection,
   explicit legacy adoption, bounded rollback, append-only events, and
   source-safe evidence validation without adding a service or database.
   Protected execution and rollout-health proof remain open. This does not claim
   downstream execution or supported-feature readiness.
8. Slice 07 is implemented on `main` through PR `#383`. Candidate score
   policies and queue ranking policy are
   separately versioned; unknown policies fail closed across process-local and
   PostgreSQL providers; priority, suppression, deduplication, expiry, scope,
   readiness, and snapshot behavior are deterministic and contract-gated.
   Gateway read-only publication exists, but Workbench product proof,
   data-product certification, and supported-feature promotion remain later,
   independently gated work. Exact-main SHA `4f4e0985` passed Main
   Releasability run `29291215703`.
9. Slice 08 is implemented on `main` through PR `#387`. Advisor,
   portfolio-manager, and compliance
   queues are audience-bound; the operator surface exposes aggregate support
   exceptions without business authority; review and feedback mutations derive
   authorization from trusted caller entitlements plus persisted candidate
   scope. Lifecycle, audit, resource-identity, replay/conflict, and PostgreSQL
   foundations remain internal and unpromoted. Gateway/Workbench product proof,
   mesh certification, and supported-feature promotion remain later-slice
   gates. Exact-main SHA `d5be2390` passed Main Releasability run
   `29297787754` and CodeQL run `29297783153`.
10. Slice 09 partially implements internal AI governance with redacted evidence
   envelopes, forbidden metadata rejection, deterministic fallback,
   unsupported-claim and forbidden-action verifier outcomes, evidence-grounded
   server-rendered claim narrative with source-safe freshness/quality bindings,
   safe audit events, no AI downstream authority, governed
   `lotus-ai:idea-explanation:v1` workflow
   identity rejection for arbitrary caller-supplied packs, and a certified
   internal AI explanation evaluator API plus a not-certified AI explanation
   readiness diagnostic. Submitted provider narrative is not advisor-visible or
   persisted, and blocked output exposes no grounded claims.
   PR `#394` additionally proves actual review-gated deterministic-stub
   execution through `idea_explanation.pack@v1` with a bounded receipt on
   exact-main SHA `b892d5d6`; Main Releasability `29303651841` and CodeQL
   `29303648849` passed. Live-provider execution, production model-risk
   approval, Gateway, Workbench, and supported-feature promotion remain absent.
   PR `#390` merged this bounded capability to exact-main SHA `67a6e005`;
   Main Releasability `29300549721` and CodeQL `29300546423` passed. Slice 09
   remains partial for its separate live-provider/production and
   product-realization gates.
   PRs `#397`/`#398` additionally require and validate a digest-bound exact-main
   CI execution receipt before durable AI lineage-store certification can
   clear. Exact-main SHA `5cf7592b` passed Main Releasability `29307190040` and
   CodeQL `29307186825`; source files and workflow text remain non-certifying.
   The same rule now protects durable repository readiness: a
   persistence-specific exact-main PostgreSQL receipt is required before the
   aggregate durable-storage and repository-side pagination blockers clear.
   Production deployment and product support remain blocked.
   Outbox downstream consumer declarations now follow the same taxonomy: the
   v2 consumer artifact is `source_contract` evidence, records authority
   boundaries, and clears no runtime blocker. Observed consumer execution
   remains required for `downstream_consumer_runtime_proof_missing`.
   Gateway/Workbench discovery declarations follow the same rule after #408:
   PR #409 merged and exact-main validation passed at `5a12dea7`; source
   evidence cannot prove publication, serving, consumption, or discovery.
   Issue #411 now applies the taxonomy to AI model-risk operations. Dashboard,
   alert-rule, runbook, and validator source may be valid while dashboard
   provisioning/query execution and alert-rule loading/evaluation/delivery
   remain blocked. The capability-owned source-contract proof clears no
   aggregate blocker and promotes no supported feature.
11. Slice 10 partially implements certified internal API foundations for
   high-cash evaluation, high-cash evaluate-and-persist, candidate lifecycle
   transitions, source-safe candidate detail, candidate evidence replay,
   AI explanation evaluation with `invalid_ai_workflow_pack` request guarding,
   advisor queues with truthful as-of/snapshot paging and stable 400/409
   ProblemDetails, review actions, feedback,
   conversion intent, conversion outcome, report evidence-pack request,
   AI-explanation-readiness diagnostics, data-mesh-readiness diagnostics,
   runtime trust telemetry preview/snapshot diagnostics,
   source-ingestion-readiness diagnostics, and source-ingestion run-once
   operator action. A certified internal
   downstream-realization-readiness diagnostic now reports Advise, Manage,
   Report, Render, and Archive blockers without calling downstream services.
   The certified internal
   implementation-proof-readiness diagnostic now aggregates RFC-0002 blocker
   posture across source ingestion, advisor queue, AI explanation, data mesh,
   runtime trust telemetry preview/snapshot/proof evidence, outbox delivery, Workbench, downstream
   realization, and supported-feature promotion.
   `make implementation-proof-readiness-check` generates and consumes the
   scheduled source-ingestion worker source contract while intentionally
   preserving the deployment blocker, durable repository
   proof artifact, runtime telemetry test-execution artifact, Gateway/Workbench
   source-contract proof artifact, Gateway/Workbench discovery contract proof
   artifact, report-intake route proof artifact, mesh policy source-contract artifact, platform catalog source
   contract artifact, AI lineage store proof artifact, Core portfolio-state
   live-proof artifact, and AI model-risk
   operations contract refs before producing the same source-safe posture as
   repo-native automation evidence.
   Bounded live source-ingestion proof, read-only Gateway publication, and
   Workbench queue/detail rendering exist for advisor review; full source-worker
   certification, full Workbench proof, data-product certification, and
   supported-feature promotion remain planned.
   Slice 05 also includes direct Performance/Risk mandate-health source-product
   ref adapters, governed `evaluate-from-source` routes across the supported
   signal families, and clean-tree canonical Risk/Performance proof for the
   governed portfolio. Full source-worker operational certification and
   mainline proof remain open.
12. Slice 12 partially implements internal conversion governance for
    review-gated conversion intent and source-versioned downstream outcome
    history/current posture, with
    target-to-source-authority mapping for `lotus-advise`, `lotus-manage`, and
    `lotus-report`, plus certified internal API foundations and an internal
    downstream realization readiness diagnostic with planned Advise, Manage,
    and Report contract-readiness records backed by
    `contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`,
    source-safe downstream application orchestration and adapter foundations,
    certified internal downstream submission APIs for Advise/Manage conversion
    intents and Report evidence-pack requests, `make
    conversion-outcome-contract-gate`, and `make
    downstream-realization-contract-gate`. It does not prove downstream
    route existence, create downstream records, execute downstream materialization,
    or promote a supported feature.
13. Slice 18 is partially implemented for API certification and
    implementation-proof documentation truth. `docs/operations/api-certification.md`
    and `docs/operations/implementation-proof-readiness.md` now mirror the
    certified foundation endpoint inventory, current capabilities,
    implementation proof blockers, and unsupported boundaries.
14. Slice 15 partially implements evidence replay, AI explanation readiness,
    source-ingestion readiness/run-once, outbox delivery readiness/run-once, downstream
    realization readiness, and aggregate implementation-proof readiness
    supportability: operators can replay candidate evidence posture over
    current source refs, inspect model-risk blockers without invoking
    `lotus-ai`, inspect run-once worker configuration and certification
    blockers without calling Core, execute a bounded aggregate-only
    source-ingestion run-once action when durable storage and runtime
    configuration are present, inspect aggregate outbox delivery blockers
    without publishing broker events, inspect downstream realization blockers
    without calling Advise, Manage, Report, Render, or Archive, and inspect
    aggregate proof blockers without promoting live ingestion, Workbench,
    downstream, data-mesh, or supported-feature support.
15. The first opportunity journey is high cash / idle liquidity for
    `PB_SG_GLOBAL_BAL_001`.
16. RFC-0002 Slice 16 now has a governed opportunity archetype/scenario
    contract and `make opportunity-archetype-contract-gate`; it is taxonomy and
    anti-overclaim evidence only, not live demo proof or supported-feature
    promotion.
17. The first review audience is advisor only.
18. The first downstream conversion posture is report-only evidence after
    advisor review.
19. Business features remain unsupported until later slices implement runtime
    behavior, certification, and supported-feature promotion.

# RFC-0002 Slice 08: Review Queues, Feedback, And Human Governance

Status: Implemented on `main`; supported-feature promotion remains pending

## Outcome

Implement human review, feedback, and governance over opportunity queues.

## Current Implementation Evidence

Implemented in this slice:

1. `src/app/domain/review_governance.py` adds a framework-free review
   governance domain layer for the first-wave advisor audience approved by
   Slice 0.
2. Advisor review actions now cover approve-for-conversion, reject, no-action,
   suppress, snooze, escalate-to-PM, and escalate-to-compliance outcomes.
3. Review actor scope fails closed across tenant, book, portfolio, and client
   membership before a review decision or feedback event is accepted.
4. Advisor-only first-wave action policy is explicit. PM, compliance, and
   operator roles are modeled as vocabulary for escalation and later queue
   slices, but they are not yet permitted to execute first-wave review actions.
5. Governed review decisions and feedback events carry candidate identity,
   evidence packet identity, evidence content hash, source signal provenance,
   actor subject, actor role, typed reason codes, and safe audit events.
6. Review decisions never grant downstream suitability, compliance, mandate,
   execution, or client-communication authority.
7. Queue projections react to review outcomes through lifecycle, posture,
   suppression, and snooze state without introducing persisted queue state.
8. `tests/unit/test_review_governance.py` covers advisor approval, entitlement
   failure, non-advisor denial, blocked-evidence approval denial, rejection,
   no-action, suppression, snooze, escalation, feedback provenance, safe audit
   attributes, and command validation.
9. `src/app/application/review_workflow.py` applies review actions and feedback
   after loading the candidate through the shared bounded candidate lookup
   helper, prechecks idempotency before reapplying domain transitions, and
   persists accepted governance results through the repository contract. For
   projection-capable repositories this avoids whole-repository snapshot
   hydration during the pre-mutation candidate lookup; the write itself remains
   on the existing repository mutation path.
10. `src/app/domain/persistence.py` records review decisions, feedback events,
    safe audit events, lifecycle history, idempotency replay, conflict, and
    not-found posture for internal review workflow mutations.
11. `tests/unit/test_review_workflow_application.py` covers approval
    persistence, replay before domain reapplication, idempotency conflict,
    feedback source provenance, safe audit persistence, missing-candidate
    behavior, and projection-only candidate lookup without `snapshot()`
    hydration for review actions and feedback.
12. `src/app/api/review_workflow.py` exposes certified internal API
    foundations for review actions and feedback:
    `POST /api/v1/idea-candidates/{candidateId}/review-actions` and
    `POST /api/v1/idea-candidates/{candidateId}/feedback`.
13. The review and feedback APIs require `Idempotency-Key`, mutating
    capabilities, caller role, upstream-authorized tenant/book/portfolio/client
    scope, and return product-safe 403, 404, and 409 errors.
14. The APIs share the active repository provider. They return
    `durableStorageBacked=false` in default process-local runtime and
    `durableStorageBacked=true` only when `LOTUS_IDEA_DATABASE_URL` activates
    the PostgreSQL provider; they always return `supportedFeaturePromoted=false`.
15. `tests/integration/test_review_workflow_api.py` covers suppression
    persistence, idempotency replay/conflict, generated-state approval conflict,
    feedback persistence, missing candidate, capability denial, and scope
    denial.
16. `tests/integration/test_postgres_runtime_integration.py` now proves the
    first PostgreSQL-backed internal review workflow path by projecting the
    advisor queue from reloaded database state, transitioning lifecycle to
    review-ready, recording approval, replaying the review decision from
    database idempotency state, recording feedback, and validating review and
    feedback tables.
17. GitHub issue `#330` adds one versioned lifecycle/review-posture policy for
    all review actions. Approve, reject, and no-action remain limited to
    ready/reviewed candidates; suppression, snooze, and escalation fail closed
    for approved or terminal candidates. Accepted audit and rejected operation
    events carry candidate state, requested action, and policy version without
    client or portfolio data.
18. Review queue and PostgreSQL readiness projections classify contradictory
    legacy snapshots as `invalid_state` and never count or decode them as normal
    advisor work items.
19. GitHub issue `#327` defines `reviewId` and `feedbackId` as durable resource
    identities independent of the HTTP `Idempotency-Key`. Identity binds
    candidate, evidence, actor, action/outcome, reasons, time, and applicable
    feedback lineage.
20. Equivalent content under a new transport key replays before domain
    lifecycle mutation and creates no second decision, feedback, audit, or
    outbox event. Changed identity returns product-safe
    `review_identity_conflict`.
21. PostgreSQL claims resource identity before candidate mutation and retries a
    collision once from fresh state. The same behavior is covered in the
    process-local adapter, API, fake adapter suite, real PostgreSQL two-connection
    integration proof, OpenAPI named examples, and
    `make review-identity-contract-gate`.
22. GitHub issue `#385` makes queue audience explicit across domain policy,
    application commands, repository ports, PostgreSQL predicates, readiness
    aggregation, snapshot identity, and API contracts. Advisor,
    portfolio-manager, and compliance routes select only their responsible
    review posture and share one deterministic ranking implementation.
23. `GET /api/v1/review-queues/operator/exceptions` exposes aggregate,
    entitlement-scoped support exceptions by audience. It omits candidate
    identifiers, does not rank business work, and grants no review, compliance,
    suitability, mandate, or execution authority.
24. GitHub issue `#386` removes `accessScope` and `authorizedScope` from review
    and feedback bodies. Trusted caller headers define actor entitlements; the
    application loads persisted candidate scope before domain authorization.
    Tests cover every scope dimension, multi-value membership, legacy-field
    rejection, product-safe denial, and OpenAPI schema truth.
25. Review queue API modules are grouped under `src/app/api/review_queue/`, and
    operator exception orchestration lives in
    `src/app/application/review_queue_exceptions.py`. These are design
    modularity improvements inside the existing deployable service, not a new
    queue process or service.

Validation evidence from the implementation slice:

1. PR `#387` merged by rebase to exact-main SHA
   `d5be2390065171a36fc8fbc19f40cc4aa3cded87`. Main Releasability run
   `29297787754` and CodeQL run `29297783153` passed for that SHA.
2. `make check` passed lint, canonical formatting, 773-file MyPy analysis,
   architecture and API gates, and 3,637 unit tests.
3. `make ci` passed 451 integration tests with 28 environment-dependent
   PostgreSQL tests skipped, four end-to-end tests, all three coverage shards,
   the 99.02% combined coverage gate, and dependency audit against the resolved
   runtime and CI tooling lock files. The coverage threshold was not reduced.
4. `LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED=1 make postgres-integration-gate`
   passed all 17 tests against an isolated PostgreSQL 18 database, including
   review-queue projection, restart/replay, downstream submission, and data
   lifecycle paths. The database was removed after validation.
5. Focused audience, workflow, malformed-scope, snapshot, caller-context,
   OpenAPI, endpoint-certification, observability, maintainability,
   documentation, issue-closure, and supported-feature gates passed.
6. Repo-authored wiki source was published after merge at wiki commit
   `3ad971d`; the post-publication synchronization check reported zero drift.
   The implementation branch was deleted locally and remotely.

## Later-Slice Promotion Dependencies

Slice 08 implementation does not promote a supported review product. The
following evidence remains owned by later RFC-0002 slices:

1. Gateway/Workbench integration proof,
2. feedback data-product declaration promotion and mesh certification,
3. trust telemetry and production operational support,
4. supported-feature promotion after mainline and live-product proof.

## Required Work

1. Add advisor, PM, compliance, and operator queue projections as approved by
   Slice 0.
2. Implement review decisions, feedback, rejection, suppression, snooze,
   escalation, and no-action outcomes.
3. Enforce role, book, portfolio, client, and tenant entitlements.
4. Capture audit reason and actor context for all review actions.

## Acceptance Gate

1. Review actions cannot approve downstream suitability, compliance, mandate, or
   execution state.
2. Entitlement tests fail closed.
3. Queue projections update after decisions.
4. Feedback events are source-provenanced.

The durable feedback portion has first PostgreSQL-backed internal workflow
proof only. It remains unsupported until Gateway/Workbench proof,
platform-scoped runtime entitlements, mesh certification, and supported-feature
evidence store and expose review decisions and feedback events as a supported
product surface.

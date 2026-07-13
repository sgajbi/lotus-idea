# RFC-0002 Slice 06: Persistence, Replay, Idempotency, And Audit

Status: Implemented - repository-owned persistence, replay, idempotency, audit, lifecycle control, recovery, deployment-migration, and proof foundations are complete; external authority, managed infrastructure, live production certification, product publication, and supported-feature promotion remain fail-closed and tracked separately

## Outcome

Persist candidate and evidence state with replayable, hash-backed, audit-ready
behavior.

## Required Work

1. Add persistence for candidate, evidence packet, lifecycle history, review
   state, feedback, suppression, conversion state, and audit events.
2. Add idempotency for signal ingestion, candidate creation, review decisions,
   AI explanation requests, and conversion intents.
3. Add replay or rebuild behavior with evidence hashes and source refs.
4. Add migration and rollback posture where persistence is introduced.

## Acceptance Gate

1. Duplicate requests do not create duplicate candidates.
2. Replay returns matching evidence hash or a clear stale-source posture.
3. Every mutating action writes an audit event.
4. Persistence tests cover conflict, replay, expiry, and recovery cases.

## Governed Data Lifecycle Closure

The local Slice 06 lifecycle boundary is implemented without introducing a
new runtime service. Design modularity is provided by domain evaluation,
application orchestration, a repository port, and PostgreSQL adapters; the
evidence does not justify a separately scalable process boundary.

Implemented evidence:

1. `contracts/operations/lotus-idea-data-lifecycle.v1.json` classifies every
   migrated table, applies versioned field-classification and residency
   profiles, maps only the governed Report retention reference, and preserves
   bank, Report, Archive, and AI authority boundaries.
2. `POST /api/v1/data-lifecycle/candidates/{candidateId}/actions` requires
   trusted role/capability context, exact tenant entitlement, idempotency,
   governed authority, durable sanitized correlation/trace, dry-run preview,
   and dual authorization where required.
3. PostgreSQL controls make hold, release, erasure, purge, operation audit,
   redaction, and tombstone updates atomic. Erased/purged candidates are hidden
   from detail and downstream lookup paths; new delivery claims share the
   lifecycle lock and cannot race into an erased aggregate.
4. Real PostgreSQL tests prove restart replay/conflict, legal-hold precedence,
   pseudonymized audit, expiry-gated purge, and safe erasure-versus-delivery
   serialization.
5. Runtime trust telemetry reports bounded lifecycle state, expired-retention,
   and missing-control counts. Erased/purged tombstones do not inflate active
   candidate or workflow product counts.
6. `docs/runbooks/data-lifecycle-operations.md` defines operator workflow,
   first response, evidence commands, research basis, and explicit
   non-certification posture.

Remaining lifecycle certification blockers are bank approval for durations
and start events, live bank authority producer/key-discovery proof,
Report/Archive/AI conformance, production authorized purge proof with privacy review, mainline CI, and
supported feature promotion. Lotus Idea enforces approved decisions; it does not own
legal, privacy, archive, report-rendering, or AI-provider policy decisions.

### Signed Lifecycle Authority Consumer

Production-like profiles now require a signed `authorityDecision` before a
lifecycle command can reach the repository. The consumer verifies an Ed25519
signature against a configured no-redirect well-known key source and binds the
approved decision to issuer, audience, tenant, candidate, action,
legal-or-privacy authority domain, authority reference, change reference, and
effective/expiry window. Unknown, duplicate, revoked, wrong-curve, stale, or
substituted claims fail before mutation.

Migration `013_lifecycle_authority_receipt` stores decision ID, replay nonce,
key ID, rotation epoch, and verification time for applied operations. A dry-run
preview verifies but does not consume the decision. The first applied command
claims decision and nonce under an advisory lock and partial unique indexes;
same-key retries replay, while new-key reuse returns
`lifecycle_authority_replay_conflict` without another lifecycle mutation.
Real PostgreSQL 18 tests prove apply, reconnect replay, single-use conflict,
and durable receipt identity. This is consumer-side enforcement, not evidence
that a bank authority producer is live or that a legal/privacy decision was
substantively correct.

The consumer is explicitly bound to the platform-owned interoperability family
through `contracts/integrations/lifecycle-authority-consumer.v1.json`. The
declaration pins the merged decision schema, key-discovery schema, and
producer-certification contract by platform path and SHA-256 digest; maps them
to Idea's request mapper, application verifier, key-source port/adapter, and
receipt migration; and keeps production authority and supported-feature
posture false. The existing `data-lifecycle-contract-gate` validates that
declaration and, when the sibling platform repository is present, recomputes
all three authoritative digests. This prevents consumer/platform drift without
copying bank decision authority or introducing another runtime process.

### Scheduled Expiry Review Foundation

The scheduled review path preserves the external decision boundary. A bounded
application use case reads at most 100 expired, non-purged controls through a
PostgreSQL projection and classifies each as ready for an authorized purge or
blocked by legal hold, invalid lifecycle state, or active delivery work. The
review does not mutate lifecycle state and does not manufacture an authority
or approver identity.

The weekly/manual `scheduled-data-lifecycle-review.yml` workflow migrates an
empty PostgreSQL 18 database, seeds synthetic ready, held, and active-delivery
states through production repository/application paths, emits aggregate-only
evidence, runs a fail-closed proof gate, attests the artifact, and retains it
for 90 days. The artifact is explicitly `reviewOnly=true`,
`productionAuthorityVerified=false`, `not_certified`, and non-promotional.
Mainline run `29180046362` passed against exact Idea SHA `f496c442`: PostgreSQL
18 migration, synthetic seeding, bounded review, source-safe proof validation,
provenance attestation, and artifact upload all succeeded. This proves the
merged review-only foundation; production purge remains blocked on signed
privacy authority, dual review, and production cross-service conformance.

### Lotus AI Provider-Retention Consumer

Attested AI explanation evaluation may now carry a separately signed
`lotus-ai:ProviderRetentionConfirmation:v1` envelope. Idea verifies the shared
Ed25519 trust bundle and binds run, tenant, provider, provider mode, model, and
model version to the already verified execution receipt and candidate access
scope before one atomic lineage write. Migration
`014_ai_provider_retention_receipt` persists bounded confirmation, provider
reference, and replay-nonce identities with uniqueness fencing; raw prompts,
outputs, client identifiers, and provider secrets remain excluded.

`PROVIDER_FAILURE` is accepted only as `BLOCKED` posture with
`deletionConfirmed=false`. The receipt reports Lotus AI/provider operations
posture only: it cannot authorize Idea hold, erasure, or purge, cannot replace
the bank lifecycle-authority decision, and cannot stand in for Report or
Archive conformance. The consumer contract is enforced by
`make ai-provider-retention-contract-gate`. Provider-native confirmation,
managed-key/production-SQL proof, bank privacy/outsourcing/model-risk approval,
and production-authorized purge remain blocked.

The bounded cross-repository contract foundations are now merged and
mainline-proven: Lotus AI `51a8e8e` / run `29179866214`, Lotus Report
`59385c5` / run `29179900038`, Lotus Archive `e5e9253` / run `29179849407`,
and Lotus Idea `f496c442` / run `29179489433`. Repo-authored wiki publication
is synchronized in all four repositories. These proofs establish producer and
consumer contract delivery; they do not certify provider-native deletion,
managed production keys or stores, bank lifecycle authority, legal/privacy
approval, or production purge execution.

### Signed Archive Posture Consumer

Linked Idea report evidence now requires a separate signed
`lotus-archive:IdeaEvidenceLifecycleDecision:v1` posture. The request DTO maps
the producer envelope, the application verifier validates canonical SHA-256 and
Ed25519 evidence against the strict Archive trust bundle, and the domain policy
reconciles that receipt with exact report evidence-pack IDs loaded by the
PostgreSQL adapter inside the lifecycle transaction.

The receipt binds tenant, candidate, Idea evidence-pack ID, Archive document,
retention policy, lifecycle action, five-minute maximum TTL, digest, and signing
key. Active Archive hold blocks release, erase, and purge. Applying a local hold
requires Archive `LEGAL_HOLD`; purging local Idea content requires Archive
`DISPOSAL_EXECUTED`, not eligibility alone. An unlinked candidate rejects an
Archive receipt rather than accepting unrelated authority.

Migration `015_archive_lifecycle_posture_receipt` persists only bounded receipt
lineage and fences applied decision IDs and payload digests across repository
restart. Blocked attempts remain auditable without consuming a receipt. The
contract is enforced by `make archive-lifecycle-posture-contract-gate`, and the
real PostgreSQL suite proves linked-pack loading, persistence, exact replay, and
cross-idempotency conflict. Archive posture remains independent of the signed
bank lifecycle decision and never grants Archive disposal authority to Idea.
Managed Archive durability, key rotation, trust distribution, bank approval,
and production-authorized purge evidence remain certification blockers.

## Implementation Evidence

Implemented first-wave internal scope:

1. `src/app/domain/persistence_models.py` defines immutable persistence
   records, lifecycle history, decisions, replay vocabulary, and repository
   snapshots. `src/app/domain/persistence.py` composes the in-memory behavioral
   reference repository from bounded lookup, AI-lineage, outbox, review,
   downstream-submission, and root candidate/lifecycle/conversion/report
   behavior. Review and feedback persistence, identity fencing, idempotency,
   audit, lifecycle history, and outbox emission now have one owner in
   `src/app/domain/persistence_review_workflow.py`. The API and optional worker
   still use one Idea repository port and one PostgreSQL database boundary.
   `src/app/domain/outbox/events.py` defines the typed outbox envelope, status
   vocabulary, deterministic event identity, hashed idempotency fingerprint,
   and forbidden payload-key guard for source/client-sensitive fields.
2. Candidate persistence now evaluates idempotency keys and payload hashes
   before writing. Matching keys and matching payloads replay the existing
   candidate record; matching keys with different payloads return conflict; a
   duplicate candidate identity under a different key returns
   `duplicate_candidate` instead of creating another record.
3. Evidence replay compares current source refs with the persisted source-ref
   hash and returns explicit matched, stale-source, hash-mismatch, expired, and
   not-found posture.
4. Candidate persistence and lifecycle transitions write safe bounded
   `AuditEvent` records. Audit events reject sensitive attribute keys and now
   validate event identity, actor, outcome, and timezone-aware event time.
5. Repository snapshots allow internal recovery of candidate records,
   idempotency records, and idempotency-to-candidate mappings for replay tests.
6. `src/app/application/high_cash_signal.py` now adds internal high-cash
   evaluate-and-persist orchestration over the Slice 06 repository contract.
   Created high-cash candidates are persisted with deterministic idempotency
   payloads, matching requests replay, changed payloads conflict, and blocked,
   suppressed, or not-eligible evaluations remain non-mutating.
7. The same orchestration shape exists for the Core source-port flow. Core
   cash-weight authority is now implemented in Core PR #431 and consumed by
   the `lotus-idea` adapter from `totals.source_reported_cash_weight`. Bounded
   live Core source-ingestion proof can now be captured and consumed by
   readiness, but this still does not promote live source support until
   source-worker certification, mesh, Workbench, and supported-feature proof are
   captured and merged.
8. `src/app/application/source_ingestion.py` now adds an internal
   high-cash source-ingestion orchestration wrapper over the Core source port
   and repository port. It generates source-ingestion idempotency keys, maps
   repository and evaluator results into explicit accepted, replayed, conflict,
   duplicate-candidate, blocked, suppressed, and skipped-not-eligible decisions,
   and keeps blocked, suppressed, and below-threshold evaluations non-mutating.
   Core-backed idempotency payloads now include generated candidate and
   source-signal identity, so same-key source changes conflict instead of being
   treated as an equivalent replay. It also exposes a bounded run-once batch
   worker foundation with maximum item validation, per-item replay/conflict
   posture, batch decision counts, and correlation/trace propagation through
   the Core source port. This is not a daemon, deploy-pipeline worker, live Core
   certification, or supported ingestion product.
9. `src/app/application/source_ingestion_worker.py` and
   `scripts/run_source_ingestion_worker.py` now provide a versioned
   manifest-backed run-once worker entrypoint. `--check-only` validates the
   manifest and returns a product-safe summary without Core calls, repository
   writes, portfolio ids, or raw idempotency keys. Run mode requires explicit
   Core query and query-control-plane URLs, or compatibility
   `LOTUS_CORE_BASE_URL`, and emits decision counts, candidate ids when
   candidates are created, and idempotency-key presence only, without source
   payloads, portfolio ids in result items, raw idempotency keys, or
   supported-feature promotion.
10. `make source-ingestion-worker-check` now validates the example manifest and
    source-safe check-only output contract in the lint path. It blocks raw
    portfolio identifiers, source routes, source payloads, raw idempotency
    keys, and candidate identifiers from check-only output.
11. `scripts/ci_contract_gate.py` blocks future removal or downgrade of the
    source-ingestion worker contract gate from local quality enforcement.
12. `src/app/application/source_ingestion_scheduled_worker.py`,
    `scripts/run_scheduled_source_ingestion_worker.py`,
    `scripts/generate_scheduled_source_ingestion_worker_proof.py`, and the
    `lotus-idea-source-ingestion-worker` Compose service now provide a bounded
    scheduled worker deploy-contract foundation over the existing run-once
    worker. `--check-only` validates schedule and manifest posture without
    Core calls or repository writes, run mode fails closed without explicit
    Core runtime configuration, and generated proof can clear only the
    scheduled-worker deploy-proof blocker.
13. `make source-ingestion-scheduled-worker-check` and
    `scripts/ci_contract_gate.py` block future removal or downgrade of the
    scheduled worker proof gate from local quality enforcement.
14. `POST /api/v1/idea-signals/high-cash/evaluate-and-persist` now exposes the
   caller-supplied high-cash evaluate-and-persist path as a certified internal
   API foundation with `Idempotency-Key`, `idea.candidate.persist`, product-safe
   conflict errors, and repository-derived `durableStorageBacked` posture.
15. `src/app/application/candidate_lifecycle.py` and
   `src/app/api/candidate_lifecycle.py` now expose certified internal candidate
   lifecycle transition orchestration over the same repository contract.
   `POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions` requires
   `idea.candidate.lifecycle.transition` plus `Idempotency-Key`, applies the
   canonical caller-settable domain lifecycle transition graph, writes
   lifecycle history and audit evidence, returns accepted/replayed/not-found/
   conflict/invalid-state posture, rejects `accepted` and `executed` as generic
   lifecycle transition inputs before repository mutation or outbox emission,
   and keeps `supportedFeaturePromoted=false`.
16. `src/app/application/candidate_evidence_replay.py` and
    `src/app/api/candidate_evidence_replay.py` now expose evidence replay
    posture as a certified internal operator API at
    `POST /api/v1/idea-candidates/{candidateId}/evidence-replay`. The route
    requires `idea.candidate.evidence.replay` plus operator role, compares
    caller-supplied current source refs with persisted evidence hashes, returns
    matched, stale-source, hash-mismatch, expired, or not-found posture, emits
    bounded operation events, and does not call Core, export raw source routes,
    grant downstream authority, or promote a supported feature.
17. `src/app/ports/idea_repository.py` now centralizes the repository workflow
    protocols used by application orchestration. Candidate persistence,
    candidate snapshots, evidence replay, lifecycle mutation, review and
    feedback mutation, conversion mutation, report evidence-pack requests, and
    AI explanation reads depend on the ports layer instead of declaring local
    per-use-case repository protocols. `tests/unit/test_repository_port_boundary.py`
    prevents future application modules from reintroducing scattered repository
    protocol declarations outside the governed runtime provider.
18. Accepted internal repository mutations now append pending outbox records for
    candidate persistence, lifecycle transitions, review decisions, feedback,
    conversion intents, conversion outcomes, and report evidence-pack requests.
    Replayed, conflict, not-found, blocked, suppressed, and not-eligible paths
    remain non-publishing and do not create duplicate outbox work. This is an
    internal outbox foundation only; no external broker, Gateway event, platform
    mesh event, or downstream publication is claimed.
19. `src/app/domain/outbox/events.py`, `src/app/domain/persistence.py`,
    `src/app/application/outbox/delivery.py`,
    `src/app/ports/outbox/publisher.py`, and
    `src/app/ports/idea_repository.py` now add the first internal outbox
    delivery semantics. Delivery-ready reads include pending events, retryable
    failed events below the configured retry limit only after their durable
    `next_attempt_at_utc` is due, and expired leases. Delivery runs claim a
    bounded batch with lease owner, attempt id, and expiry before broker
    publication, publish only claimed events, and complete or fail delivery only
    when the same owner/attempt still owns the lease. Status updates can mark an
    event published, failed for retry with first/last failure timing and a
    deterministic capped next-attempt schedule, or dead-lettered when the retry
    limit is reached. Publisher exceptions are mapped to bounded
    `publisher_unavailable` failure reason codes, failure reasons reject
    source/client-sensitive marker names, and run summaries expose aggregate
    counts only. `src/app/infrastructure/outbox/publisher.py` adds a
    source-safe HTTP broker-publisher adapter foundation with bounded envelopes,
    trace headers, and product-safe failure reasons. `PostgresIdeaRepository`
    persists claim/lease metadata, failure timing, and next-attempt eligibility
    through the existing `idea_outbox_event` table. Retry claims clear the due
    timestamp while preserving first/last failure timing until publication or
    dead-letter closure.
    This is not certified live broker runtime,
    downstream delivery, Gateway event publication, data-product certification,
    or supported-feature promotion.
    `contracts/outbox-events/lotus-idea-outbox-events.v1.json` and
    `make outbox-event-contract-gate` now define and enforce the repo-owned
    outbox event envelope, event families, payload safety policy, and remaining
    certification blockers. `src/app/application/outbox/broker_proof.py`,
    `scripts/outbox/generate_broker_proof.py`, and
    `make outbox-broker-proof-contract-gate` now add a source-safe bounded
    outbox broker proof artifact for aggregate implementation-readiness
    evidence. It clears only the aggregate broker configuration/runtime-proof
    blockers and preserves downstream consumer runtime, platform mesh event
    publication, Gateway/Workbench, and supported-feature blockers.
    `contracts/outbox-events/lotus-idea-outbox-consumers.v1.json` and
    `make outbox-consumer-contract-gate` now declare Gateway, Advise, Manage,
    and Report as governed downstream consumers with source-authority
    boundaries. The contract clears the missing-contract posture only; all
    consumers remain `contract_declared_not_runtime_certified`.
    `src/app/application/outbox/consumer_runtime_proof.py`,
    `scripts/outbox/generate_consumer_runtime_proof.py`, and
    `make outbox-consumer-runtime-proof-contract-gate` now add a source-safe
    bounded downstream consumer runtime proof artifact. It clears only
    `downstream_consumer_runtime_proof_missing` and preserves platform mesh
    event publication, Gateway/Workbench, downstream delivery, and
    supported-feature blockers.
    `src/app/application/outbox/platform_mesh_event_publication_proof.py`,
    `scripts/outbox/generate_platform_mesh_event_publication_proof.py`, and
    `make outbox-platform-mesh-event-publication-proof-contract-gate` now add a
    source-safe bounded outbox platform mesh event publication proof artifact.
    It clears only `platform_mesh_event_publication_proof_missing` after the
    repo-owned event/consumer contracts and sibling platform source-manifest
    and catalog evidence validate. It preserves external broker publication,
    downstream delivery, Gateway/Workbench, client-ready publication, and
    supported-feature blockers.
20. `src/app/application/outbox/readiness.py` and
    `GET /api/v1/outbox-delivery/readiness` now expose the outbox delivery
    foundation through a certified internal operator diagnostic. The endpoint
    requires the `operator` role and `idea.outbox-delivery.readiness.read`,
    returns aggregate status counts, due delivery-ready backlog,
    retry-deferred failed-row counts, leased and expired lease counts, durable
    repository posture, broker configuration posture, publisher-adapter presence,
    source-of-truth paths, and certification blockers, and emits bounded
    `outbox_delivery_readiness_read` operation events. It does not expose event identifiers, aggregate
    identifiers, raw idempotency keys, broker payloads, downstream contracts,
    Gateway/Workbench support, or supported-feature promotion.
    PostgreSQL-backed readiness now uses a repository-side aggregate projection
    over `idea_outbox_event` for status counts, expired leases, due
    delivery-ready counts, and retry-deferred failed-row counts instead of
    hydrating unrelated repository snapshot tables. The adapter also reads only
    pending, due failed, and expired leased events through a bounded
    `idea_outbox_event` query for worker polling semantics.
21. `migrations/001_idea_repository_foundation.sql` and
    `migrations/001_idea_repository_foundation.rollback.sql` now define the
    first versioned database schema and rollback contract for future candidate,
    idempotency, lifecycle, audit, outbox, review, feedback, conversion, and
    report evidence-pack repository state. `scripts/migration_contract_gate.py`
    validates required tables, indexes, JSONB payload columns, UTC timestamp
    columns, source relationships, and rollback statements so future agents
    cannot add persistence-shaped work without governed reversibility evidence.
22. `src/app/infrastructure/migrations.py` and `scripts/run_migrations.py` now
    provide a PostgreSQL migration execution path. `make migration-execution-gate`
    dry-runs apply and rollback plans in CI without needing a database, while
    `make migrate` and `make migrate-rollback` execute the same plans when
    `LOTUS_IDEA_DATABASE_URL` points to a PostgreSQL database. The Docker image
    now includes `migrations/` so runtime migration commands have the same SQL
    contract as local development.
23. `src/app/infrastructure/postgres_repository.py` now implements the first
    PostgreSQL repository adapter behind the governed port surface. The adapter
    hydrates repository snapshots from the schema, delegates domain decisions to
    the same in-memory repository contract, flushes typed table rows and JSONB
    snapshots transactionally, persists pending outbox records across reload,
    exposes repository-side outbox readiness and delivery-ready projections,
    and rolls back when a database flush fails.
    `tests/unit/test_postgres_repository.py` proves candidate persistence,
    idempotency replay, lifecycle history, audit events, review decisions,
    feedback, conversion intent/outcome, report evidence-pack requests, pending
    outbox hydration, bounded review/feedback/conversion replay-conflict
    prechecks, and rollback behavior with a fake Postgres cursor.
    `tests/unit/outbox/test_postgres_readiness.py` proves the outbox readiness
    projection avoids whole-repository snapshot hydration.
24. `src/app/infrastructure/postgres_codecs.py` now isolates PostgreSQL JSON
    serialization/deserialization helpers from the repository adapter so future
    persistence growth does not erode source-file maintainability gates.
25. `src/app/runtime/settings.py` now owns runtime profile semantics, and
    `src/app/runtime/repository_state.py` selects `PostgresIdeaRepository` when
    `LOTUS_IDEA_DATABASE_URL` is configured. `local` and `test` profiles may use
    the process-local `InMemoryIdeaRepository`; `demo`, `staging`, and
    `production` degrade readiness and fail write-capable routes closed before
    in-memory mutation when durable storage is absent. psycopg connections use
    mapping rows so the adapter receives the row shape it enforces. Runtime
    composition stays outside the API layer and app root.
26. Repository-backed API routes now derive `durableStorageBacked` responses and
    `durable_storage_backed` operation-event labels from the active repository
    instead of hardcoding storage posture. Default local/test runtime remains
    process-local and continues to report `durableStorageBacked=false`; a
    configured PostgreSQL runtime reports `durableStorageBacked=true` for the
    repository-backed foundation routes. Production-like profiles without
    durable storage return `durable_repository_not_configured` before mutation.
27. `tests/integration/test_postgres_runtime_integration.py` now runs the
    first real PostgreSQL runtime proof. It applies the governed schema,
    persists a high-cash candidate through
    `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`, reloads the
    repository provider to force a new database connection, proves idempotency
    replay from PostgreSQL state, projects the advisor queue from the reloaded
    repository, transitions the candidate to review-ready state, records review
    approval, advisor feedback, report conversion intent, conversion outcome,
    and report evidence-pack request state, validates the backing workflow
    tables, proves internal Core-backed source-ingestion replay and same-key
    changed-source conflict recovery through the PostgreSQL repository adapter,
    rolls the schema back, reapplies it, and proves the recovered API
    persistence contract is usable. `make postgres-integration-gate` is the
    repo-native command, and PR Merge Gate / Main Releasability run it against
    `postgres:18-alpine` with
    `LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED=1`.
28. `src/app/application/durable_repository_proof.py`,
    `scripts/generate_durable_repository_proof.py`, and
    `make durable-repository-proof-contract-gate` now define and validate a
    source-safe durable repository proof artifact for aggregate RFC proof
    readiness. The artifact cites migration contracts, the PostgreSQL adapter,
    and the GitHub PostgreSQL runtime proof lane. It clears only aggregate
    stale durable-repository proof blockers; it does not configure runtime
    storage, certify production storage, replace `make postgres-integration-gate`,
    or promote support.
29. `contracts/operations/lotus-idea-deployment-migrations.v1.json` and the
    layered deployment-migration domain, application, port, and PostgreSQL
    adapter now govern production-like schema changes without adding a service
    or database. The executor acquires a transaction-scoped advisory lock,
    validates PostgreSQL 18, binds the 15-migration bundle to an immutable
    digest, applies only a strict pending prefix, rejects name/content drift,
    commits schema and history atomically, and records release lineage in
    durable history plus database-enforced append-only events. Existing legacy
    schemas require an explicit structural-fingerprint adoption operation;
    rollback is explicit, bounded, audited, and never represented as restore.
    `.github/workflows/deployment-migration-evidence.yml` accepts only an exact
    signed and GitHub-attested mainline image digest in a protected environment,
    injects the database URL only at runtime, validates source-safe evidence
    with the same image, attests it, and retains it for 90 days. The contract
    gate blocks mutable-image, secret-input, direct-workflow bypass, Docker
    closure, bundle, lock, and evidence drift. Real disposable PostgreSQL tests
    prove fresh apply, exact replay, adoption, checksum drift, failed-plan
    rollback, rollback/reapply, concurrent execution, CLI evidence, and
    append-only event enforcement. Protected environment execution and rollout
    health evidence remain absent, so production certification and supported
    feature posture remain false. The `lotus-idea-staging` and
    `lotus-idea-production` environments now exist with protected-branch rules;
    production also requires reviewer approval. Issue `#375` tracks the
    remaining runtime database secret, governed target, encrypted connectivity,
    execution attestation, and same-digest rollout-health evidence.

External certification backlog (not repository-implementation blockers):

1. protected-environment execution of the exact-image migration workflow plus
   attested rollout-health evidence; issue `#375` records the absent governed
   PostgreSQL target, environment-scoped runtime secret, approved encrypted
   connectivity, and live evidence. The protected environments exist and the
   workflow uses GitHub's ephemeral `ubuntu-latest` runner,
2. physical/WAL provider recovery and live-service recovery certification,
   tracked by issues `#343` and `#345`,
3. bank-owned lifecycle authority, authorized purge, and provider-native AI
   confirmation/approval, tracked by issues `#344` and `#340`,
4. Report/Archive production authority and data-product certification, tracked
   by issues `#378` and `#380`,
5. certified external broker publication and downstream delivery beyond the
   aggregate outbox readiness diagnostic, HTTP
   publisher adapter foundation, repo-owned outbox event and consumer
   contracts, bounded outbox broker proof artifact, bounded downstream
   consumer runtime proof artifact, and bounded outbox platform mesh event
   publication proof artifact; issue `#379` tracks live authoritative outcomes,
6. Gateway/Workbench product proof and supported-feature promotion, tracked by
   issue `#380` and the owning later RFC slices.

This backlog does not transfer source authority into Lotus Idea and does not
permit a support claim. It records work that requires managed infrastructure,
another Lotus authority, a production approval, or cross-application live
evidence. Repository implementation closure therefore advances the RFC while
readiness and supported-feature evaluators continue to fail closed.

## Migration And Rollback Posture

The slice has an explicit schema and rollback contract, a local/disposable
migration planner, a governed deployment executor, opt-in runtime repository
wiring, and real PostgreSQL API persistence/replay plus rollback/reapply proof.
The deployment executor is the only production-like path: it runs from the
exact published image, uses durable history and an advisory transaction lock,
applies only pending migrations, rejects immutable-bundle or applied-history
drift, requires explicit fingerprinted legacy adoption, and emits source-safe
release evidence. `make migrate` and `make migrate-rollback` remain
local/disposable fixture tools and are not deployment authority. CI dry-runs
those plans, runs real PostgreSQL behavior tests, and statically prevents other
workflows from bypassing the protected exact-image path. Database credentials
are runtime-only secret input and are excluded from CLI arguments and evidence.
This is intentionally ahead of production storage promotion so schema,
rollback, indexing, relationship posture, execution command shape, adapter
behavior, runtime selection, and durable replay become CI-visible before any
supported database-backed product claim is made.
The current proof now also exercises the first internal review, queue,
conversion, report evidence-pack workflow, pending outbox persistence, and
internal source-ingestion replay/conflict recovery path against PostgreSQL. The
durable repository proof artifact lets aggregate implementation-readiness
evidence cite that persistence proof without requiring the generator itself to
connect to PostgreSQL; runtime endpoints still report durable storage only from
the active repository provider. The
source-ingestion application layer now has a bounded run-once batch primitive,
a versioned manifest-backed run-once CLI and check-only gate, and a bounded
scheduled-worker deploy-contract proof over that run-once primitive. The outbox
foundation now includes internal retry and dead-letter status semantics through
the repository port, a source-safe HTTP publisher adapter foundation, a
certified aggregate readiness diagnostic, and a certified internal
`POST /api/v1/outbox-delivery/run-once` operator action. The operator action
requires the `operator` role plus `idea.outbox-delivery.run`, fails closed
without valid broker configuration, leaves records untouched when blocked, and
returns aggregate delivery counts without event identifiers, aggregate ids, raw
idempotency keys, source payloads, broker payloads, or downstream claims. This
does not certify external publication, Gateway/Workbench consumption, or
downstream delivery. The next durable persistence slices must still prove
certified long-running scheduled daemon behavior, execute the protected
migration workflow and retain rollout-health evidence, prove live Core
source-adapter behavior against that service,
certified external broker event-publication proof before any supported event
publication claim, and keep API responses truthful:
`durableStorageBacked=true` means the configured repository adapter is active,
not that the idea product is data-mesh certified or supported.

## Validation

Current slice validation:

1. `.venv\Scripts\python.exe -m pytest tests\unit\test_high_cash_application.py tests\unit\test_idea_persistence.py -q`
   passed with `19 passed` for the new orchestration and persistence replay
   coverage.
2. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion.py tests\unit\test_high_cash_application.py -q`
   passed with `24 passed` for the internal source-ingestion orchestration,
   generated idempotency key, replay, conflict, blocked, suppressed, and
   skipped-not-eligible coverage.
3. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion.py -q`
   passed with `11 passed` after adding bounded run-once batch worker coverage
   for duplicate replay, changed-source conflict, batch decision counts,
   timezone validation, maximum item enforcement, and correlation propagation.
4. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion_worker.py tests\unit\test_source_ingestion.py tests\unit\test_ci_enforcement_contract.py -q`
   passed with `30 passed` after adding manifest parsing, unknown-key
   rejection, product-safe summary, CLI check-only, and CI-contract coverage.
5. `make source-ingestion-worker-check` passed, validating
   `docs/examples/source-ingestion/high-cash-worker-manifest.example.json` and
   the source-safe check-only output contract without Core calls or repository
   writes.
6. `.venv\Scripts\python.exe scripts\ci_contract_gate.py` passed after adding
   the source-ingestion worker check target to the required local lint
   contract.
7. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion_scheduled_worker.py tests\unit\test_source_ingestion_scheduled_worker_contract_gate.py -q`
   passed after adding scheduled worker deploy-contract, proof artifact,
   missing Core runtime guard, and source-safe gate coverage.
8. `.venv\Scripts\python.exe scripts\source_ingestion_scheduled_worker_contract_gate.py`
   passed, proving the scheduled worker proof shape, entrypoints, and Compose
   service remain wired into local enforcement without exposing source-owned
   identifiers.
9. `.venv\Scripts\python.exe -m pytest tests\integration\test_postgres_runtime_integration.py -q`
   skips locally when `LOTUS_IDEA_POSTGRES_INTEGRATION_URL` is not configured;
   a required local disposable-PostgreSQL run passed with `11 passed` across
   the runtime and review-queue suites. The runtime suite includes internal
   source-ingestion replay/conflict recovery plus exact outbox dead-letter
   recovery lookup and durable audit replay after connection reload. GitHub
   PR/Main PostgreSQL lanes run the same contract on `postgres:18-alpine`.
10. `make check` passed with lint, format, CI contract, maintainability,
   monetary/no-sensitive guards, implementation-truth, data-mesh,
   migration, supported-feature, endpoint-certification, typecheck,
   architecture, OpenAPI, and `265` unit tests.
11. `make ci` passed with `60` integration tests, `4` local PostgreSQL skips,
   `2` e2e tests, `265` unit tests under coverage, coverage gate at `99.00%`,
   and dependency audit reporting no known vulnerabilities.
12. `.venv\Scripts\python.exe -m pytest tests\integration\test_candidate_evidence_replay_api.py tests\integration\test_api_operation_events.py -q`
    passed with `9 passed` after adding the certified evidence replay API,
    matched/stale/hash-mismatch/not-found/permission/validation coverage, and
    bounded operation-event proof.
13. `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py -q`
    passed with `17 passed` after adding source-safe pending outbox records,
    replay/conflict non-publication coverage, snapshot recovery proof, and
    forbidden payload-key coverage.
14. `.venv\Scripts\python.exe -m pytest tests\unit\test_postgres_repository.py tests\unit\test_migration_contract_gate.py -q`
    passed with `9 passed` after adding outbox schema enforcement and
    PostgreSQL outbox round-trip coverage.
15. `.venv\Scripts\python.exe scripts\migration_contract_gate.py`,
    `.venv\Scripts\python.exe scripts\run_migrations.py --direction apply --dry-run`,
    and `.venv\Scripts\python.exe scripts\run_migrations.py --direction rollback --dry-run`
    passed with the outbox table/index contract included in the baseline
    migration.
16. `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_outbox_delivery.py tests\unit\test_postgres_repository.py -q`
    passed with `29 passed` after adding internal outbox retry/dead-letter
    delivery state, bounded publisher exception handling, sensitive
    failure-reason rejection, and PostgreSQL outbox status persistence coverage.
17. `.venv\Scripts\python.exe -m ruff check src\app\domain\events.py src\app\domain\persistence.py src\app\application\outbox_delivery.py src\app\ports\idea_repository.py src\app\infrastructure\postgres_repository.py tests\unit\test_idea_persistence.py tests\unit\test_outbox_delivery.py tests\unit\test_postgres_repository.py`
    passed.
18. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini src\app\domain\events.py src\app\domain\persistence.py src\app\application\outbox_delivery.py src\app\ports\idea_repository.py src\app\infrastructure\postgres_repository.py`
    passed.
19. `.venv\Scripts\python.exe -m pytest tests\unit\test_outbox_delivery_readiness.py tests\integration\test_outbox_delivery_readiness_api.py -q`
    passed with `6 passed` after adding the certified aggregate outbox delivery
    readiness diagnostic, source-safe response proof, permission proof, and
    bounded operation-event proof.
20. `.venv\Scripts\python.exe scripts\openapi_quality_gate.py` and
    `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py` passed
    after adding the outbox delivery readiness OpenAPI route and endpoint
    certification ledger entry.
21. `.venv\Scripts\python.exe -m pytest tests\integration\test_outbox_delivery_readiness_api.py tests\unit\test_outbox_delivery.py -q`
    passed with `19 passed` after adding the certified aggregate-only outbox
    delivery run-once operator action, blocked-without-broker proof,
    configured-publisher proof, permission proof, UTC request validation, and
    bounded `outbox_delivery_run_once` operation-event proof.

Prior Slice 06 validation:

1. `.venv\Scripts\python.exe -m ruff check src\app\application\high_cash_signal.py tests\unit\test_high_cash_application.py`
   passed.
2. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini` passed.
3. Prior persistence validation also covered
   `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_idempotency_audit.py -q`
   with `11 passed`.
4. `make check` passed with lint, format, CI contract, monetary/no-sensitive
   guards, data-mesh contract gate, supported-feature gate,
   endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
   `257` unit tests.
5. `make ci` passed with `13` integration tests, `2` e2e tests, `174` unit
   tests under coverage, coverage gate at `99.37%`, and dependency audit
   reporting no known vulnerabilities.
6. Later endpoint foundation validation covered the certified
   evaluate-and-persist API with OpenAPI and endpoint-certification gates; at
   that point database-backed persistence remained planned.
7. `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_service_contract.py tests\integration\test_review_workflow_api.py -q`
   passed with `29 passed` after adding idempotent lifecycle transition
   repository and API coverage.
8. `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py` and
   `.venv\Scripts\python.exe scripts\openapi_quality_gate.py` passed after
   adding lifecycle route certification evidence.
9. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, supported-feature gate,
    endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
    `189` unit tests.
10. `make ci` passed with `39` integration tests, `2` e2e tests, `189` unit
    tests under coverage, coverage gate at `99.14%`, and dependency audit
    reporting no known vulnerabilities.
11. `make docker-build` passed for `backend-service:ci-test`.
12. `.venv\Scripts\python.exe -m ruff check src\app\application src\app\ports\idea_repository.py tests\unit\test_repository_port_boundary.py`
    passed after centralizing repository workflow protocols.
13. `.venv\Scripts\python.exe -m pytest tests\unit\test_repository_port_boundary.py tests\unit\test_high_cash_application.py tests\unit\test_review_queue_application.py tests\unit\test_review_workflow_application.py tests\unit\test_idea_persistence.py -q`
    passed with `43 passed`.
14. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini src\app\application src\app\ports\idea_repository.py`
    passed.
15. `.venv\Scripts\python.exe scripts\migration_contract_gate.py` passed after
    adding the first versioned schema/rollback contract.
16. `.venv\Scripts\python.exe -m pytest tests\unit\test_migration_contract_gate.py tests\unit\test_ci_enforcement_contract.py -q`
    passed with `14 passed`.
17. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, migration contract gate,
    supported-feature gate, endpoint-certification gate, typecheck,
    architecture boundary, OpenAPI, and `223` unit tests.
18. `make ci` passed with `59` integration tests, `2` e2e tests, `223` unit
    tests under coverage, coverage gate at `99.17%`, and dependency audit
    reporting no known vulnerabilities.
19. `.venv\Scripts\python.exe scripts\run_migrations.py --direction apply --dry-run`
    and `.venv\Scripts\python.exe scripts\run_migrations.py --direction rollback --dry-run`
    passed with `20` planned statements each.
20. `.venv\Scripts\python.exe -m pytest tests\unit\test_migration_execution.py tests\unit\test_migration_contract_gate.py tests\unit\test_ci_enforcement_contract.py -q`
    passed with `19 passed`.
21. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini src\app\infrastructure\migrations.py scripts\run_migrations.py`
    passed.
22. `.venv\Scripts\python.exe -m pip_audit -r requirements\shared-runtime.lock.txt -r requirements\ci-tooling.lock.txt`
    passed with no known vulnerabilities after adding
    `psycopg[binary]==3.3.4`.
23. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, migration contract gate,
    migration execution dry-run gate, supported-feature gate,
    endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
    `228` unit tests.
24. `make ci` passed with `59` integration tests, `2` e2e tests, `228` unit
    tests under coverage, coverage gate at `99.08%`, and dependency audit
    reporting no known vulnerabilities.
25. `make docker-build` passed for `backend-service:ci-test` after adding
    `migrations/` to the Docker image.
26. `make postgres-integration-gate` passed against a disposable
    `postgres:18-alpine` service on `localhost:55434` with `2 passed` after
    broadening the proof to cover high-cash persistence/replay, advisor queue
    projection, lifecycle transitions, review approval replay, feedback,
    report conversion intent replay, conversion outcome, report evidence-pack
    request replay, and backing workflow table counts.
27. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, migration contract gate,
    migration execution dry-run gate, supported-feature gate,
    endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
    `237` unit tests.
28. `make ci` passed with `60` integration tests, `2` local PostgreSQL skips,
    `2` e2e tests, `237` unit tests under coverage, coverage gate at `99.15%`,
    and dependency audit reporting no known vulnerabilities.
29. `make docker-build` passed for `backend-service:ci-test` after broadening
    the PostgreSQL runtime proof and synchronizing docs/wiki truth.
30. The deployment-migration unit, evidence, contract, and CI meta-contract
    suites pass with `121 passed`; the focused workflow/CI set separately
    passes with `112 passed`.
31. The deployment-migration adapter suite passes with `8 passed` against a
    disposable `postgres:18-alpine` service, including concurrent lock,
    drift, adoption, atomic failure, rollback/reapply, exact CLI evidence, and
    append-only event mutation cases.
32. Full `make ci` passes with `3,611` unit tests, `430` integration tests
    passed and `28` environment-dependent PostgreSQL skips, `4` e2e tests,
    `99.01%` coverage over `24,237` statements, and no known dependency
    vulnerabilities.
33. The SHA-tagged image passes runtime smoke, OCI-label and `/version`
    identity inspection, deployment migration CLI/evidence-gate closure,
    CycloneDX 1.6 SBOM generation with `27` components, and a blocking Trivy
    scan with zero HIGH/CRITICAL vulnerabilities or detected secrets.
34. Before PR `#373` merged, protected workflow execution, exact-main release
    proof, and wiki publication remained required. Local image proof did not
    substitute for a signed, attested, registry-digest-bound execution from a
    protected environment.
35. PR `#373` merged by rebase at exact main SHA `6ba9618a`; Main
    Releasability run `29261043056` and CodeQL run `29261035371` passed. The
    published release manifest binds digest
    `sha256:24cff4c4528f6d06eba2f87e2d151f104e6e2303785ccfcfef589511f0ad46b7` to the
    full-SHA tag, OCI labels, matching `/version`, zero-finding vulnerability
    and secret scan, CycloneDX SBOM, Cosign signature, provenance and SBOM
    attestations, Kubernetes digest reference, and same-image promotion
    policy. Wiki publication `bda1965` has zero source drift. Protected
    migration execution, approved production change, and rollout-health proof
    remain unclaimed certification blockers.

Repository implementation, PR validation, exact-main validation, wiki
publication, and branch cleanup are complete. Issue `#375` remains the
external configuration and execution blocker; closing repository issue `#372`
does not certify protected migration execution or rollout health.

## Issue 334 Durable Downstream Submission Recovery

Issue `#334` closes the external-call/local-commit ambiguity in the downstream
submission foundation. The application now creates an atomic durable claim
before invoking Advise, Manage, or Report. A request can reach the adapter only
when that claim is newly accepted.

### State And Failure Policy

| Condition | Durable posture | Automatic downstream retry |
| --- | --- | --- |
| Claim accepted, call not yet finalized | `in_flight` | No |
| Downstream returns a definitive 2xx acceptance | `accepted_by_downstream` after local finalization | No |
| Downstream returns a definitive 4xx rejection | `rejected_by_downstream` | No |
| Adapter is not configured | `not_configured` | No |
| Timeout, transport failure, 5xx, malformed response, lease loss, or local finalization failure | `reconciliation_required` or retained `in_flight` claim | No |
| Operator cannot establish source-owned truth | `quarantined` | No |

Acceptance is returned only after the terminal local state commits. If the
downstream service accepted work but the local finalization fails, the caller
receives `202 reconciliation_required` with an opaque support reference. A
same-key retry returns stored uncertain posture and never invokes the adapter
again. Lotus Idea still does not record an authoritative conversion outcome;
that fact must arrive through the owning downstream source-authority contract.

### Recovery Controls

The operator-only reconciliation API exposes a bounded source-safe projection:

1. `GET /api/v1/downstream-submissions/reconciliation` requires the `operator`
   role and `idea.downstream-reconciliation.read` capability.
2. `POST /api/v1/downstream-submissions/reconciliation/{supportReference}`
   requires the `operator` role and
   `idea.downstream-reconciliation.resolve` capability.
3. `Idempotency-Key` must equal `changeReference`; exact repeats replay, while
   reuse for another resolution, reason, or actor conflicts.
4. Accepted, rejected, and quarantined resolutions append actor, reason,
   change reference, time, previous posture, and current posture to durable
   audit history.
5. Responses omit resource IDs, idempotency keys, downstream payloads, client
   identifiers, and portfolio identifiers.

### Modularity And Operability

The state machine, in-memory provider, PostgreSQL provider, application use
case, DTO models, and API route are separate bounded modules behind repository
ports. They remain in the existing `lotus-idea` process. No workload,
failure-isolation, ownership, or operability evidence justifies a new runtime
service.

Migration `008_downstream_submission_state_machine` adds deterministic opaque
support references, attempt count, update time, lease identity/expiry,
append-only JSON audit history, posture constraints, and a reconciliation
index. PostgreSQL uses `ON CONFLICT DO NOTHING`, exact locked lookup, and
lease-fenced state update. The real PostgreSQL lane proves concurrent claim
serialization, migration apply/rollback, restart recovery, exact operator
replay, and preservation of an in-flight claim after connection failure.

`make downstream-realization-contract-gate` blocks reintroduction of
call-before-claim ordering, legacy post-call writes, weak PostgreSQL conflict
handling, ungoverned reconciliation, or fake-only runtime proof. Supported
features remain unchanged because this is recovery and local submission
posture, not downstream execution, materialization, Gateway/Workbench product
proof, or production support promotion.

Current branch validation:

1. `make lint` passed all repository contract and governance gates.
2. `make typecheck` passed across `563` source files.
3. `make test-unit` passed with `2764 passed`.
4. `make test-integration` passed with `389 passed` and `12` expected
   PostgreSQL skips when no integration DSN is configured.
5. `make test-e2e` passed with `4 passed`.
6. The required disposable PostgreSQL gate passed with `12 passed`, including
   concurrent submission recovery, restart, connection-failure recovery,
   outbox recovery, review-queue snapshot, and migration apply/rollback proof.
7. `make ci` passed all blocking lint, modularity, duplicate, architecture,
   contract, migration, OpenAPI, endpoint-certification, test, and dependency
   audit gates. Combined coverage passed at `99.01%` with no known dependency
   vulnerabilities.
8. Final stranded-truth reconciliation on 2026-07-11 found no remote branches
   unmerged from `origin/main`; no durable RFC, docs, wiki, context, contract,
   migration, OpenAPI, or supported-feature truth required recovery.

## Issue 337 Dead-Letter Recovery Hardening

Issue `#337` closes the direct-database recovery gap without making dead
letters automatically retryable. Source-safe inspection and explicit re-drive
now flow through API DTOs, an application use case, typed recovery policy, a
repository port, and in-memory/PostgreSQL adapters. Migration
`004_outbox_dead_letter_recovery` preserves actor, reason, change reference,
hashed idempotency identity, new lease identity, and the original failure
snapshot.

Concurrent and repeated actions are fenced. One failed re-drive remains
quarantined with no next attempt. This is design modularity inside the existing
`lotus-idea` runtime, not a new service boundary, and does not promote Slice 6
or a supported feature while external publication and consumer proof remain
open.

PostgreSQL recovery now resolves the opaque support reference with an exact
immutable SHA-256 expression index instead of scanning and locking the latest
1,000 outbox rows. The selector remains state-aware so a competing request sees
the leased event and returns a deterministic conflict. The shared delivery
claim also qualifies its `RETURNING` columns for PostgreSQL `UPDATE ... FROM`.
The required real-PostgreSQL lane proves delivery claim, dead-lettering,
connection reload, exact recovery claim, durable replay, and migration
rollback/reapply. `make outbox-recovery-contract-gate` rejects reintroduction
of a bounded selector.

## Issue 330 Candidate-State Persistence Hardening

Migration `005_candidate_state_policy` snapshots contradictory legacy candidate
rows into `idea_candidate_state_quarantine` and blocks contradictory new writes
with a `NOT VALID` policy constraint. PostgreSQL codecs reject invalid JSON
rehydration, while review queue and readiness SQL derive compatibility from the
domain matrix and classify historical contradictions as `invalid_state`.

The constraint remains `NOT VALID` until controlled legacy reconciliation is
complete. This avoids deployment-time data loss and does not turn quarantine
into a supported operator repair feature.

## Issue 327 Review Resource Identity Hardening

Review decisions and feedback events now preserve business-resource identity
independently of the HTTP `Idempotency-Key`. The domain binds resource ID,
candidate, evidence, actor, event, reasons, and event time. Application
prechecks resolve an equivalent new-key retry before lifecycle mutation, while
the repository repeats the decision at the persistence boundary.

PostgreSQL claims review or feedback identity before candidate, audit, and
outbox writes. A primary-key collision rolls back and retries once from fresh
state, producing deterministic replay or `review_identity_conflict` without a
duplicate side effect or raw database error. Existing primary keys provide the
schema authority, so no migration is required. The design remains an internal
bounded module and does not promote Slice 6 or a supported feature.

## Issue 328 Outbox Event Lineage Hardening

Every candidate-persistence, lifecycle, review, feedback, conversion-intent,
conversion-outcome, and report evidence-pack request event now carries
required correlation and trace metadata. Optional causation is accepted only
for a distinct parent event or workflow. `app.api.event_lineage` maps the API
request, application commands pass a framework-neutral context, repository
ports preserve it independently of idempotency payloads, and the publisher
uses trace rather than causation for transport tracing.

Migration `007_outbox_event_lineage` performs non-destructive legacy backfill
and enforces product-safe identifiers plus origin/causation compatibility.
Unit, API, publisher, and real PostgreSQL tests prove all seven event families,
new-trace replay preservation, repository reload hydration, migration
sanitization, and database rejection of invalid combinations. Producer and
consumer gates protect the contract. External broker, consumer, mesh,
Gateway/Workbench, and supported-feature certification remain blocked. This is
internal design modularity only; no runtime split is justified.

## Issue 329 Outbox Supportability Projection

The bounded readiness projection now returns the oldest delivery-ready time in
addition to status, due, deferred-retry, and expired-lease counts. PostgreSQL
computes the value with the existing aggregate query; the in-memory adapter
uses the same pending, due-retry, and expired-lease eligibility semantics.

The application converts that timestamp to a non-negative age for metrics and
tests exact due-time behavior. No event identity or payload is added to the
projection, and no persistence or delivery transition changes. This is an
internal query-contract extension, not a separate outbox runtime.

## Issue 326 Conversion Outcome Persistence Hardening

Conversion outcomes now preserve `conversionOutcomeId` resource identity and a
contiguous source-event version independently of `Idempotency-Key`. Equivalent
content under a new transport key replays without outcome, audit, or outbox
duplication. Changed identity, competing version, illegal transition, time
regression, or invalid correction returns a typed conflict.

Migration `006_conversion_outcome_lifecycle` adds source version, actor, and
append-only correction fields plus a unique intent/version constraint. It
copies every event in a contradictory legacy stream to
`idea_conversion_outcome_quarantine` without deleting source history. Such a
stream has no current posture and is excluded from readiness until reconciled.
PostgreSQL claims outcome identity/version before side effects and retries one
collision from fresh state. `make conversion-outcome-contract-gate` protects
the layered policy, provider parity, migration, API examples, and architecture
decision. The work remains internal design modularity and does not promote a
supported feature or create a separately deployable service.

## Issue 343 PostgreSQL Disaster Recovery

Issue `#343` adds a versioned disaster-recovery contract with 17-table schema
reconciliation, 15-minute RPO, 60-minute RTO, daily base-backup and continuous
WAL expectations, jurisdiction/access/encryption controls, named ownership,
cadence, and explicit certification blockers. A logical `pg_dump` drill and a
provider-restored validation adapter share the same domain policy,
application use case, read-only PostgreSQL inspector, and source-safe evidence
shape. Logical evidence is always `pitrProof=false` and cannot clear the
physical/WAL blocker.

The representative fixture uses production domain/repository paths for
candidate, review, feedback, conversion, report, AI-lineage, idempotency,
audit, and outbox creation, then adds governed pending, leased, failed,
dead-letter, published, recovery-audit, and downstream reconciliation states.
Real disposable PostgreSQL proof restored the backup into a separate clean
database, matched all table counts/hashes, returned zero relationship/state
violations, measured RPO at `0s` and RTO below `2s`, and then proved candidate
replay, recovery replay, downstream reconciliation fencing, stale-lease
rejection, and unchanged table hashes.

`LOTUS_IDEA_RECOVERY_POSTURE` now makes `draining`, `restoring`, `degraded`,
and invalid posture fail readiness and every durable-write guard before
mutation. The weekly CI workflow performs a real logical restore, validates
resume safety, retains evidence for 90 days, and generates provenance
attestation. Mainline dispatch `29157824527` at commit `e565c915` passed on
2026-07-11 with PostgreSQL 18.4: all 17 owned tables were restored, the latest
migration was `012_ai_run_attestation_receipt`, RPO was `0s`, RTO was below
`0.2s`, all relationship/state checks passed, and replay/fencing preserved
every table hash. The artifact remains explicitly `not_certified`,
`pitrProof=false`, and `supportedFeaturePromoted=false`.

Production PITR certification remains blocked until an approved
managed-provider physical base-backup/WAL exercise is captured. This is
internal design modularity and operator automation; database backup
infrastructure remains platform/provider owned and no new runtime service is
introduced.

## Outbox Capability-Package Hardening

Issue `#357` is implemented for the second measured capability family. Outbox
routes and DTOs, use cases, event/lineage and recovery policy, publisher port,
PostgreSQL and HTTP adapters, runtime composition, supportability metrics,
proof generators, contract gates, and focused tests now live in `outbox/`
packages inside their existing layers. Event construction and the in-memory
outbox repository behavior moved with the domain package: event writes,
delivery selection and leasing, publish/failure transitions, dead-letter
summaries, and operator recovery are now owned by one bounded outbox mixin. The
PostgreSQL fake behavior and event-lineage API proof moved with focused outbox
tests.

The migration is atomic: internal imports and contract source-of-truth paths
use the new package, public `app.domain` exports remain stable, and no legacy
module alias remains. Repository hygiene requires the canonical paths and
rejects every retired flat path. Broader implementation-readiness tests remain
outside the package because they own aggregate proof consumption rather than
outbox behavior.

This reduces navigation and ownership ambiguity across 34 production/support
modules and 22 focused test/helper modules without changing runtime topology. The API
and optional worker roles continue to share one Idea-owned PostgreSQL boundary.
No broker, consumer, mesh, Gateway/Workbench, data-product, or supported-feature
certification is implied.

Local closure evidence is green: `make ci` passed with MyPy over 739 files,
3,567 unit tests, 430 integration tests passed with 19 environment-dependent
skips, 4 E2E tests, 99.02% coverage over 23,779 statements, and no known
dependency vulnerabilities. A separate disposable PostgreSQL 18 run passed all
16 required runtime tests. Clean wheel contents/imports and a SHA-tagged Docker
build with container package, health, `/version`, and OCI-label smoke also
passed.

PR `#362` then merged by repository-approved rebase. Main Releasability run
`29235051710` and CodeQL run `29235047521` passed on exact main commit
`eba199252488638d46e24d833215c02989679a86`. The release manifest binds the
same commit, `main` branch, build timestamp, repository, CI run, SHA tag, OCI
labels, registry digest, keyless signature, SBOM, vulnerability scan, provenance
and SBOM attestations, digest-only Kubernetes reference, and `/version` response.
Wiki publication commit `5534db5` has zero source drift. Issue `#357` is closed
with `status/merged-main`; its local and remote feature branches are removed.

## Bounded Aggregate Mutations And Replay

Issues `#363` and `#364` remove whole-store hydration from ordinary PostgreSQL
mutation and replay paths. `app.infrastructure.persistence` now separates:

1. aggregate snapshot composition,
2. PostgreSQL mutation orchestration,
3. evidence replay and idempotency prechecks.

Mutation identity locks are acquired before sorted candidate locks and the
exact idempotency lock. The loader then hydrates only command candidates,
exact identity-linked candidates, and the candidate linked to the supplied
idempotency key. This covers candidate creation, lifecycle, review, feedback,
conversion intent/outcome, report evidence, AI request and replay-nonce
lineage, plus idempotency-only outbox delivery-run requests. Evidence replay
loads one candidate; report precheck loads one exact idempotency row and its
linked candidate. The existing domain repository still decides typed outcomes,
and the existing delta writer still commits candidate, lifecycle, idempotency,
audit, outbox, conversion, report, and AI-lineage changes atomically.

Query-shape tests reject whole-store candidate, idempotency, and outbox markers.
A disposable PostgreSQL 18 run passes all 17 required persistence, recovery,
queue, downstream, and lifecycle tests. It also caught and now protects an
explicit `text` cast required for nullable AI replay-nonce bind parameters.
Full `snapshot()` and `replace_snapshot()` remain administrative/test/DR
operations; ordinary API and application paths do not call them.

This is database-access and design modularity inside the existing deployable
and one Idea-owned PostgreSQL database. It adds no service, database, schema,
API/OpenAPI change, migration, source authority, or supported feature.

## Issue 381 Standalone Durable Runtime

Issue `#381` closes the app-local composition gap without introducing another
application boundary. `docker-compose.yml` now owns a dedicated PostgreSQL 18
container, major-version-correct named volume, one-shot migration dependency,
API, and optional worker wiring. API and worker roles still share one
Idea-owned database.

Local migration execution now records a strict version/name/content-checksum
prefix under a PostgreSQL advisory transaction lock. Apply executes pending
versions only; rollback removes tracked versions in reverse order; history
ahead of the image, gaps, and content drift fail closed atomically. The
release-attested staging/production migration use case and evidence contract
remain separate and unchanged.

Live local proof built the actual image, started a fresh PostgreSQL 18 volume,
applied migrations `001` through `015`, reached ready durable posture, repeated
Compose startup without replay, persisted a high-cash candidate through the
API, restarted the API container, and read the same candidate from the advisor
queue with `durableStorageBacked=true`. This proves standalone local durability
only; it does not promote a supported feature or certify production storage,
recovery, Workbench, data mesh, or client publication.

PR `#365` merged this increment by repository-approved rebase to exact main
SHA `6932606474caa32308f09a0e96969da0bb1eaafa`. Main Releasability run
`29239140276` and CodeQL run `29239134509` passed for that SHA. The release
lane also built and pushed the SHA-tagged image in CI, scanned it, generated
its SBOM, signed its digest, generated provenance and SBOM attestations, and
validated the published digest against runtime release identity. Wiki
publication commit `8386705` has zero source drift. Issues `#363` and `#364`
are closed with `status/merged-main`; the implementation branch is absent
locally and remotely. Slice 06 remains partially implemented only because the
external certification blockers listed in this RFC are still unresolved.

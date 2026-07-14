# RFC-0002 Slice 12: Advise And Manage Conversion Realization

Status: Partially implemented - internal conversion governance, source-versioned outcome lifecycle and correction policy, atomic repository-provider parity, durable claim-before-call submission and operator reconciliation, certified API/current-posture foundation, source-safe adapter foundations, governed downstream contract-plan gate, and digest-bound Advise/Manage route source-contract consumption; live execution and supported product proof remain blocked

## Outcome

Convert reviewed ideas into downstream advisory and portfolio-management
workflows without moving downstream authority into `lotus-idea`.

## Current Implementation Evidence

Implemented in this slice:

1. `src/app/domain/conversion_governance.py` adds a framework-free conversion
   governance layer for review-gated downstream intents and source-owned
   downstream outcomes.
2. `ConversionIntentCommand` requires a target, actor, idempotency key, reason
   codes, and timezone-aware request time before an intent can be created.
3. `request_conversion_intent` accepts only candidates that are already
   lifecycle-approved, have `approved_for_conversion` review posture, and carry
   ready evidence. It rejects unreviewed, not-approved, or blocked-evidence
   candidates.
4. Conversion targets map to the downstream source authority that owns
   realization:
   - `advise_proposal` -> `lotus-advise`,
   - `manage_review` -> `lotus-manage`,
   - `report_evidence` -> `lotus-report`.
5. Requesting a conversion intent moves the candidate into the appropriate
   converted lifecycle posture while keeping the conversion boundary
   `intent_only`; it does not create proposals, DPM actions, reports, orders,
   client communications, suitability approvals, compliance approvals, or
   mandate approvals.
6. `record_conversion_outcome` accepts outcome status only from the expected
   downstream source authority and records a governed outcome without granting
   execution, suitability, or client-communication authority.
7. Safe audit events are emitted for conversion intent and outcome recording
   without portfolio/client identifiers or raw payloads.
8. `tests/unit/test_conversion_governance.py` covers report, advise, and manage
   target mapping, review gating, blocked evidence, idempotency-key validation,
   target source-authority enforcement, safe audit fields, forbidden target
   vocabulary, and no downstream-authority semantics.
9. `src/app/domain/persistence.py` stores conversion intents and outcomes in
   the in-memory repository foundation with idempotency replay, conflict,
   not-found posture, lifecycle history updates, safe audit event append, and
   snapshot recovery for conversion-intent lookup.
10. `src/app/application/conversion_workflow.py` adds the application use case
    layer for repository precheck, conversion intent creation, and conversion
    outcome recording without re-running domain transitions on idempotency
    replay. Conversion-intent requests load the candidate through the shared
    bounded candidate lookup helper, so projection-capable repositories avoid
    whole-repository snapshot hydration before the review-gated conversion
    decision. Intent persistence remains on the existing repository mutation
    path. The application command requires the conversion-intent command
    idempotency key to match the repository replay key so internal workers
    cannot persist contradictory conversion evidence.
11. `src/app/api/conversion_governance.py` exposes certified internal API
    foundations:
    - `POST /api/v1/idea-candidates/{candidateId}/conversion-intents`,
    - `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes`.
12. `docs/operations/endpoint-certification-ledger.json` records certification
    evidence, examples, error posture, and test proof for the conversion API
    foundations.
13. `tests/unit/test_idea_persistence.py` and
    `tests/integration/test_review_workflow_api.py` cover repository
    idempotency, audit posture, API permission, invalid state, missing
    resources, wrong source authority, replay, and conflict behavior.
    `tests/unit/test_conversion_workflow_application.py` adds focused
    projection-only coverage proving conversion-intent requests and missing
    candidate handling do not require `snapshot()` hydration, plus regression
    coverage for mismatched application/domain idempotency rejection.
14. `tests/integration/test_postgres_runtime_integration.py` now proves the
    first PostgreSQL-backed internal report conversion path by creating a
    review-approved candidate, recording the report conversion intent, replaying
    the intent from database idempotency state, recording a source-authorized
    conversion outcome, and validating the conversion intent/outcome tables.
    `tests/unit/test_postgres_repository.py` also proves the PostgreSQL adapter
    rejects mismatched conversion-intent idempotency before writing intent JSON
    or repository idempotency rows.
15. `contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`
    now holds the planned Advise, Manage, and Report handoff contract rows as
    machine-readable repository truth.
16. `scripts/downstream_realization_contract_gate.py` and
    `make downstream-realization-contract-gate` block missing contract rows,
    source-authority drift, current-route claims, missing blockers, and
    premature route-existence, downstream-execution, or supported-feature
    claims.
17. `src/app/ports/downstream_realization.py` and
    `src/app/infrastructure/downstream_realization.py` add source-safe HTTP
    adapter foundations for Advise proposal intent and Manage action intent
    handoff envelopes. They preserve downstream source authority, carry
    bounded evidence and lifecycle fields, propagate correlation/trace
    headers, and map downstream failures to product-safe reasons without
    exposing raw downstream responses.
18. `src/app/application/downstream_realization_readiness.py` and
    `GET /api/v1/downstream-realization/readiness` add a certified internal
    operator diagnostic over current conversion intent/outcome counts and
    Advise/Manage realization blockers. The diagnostic also exposes
    adapter-foundation presence and planned downstream contract-readiness
    records for the Advise proposal and Manage action handoff seams, with owner
    repositories, planned target-route posture, adapter status, evidence refs,
    and blockers. It requires both the `operator` role and
    `idea.downstream-realization.readiness.read` capability, emits
    `downstream_realization_readiness_read`, and keeps the supportability
    posture `not_certified` until live downstream contract proof exists.
19. `src/app/application/downstream_realization.py` now adds source-safe
    application orchestration for submitting existing Advise proposal and
    Manage action conversion intents through the downstream realization ports.
    The orchestration selects the correct downstream client, atomically claims
    the submission before the adapter call, propagates correlation and trace
    identifiers, and lease-fences local finalization. Definitive acceptance or
    rejection is returned only after local state commits. Timeout, 5xx,
    malformed response, transport ambiguity, lease loss, or local finalization
    failure returns `reconciliation_required`; same-key retries never call the
    downstream service again. Operators can inspect and explicitly resolve the
    uncertain posture by opaque support reference with role, capability,
    idempotency, audit, and source-safety controls. Authoritative acceptance,
    completion, suitability, action-register, materialization, and failure
    truth remains owned by the downstream service and the existing
    conversion-outcome recording API.
20. `tests/unit/test_downstream_realization_application.py` proves Advise
    routing, Manage failure mapping, report-target rejection through the
    conversion-intent submission path, not-found behavior, local idempotency
    replay/conflict/not-configured persistence, no outcome recording, no
    downstream-authority grant, and no supported-feature promotion.
    Downstream realization now obtains conversion intents and report
    evidence-pack requests through explicit repository lookup methods before
    any adapter call; durable PostgreSQL providers query
    `idea_conversion_intent` or `idea_report_evidence_pack_request` directly
    instead of hydrating whole repository snapshots. This is internal design
    modularity only, not a separate downstream-realization runtime service.
21. `src/app/api/downstream_realization.py` exposes the certified internal
    `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions`
    route for existing Advise and Manage conversion intents. The route requires
    `idea.downstream-realization.submit` and `Idempotency-Key`, obtains
    configured Advise/Manage clients from
    `src/app/runtime/downstream_realization_state.py`,
    propagates correlation, trace, and idempotency headers through the
    application layer, returns `idempotencyReplayed=true` when local posture is
    replayed without an adapter call, returns `409 idempotency_conflict` when a
    key is reused for a different request fingerprint, and fails closed with
    `503 downstream_realization_not_configured` when adapter configuration is
    absent.
22. `docs/operations/endpoint-certification-ledger.json` and
    `docs/operations/api-certification.md` record endpoint certification,
    product-safe errors, usage boundaries, and operation-event evidence for
    the downstream submission route.
23. `tests/integration/test_downstream_realization_api.py` proves the
    Advise submission success path, missing-adapter fail-closed posture,
    idempotency replay, idempotency conflict, permission denial, report-target
    rejection on the conversion route, not-certified operation-event emission,
    and absence of downstream outcome recording or supported-feature promotion.
24. `src/app/application/downstream_realization/route_source_contract.py`,
    `scripts/downstream_realization/generate_advise_route_source_contract.py`,
    `scripts/downstream_realization/generate_manage_route_source_contract.py`, and
    `make downstream-route-source-contract-proof-gate` now define and enforce
    closed-field, digest-bound Advise and Manage route `source_contract`
    artifacts. They clear no blocker and explicitly preserve
    `advise_live_contract_proof_missing` and
    `manage_live_contract_proof_missing`. Missing sibling evidence writes
    invalid non-proof artifacts and preserves blockers.
25. `src/app/application/downstream_realization_readiness.py` consumes valid
    Advise/Manage source contracts as supporting evidence only. It keeps both
    live-route blockers together with
    `suitability_policy_authority_remains_lotus_advise` and
    `rebalance_execution_authority_remains_lotus_manage` intact, so route
    evidence cannot become suitability, rebalance, execution, or supported
    product proof.
26. `tests/unit/downstream_realization/test_route_source_contract.py` and
    `tests/unit/test_downstream_realization_readiness.py` prove source-safe
    payloads, fail-closed missing sibling evidence, anti-overclaim flags,
    digest binding, closed-field validation, zero blocker clearance, and
    retained live-route and downstream-authority blockers.
27. `tests/unit/test_downstream_realization_lookup.py` and
    `tests/unit/test_postgres_downstream_lookup.py` prove the bounded lookup
    path bypasses `snapshot()` while preserving idempotency posture and direct
    PostgreSQL query shape for conversion intents and report evidence-pack
    requests.

## Issue 326 Outcome Lifecycle Hardening

`conversionOutcomeId` is now a source-event resource identity rather than an
alias for the HTTP retry key. The versioned policy accepts legal requested,
accepted, rejected, failed, and completed progressions; terminal corrections
must append the next version, link the superseded current event, and state a
reason. Accepted and completed facts require a downstream reference.

The application use case performs bounded intent, identity, and history reads
before domain evaluation. In-memory and PostgreSQL adapters repeat the policy
at persistence. PostgreSQL atomically protects outcome identity and one version
per intent, while migration 006 preserves but quarantines contradictory legacy
streams. Candidate detail exposes full history plus one policy-valid current
posture per intent; readiness excludes quarantined streams.

This closes the issue's internal lifecycle and provider-parity gap only.
Advise, Manage, and Report remain authoritative for their outcomes, and no
suitability, execution, rebalance, reporting, archive, client-publication, or
supported-feature authority moves into `lotus-idea`.

## Remaining Work

This slice is not yet a supported conversion product. Remaining work includes:

1. Gateway/Workbench proof,
2. `lotus-advise` live route acceptance, suitability, policy, proposal
   lifecycle, and client communication certification beyond source declarations,
3. `lotus-manage` live route acceptance, mandate, DPM/rebalance/action,
   execution, and settlement certification beyond source declarations,
4. `lotus-report` report-evidence package intake proof for the first
   report-only conversion path,
5. downstream failure/rejection/completion integration tests across owning
   services,
6. data-product trust telemetry and mesh certification,
7. supported-feature promotion after runtime and downstream proof.

The downstream-realization readiness diagnostic and submission API are blocker
and submission-posture foundations only. They do not create proposals,
suitability records, manage action-register records, rebalance records, orders,
client communications, reports, rendered output, or archive records. Planned
contract-readiness records and configured adapter calls are not runtime proof.
Valid Advise and Manage source contracts prove only that governed declarations
exist at bound digests; they are not route-serving, acceptance, authorization,
tenant-isolation, suitability, rebalance, execution, client-publication, or
supported-feature proof.

## Required Work

1. Implement `IdeaConversionIntent` and `IdeaConversionOutcome`.
2. Add certified internal API/OpenAPI contracts for conversion intent and
   outcome recording.
3. Add advisory conversion contract into `lotus-advise` for proposal or
   suitability workflow intake.
4. Add manage conversion contract into `lotus-manage` for DPM review/action
   candidate intake.
5. Record idempotency, downstream acceptance, rejection, failure, and
   completion.

## Acceptance Gate

1. Conversion requires human review.
2. Advise owns proposal and suitability realization.
3. Manage owns action and rebalance realization.
4. No conversion path creates orders, client communications, or autonomous
   advice.

The current implementation satisfies the internal domain governance, certified
internal API foundation, source-safe submission API, and source-safe
adapter-foundation portions of this gate, plus route-only proof consumption
when sibling evidence is present. Cross-repository downstream realization
remains planned until the owning services certify live acceptance,
suitability/rebalance authority, downstream outcomes, and product support.

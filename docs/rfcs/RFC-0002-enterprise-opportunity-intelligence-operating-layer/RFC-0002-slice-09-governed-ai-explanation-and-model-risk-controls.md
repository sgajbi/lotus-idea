# RFC-0002 Slice 09: Governed AI Explanation And Model-Risk Controls

Status: Partially implemented - internal AI governance, certified API foundation, and source-safe API-idempotent lineage persistence with PostgreSQL runtime proof

## Outcome

Add AI-assisted explanations through `lotus-ai` without weakening deterministic
evidence, review, or source-authority controls.

## Current Implementation Evidence

Implemented in this slice:

1. `src/app/domain/ai_governance.py` adds framework-free AI governance models
   for `lotus-ai` workflow-pack references, redacted evidence envelopes,
   AI-output claims, proposed actions, verifier outcomes, deterministic
   fallback, and safe audit events.
2. Redacted evidence keeps candidate identity, evidence packet identity,
   lineage content hash, source product identity, source version, freshness,
   data-quality status, reason codes, unsupported reasons, score posture, and
   review posture. It deliberately excludes source routes, raw source hashes,
   prompt text, provider output, portfolio identifiers, client identifiers,
   trace identifiers, and correlation identifiers.
3. AI request metadata fails closed when forbidden keys such as `portfolio_id`,
   `client_id`, raw prompt/output, route, trace, or correlation identifiers are
   supplied.
4. Advisor rationale and meeting-preparation drafting require ready evidence
   and a review-ready candidate lifecycle. Missing-evidence checks can run on
   blocked evidence.
5. The API and domain command path now share one governed workflow-pack
   contract: public request identity `lotus-ai:idea-explanation:v1`, version
   `v1`, and evaluator `lotus-ai:governed-verifier:v1` deliberately map to
   proof identity `idea_explanation.pack@v1`. Any unregistered pack id,
   version, evaluator ref, or purpose fails closed with a product-safe
   `400 invalid_ai_workflow_pack` before candidate lookup or lineage
   persistence.
6. Deterministic fallback records an AI-unavailable posture without exposing
   raw prompt/provider data and without changing candidate state.
7. The verifier blocks unsupported source claims and forbidden actions such as
   suitability approval, compliance approval, mandate approval, trade/order
   instructions, final recommendations, and client communication.
   It validates both the structured action type and untrusted label content
   through `lotus-idea.ai-action-content-policy.v1`; accepted labels are
   replaced with canonical server-owned wording, while rejected raw labels are
   not persisted or returned.
8. AI explanation results expose `grants_downstream_authority=False`, so AI
   output cannot approve suitability, compliance, mandate, execution, client
   communication, score, lifecycle, review, or conversion state.
9. `tests/unit/test_ai_governance.py` covers redaction, sensitive metadata
   rejection, evidence/lifecycle gates, blocked-evidence missing-evidence
   checks, deterministic fallback, supported-output verification, unsupported
   claim blocking, forbidden-action blocking, request/workflow identity
   validation, governed workflow-pack allowlist rejection, no candidate-state
   mutation, and projection-only candidate lookup without `snapshot()`
   hydration before AI explanation evaluation.
10. `src/app/application/ai_governance.py` orchestrates persisted candidate
   lookup through the shared bounded candidate lookup helper, governed request
   construction, deterministic fallback, verifier evaluation, and source-safe
   API-idempotent lineage recording without provider execution or
   supported-feature claims.
   For projection-capable repositories this avoids whole-repository snapshot
   hydration before evaluation; lineage persistence remains on the existing
   repository mutation path.
11. `src/app/api/ai_governance.py` exposes the certified internal endpoint
    `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`.
    It requires `idea.ai-explanation.evaluate`, returns redacted evidence only,
    blocks unsupported claims and forbidden actions, requires
    `Idempotency-Key`, records source-safe lineage, emits bounded
    `ai_explanation` operation events, reports
    `durableStorageBacked` from the active repository provider, and keeps
    `lotusAiRuntimeExecuted=false` and `supportedFeaturePromoted=false`.
12. `src/app/application/ai_governance.py` also exposes a deterministic
    AI-explanation readiness snapshot, and `src/app/api/ai_governance.py`
    publishes it through `GET /api/v1/ai-explanations/readiness` for operator
    model-risk diagnostics. The route requires both the `operator` role and
    `idea.ai-explanation.readiness.read`, reports `readinessStatus=blocked`,
    `supportabilityStatus=not_certified`, `lotusAiRuntimeExecuted=false`,
    `durableAiLineageStoreBacked` from the active repository provider, and
    `supportedFeaturePromoted=false`, and returns only guardrail availability
    plus certification blockers.
13. `src/app/domain/persistence.py` adds `AIExplanationLineageRecord` and
    idempotent lineage persistence decisions. `InMemoryIdeaRepository` records
    exactly one lineage record per AI request id, replays identical lineage,
    blocks changed-content conflicts, appends the safe audit event, and does
    not create outbox work for AI explanation evaluation. The repository port
    also exposes request-level idempotency for lineage writes so same-key
    retries replay and same-key changed fingerprints conflict before duplicate
    lineage writes.
14. `migrations/002_ai_explanation_lineage.sql`,
    `migrations/002_ai_explanation_lineage.rollback.sql`,
    `src/app/infrastructure/postgres_codecs.py`, and
    `src/app/infrastructure/postgres_repository.py` add PostgreSQL persistence
    for source-safe AI explanation lineage. The stored record includes request
    id, candidate id, evidence packet id, evidence content hash, workflow-pack
    identity, posture, verifier outcome, fallback state, reason codes, bounded
    output summary ids, actor, timestamps, lineage hash, and
    no-downstream-authority posture. It excludes prompts, provider payloads,
    raw source routes, trace ids, correlation ids, portfolio ids, client ids,
    request bodies, response bodies, and free-form source payloads.
15. `tests/unit/test_ai_explanation_readiness.py` proves the readiness snapshot
    stays blocked and not certified until runtime and lineage evidence exist.
16. `tests/integration/test_ai_governance_api.py` covers deterministic
    fallback, verified-output acceptance, unsupported-claim blocking,
    forbidden-action blocking, permission denial, missing candidate handling,
    invalid candidate state, provider-unsafe metadata, unregistered workflow-pack
    id/version/evaluator rejection, and source-safe AI readiness diagnostics,
    plus API idempotency required/replay/conflict behavior and accepted/
    replayed/conflicting lineage persistence.
17. `tests/integration/test_api_operation_events.py` proves the API emits the
    bounded `ai_explanation` operation event and the not-certified
    `ai_explanation_readiness_read` operation event.
18. `tests/unit/test_idea_persistence.py` and
    `tests/unit/test_postgres_repository.py` prove in-memory and PostgreSQL
    lineage acceptance, API idempotency replay/conflict handling, request-id
    replay/conflict handling, snapshot recovery, and source-safe JSON
    persistence.
19. `tests/integration/test_postgres_runtime_integration.py` proves the
    FastAPI runtime path records AI explanation lineage through the configured
    PostgreSQL repository, replays the same API idempotency key after
    repository reload, rejects distinct-key changed request-id lineage with a
    source-safe `409`, includes
    `idea_ai_explanation_lineage` in rollback/reapply schema proof, and keeps
    prompts, provider payloads, raw source routes, trace ids, correlation ids,
    portfolio ids, client ids, and free-form source payloads out of the stored
    lineage JSON.
20. `tests/unit/test_ai_explanation_readiness.py` and
    `tests/integration/test_ai_governance_api.py` prove the readiness
    diagnostic reports durable AI lineage-store backing from the active
    repository while keeping supportability `not_certified`, blockers present,
    no `lotus-ai` runtime execution, and no supported-feature promotion.
21. `src/app/domain/ai_action_policy.py` provides a deterministic, versioned,
    fail-closed action-content boundary. Adversarial unit and API integration
    tests cover directive hiding behind allowed enums, case/punctuation/common
    substitution obfuscation, unsupported scripts, canonical-label projection,
    source-safe audit, lineage versioning, and replay/conflict behavior.
22. `src/app/domain/ai_output_integrity.py` and migration `010` bind every
    accepted, blocked, and fallback result to
    `lotus-idea.ai-output-integrity.v1`. The ordered canonical payload covers
    advisor-visible explanation/claim/action content plus workflow/evaluator
    and policy metadata; persistence retains only the digest and version.
    PostgreSQL hydration verifies column/JSON parity and the enclosing lineage
    hash. Pre-v1 rows are explicitly unverifiable rather than retroactively
    certified.
23. `lotus-idea.ai-execution-provenance-policy.v1` and migration `011`
    distinguish deterministic fallback, local/test unattested fixtures, and
    historical pre-attestation records. Demo, staging, and production reject
    self-asserted workflow output before candidate lookup or lineage write.
    Signed producer/consumer contracts are implemented locally: Lotus AI issues
    Ed25519 run attestations and fixed-path key discovery, while Idea verifies
    exact claims and digests, maps producer output, persists a bounded receipt,
    and rejects run-id or nonce replay. Producer issue `sgajbi/lotus-ai#113`
    is closed with producer main commit `162df803` and Main Releasability run
    `29153879884`; the Idea consumer is mainline-proven through `f496c442` and
    run `29179489433`. Local fixtures and source inspection still cannot clear
    live-provider execution, runtime trust, Workbench, or promotion blockers.
24. `src/app/domain/ai_metadata_policy.py` implements
    `lotus-idea.ai-metadata-envelope.v1` as a closed, purpose-scoped allowlist.
    The typed request DTO rejects unknown fields, the domain rejects
    unapproved values before candidate lookup or lineage persistence, OpenAPI
    publishes the closed shape, and evaluation/readiness responses publish the
    policy version. Lineage retains approved field names only. The model-risk
    contract machine-checks classification, forwarding, retention, and
    no-raw-value guarantees. No provider adapter or runtime split is claimed.
25. Issue `#389` adds `src/app/domain/ai_explanation/grounding.py` as a bounded
    deterministic explanation policy. Accepted advisor-visible narrative is
    rendered only from ordered claims that passed source-product verification;
    the submitted provider narrative remains attested input and is neither
    returned nor persisted. The response exposes claim-level source product,
    version, as-of, freshness, and quality references. Blocked output exposes no
    grounded claims. Output integrity binds the grounding policy and the
    submitted provider-output digest without retaining raw narrative, while the
    model-risk contract and readiness endpoint expose the active grounding
    posture. Duplicate claim or source-product identities fail closed. This is
    design modularity inside the existing Idea process, not an AI runtime split.
26. Issue `#392` replaces the static source-scan runtime claim with an actual
    `idea_explanation.pack@v1` execution proof. The layered path is automation
    input -> `app.application.ai_runtime_proof` ->
    `app.ports.lotus_ai_runtime` ->
    `app.infrastructure.lotus_ai.workflow_runtime` -> Lotus AI. A valid v2
    proof binds eligible caller/pack/run/task identity, the synthetic redacted
    evidence hash, completed execution, `ACTION_REQUIRED` review posture, and
    blocked client-publication/downstream authority into a source-safe receipt
    digest. Deterministic stub execution clears only the generic runtime seam;
    live-provider execution, production attestation acceptance, runtime-trust
    certification, Workbench proof, and feature promotion remain blocked. This
    is design modularity and automation around the existing runtimes, not a new
    Idea service.
27. Issue `#396` replaces source-contract inference for durable AI lineage with
    a closed `ci_execution` receipt. `src/app/domain/proof_evidence/` owns the
    evidence taxonomy and receipt integrity; the organized
    `src/app/application/ai_lineage_store_proof/` package owns proof assembly
    and receipt consumption. Main Releasability runs the exact PostgreSQL
    lineage test, uploads its JUnit artifact, binds the server-reported artifact
    digest and exact mainline run identity into the receipt, and only then
    clears `certified_ai_lineage_store_missing`. Missing, malformed, tampered,
    non-mainline, failed, or wrong-job evidence fails closed. Source files and
    Make targets remain useful `source_contract` evidence but cannot prove
    execution. This is design modularity inside the existing Idea process, not
    a separately scalable service boundary.

Validation evidence from the implementation slice:

1. `.venv\Scripts\python.exe -m ruff check src\app\domain\ai_governance.py src\app\domain\ideas.py src\app\domain\__init__.py tests\unit\test_ai_governance.py`
2. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini`
3. `.venv\Scripts\python.exe -m pytest tests/unit/test_ai_governance.py`
4. `python -m pytest tests/integration/test_ai_governance_api.py tests/integration/test_api_operation_events.py` passed with `8 passed` after adding the AI explanation API foundation.
5. `python -m ruff check src/app/application/ai_governance.py src/app/api/ai_governance.py tests/integration/test_ai_governance_api.py tests/integration/test_api_operation_events.py` passed after adding the API route and event coverage.
6. `make ci` passed after the API foundation with `59` integration tests, `2`
   e2e tests, `218` unit tests, coverage gate at `99.17%`, and dependency
   audit reporting no known vulnerabilities.
7. `python -m pytest tests/unit/test_ai_explanation_readiness.py tests/integration/test_ai_governance_api.py tests/integration/test_api_operation_events.py`
   is the focused readiness diagnostic proof for the current slice.
8. `python -m pytest tests/unit/test_idea_persistence.py tests/unit/test_postgres_repository.py tests/integration/test_ai_governance_api.py`
   passed after adding source-safe lineage persistence.
9. `python scripts/migration_contract_gate.py` and
   `python scripts/run_migrations.py --direction apply --dry-run` passed after
   adding migration `002_ai_explanation_lineage`.
10. `LOTUS_IDEA_POSTGRES_INTEGRATION_URL=postgresql://... make postgres-integration-gate`
    passed locally against a disposable `postgres:18-alpine` container with
    `5 passed`, including durable AI explanation lineage accepted/replayed/
    conflict behavior through the API.
11. `python -m pytest tests/unit/test_ai_explanation_readiness.py tests/integration/test_ai_governance_api.py`
    is the focused readiness-posture proof for repository-aware durable lineage
    reporting.
12. `.venv\Scripts\python.exe -m pytest tests/unit/test_ai_governance.py::test_ai_explanation_uses_candidate_projection_without_snapshot`
    is the focused bounded candidate lookup proof for explanation evaluation.
13. `python -m pytest tests/unit/test_ai_governance.py tests/unit/test_ai_governance_api_contract.py tests/unit/test_ai_workflow_pack_registration_proof.py tests/integration/test_ai_governance_api.py -q`
    passed with `74 passed` after adding the governed workflow-pack allowlist
    and product-safe `invalid_ai_workflow_pack` API rejection.
14. `make check` passed after the signed-attestation consumer slice with all
    lint, maintainability, duplicate, security, contract, proof, migration,
    OpenAPI, type, architecture, endpoint, and supported-feature gates plus
    `3365 passed` unit tests. Supported-feature promotion remained blocked.
15. Issue `#389` local closure passed `172` focused AI governance, attestation,
    integrity, lineage, persistence, API, and operation-event tests; all `17`
    cases in `make postgres-integration-gate` against an isolated PostgreSQL 18
    database; `make check`; and `make ci`. The final CI-parity lane passed
    `3642` unit tests, `451` integration tests with `28` environment-dependent
    PostgreSQL skips, `4` E2E tests, MyPy over `776` source files, `99.02%`
    coverage over `24545` statements, OpenAPI/model-risk/issue/documentation/
    repository-organization gates, and dependency audit with no known
    vulnerabilities. The skipped integration cases are covered by the separate
    required PostgreSQL run.
16. PR `#390` merged the grounded-narrative capability by rebase to exact main
    SHA `67a6e005`. Main Releasability run `29300549721` and CodeQL run
    `29300546423` passed. The releasability lane also validated the SHA-tagged
    digest image, runtime metadata, vulnerability scan, SBOM, signature,
    provenance, release manifest, and digest-bound deployment evidence. Wiki
    publication `f86a57c` synchronized the three changed pages with zero drift.
    Issue `#389` is implementation-complete; Slice 09 remains partial only for
    the separate live-provider/production, Gateway/Workbench, and promotion
    blockers below.
17. Issue `#392` closed through PR `#394` with `65` focused runtime-proof and
    HTTP-adapter tests covering the changed boundary at `100%`; full local
    coverage passed at `99.03%`. A running canonical Lotus AI service returned
    a completed, review-gated deterministic stub run bound to clean commit
    `f296f4eb`; the generated v2 proof retained no request body or generated
    output. PR `#394` merged to exact-main SHA `b892d5d6`; Main Releasability
    `29303651841`, CodeQL `29303648849`, and wiki publication `48fd63a` passed.
    Live-provider/production approval and the other blockers below remain.
18. Issue `#396` validation passed `121` focused proof tests, all `17`
    disposable PostgreSQL 18 integration tests, and full local `make ci` with
    `3704` unit, `451` integration, and `4` E2E tests at `99.01%` coverage.
    PR `#397` merged the capability; failed exact-main run `29306713267`
    correctly rejected GitHub's non-canonical artifact-digest representation.
    Fix-forward PR `#398` added strict canonical mapping and regression tests.
    Exact-main SHA `5cf7592b` then passed Main Releasability `29307190040` and
    CodeQL `29307186825`. The downloaded v2 proof passed the production
    validator, bound the exact repository/workflow/job/run/commit/main ref and
    PostgreSQL artifact digest, and cleared only
    `certified_ai_lineage_store_missing`.
19. Issue `#401` applies the same evidence-classification rule to persistence.
    The durable repository proof is now a capability package rather than a
    flat application module, and source/design evidence alone cannot clear its
    runtime-backed blockers. Only an exact-main, digest-bound PostgreSQL CI
    receipt derived from the governed migration, persistence, idempotency,
    audit/outbox, concurrency, and repository-side queue-pagination tests can
    clear them. Production database deployment, runtime trust telemetry,
    Gateway/Workbench realization, and supported-feature promotion remain
    explicitly blocked.

## Current Governance References

The Slice 09 implementation is aligned to current official AI/model-risk
reference points:

1. NIST AI Risk Management Framework and NIST AI 600-1 Generative AI Profile:
   `https://www.nist.gov/itl/ai-risk-management-framework`
2. MAS FEAT principles for responsible AI/data analytics in financial services:
   `https://www.mas.gov.sg/publications/monographs-or-information-paper/2018/feat`
3. 2026 OCC/Federal Reserve/FDIC revised model-risk management guidance:
   `https://www.occ.gov/news-issuances/bulletins/2026/bulletin-2026-13.html`

Product research and differentiation decisions are governed by
`docs/research/advisor-intelligence-product-differentiation.md`. Its candidate
capabilities are hypotheses, not implementation or supported-feature evidence.
Refresh its primary-source research and satisfy its research-to-delivery gate
before resuming material Slice 09 capability implementation.

These references shape controls only. Lotus product truth remains the code,
tests, RFC evidence, supported-features ledger, CI, and published wiki source.

## Remaining Work

This slice is not yet a supported AI explanation product. Remaining work
includes:

1. prompt registry, RAG, evaluation, and provider telemetry owned by
   `lotus-ai`,
2. live-provider execution and production workflow-pack certification beyond
   the current actual deterministic-stub runtime proof, source-safe AI lineage
   store proof, and certified repo-owned model-risk operations artifacts,
3. Gateway/Workbench proof,
4. certified runtime trust telemetry beyond the current model-risk operations
   dashboard, alert-rule, and runbook artifacts,
5. supported-feature promotion after runtime proof.

## Required Work

1. Send only redacted evidence packets and approved metadata to `lotus-ai`.
2. Persist lineage refs, workflow-pack version, evaluation posture, verifier
   result, fallback state, and review posture.
3. Block unsupported claims, autonomous advice, client communication, and raw
   provider output exposure.

## Acceptance Gate

1. AI unavailable path returns deterministic fallback.
2. Prompt/input redaction tests pass.
3. Unsupported-claim and forbidden-action tests pass.
4. AI output cannot change score, lifecycle, source facts, review state, or
   conversion state.

Generic deterministic-stub `lotus-ai` workflow execution and mainline durable
lineage-store CI certification are implemented. Live-provider and production
model-risk approval, Gateway/Workbench realization, and supported-feature
promotion remain planned and blocked.

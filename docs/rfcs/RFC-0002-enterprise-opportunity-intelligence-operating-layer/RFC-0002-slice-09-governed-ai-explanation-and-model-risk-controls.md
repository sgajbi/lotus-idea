# RFC-0002 Slice 09: Governed AI Explanation And Model-Risk Controls

Status: Partially implemented - internal AI governance, certified API foundation, and source-safe lineage persistence with PostgreSQL runtime proof

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
5. Deterministic fallback records an AI-unavailable posture without exposing
   raw prompt/provider data and without changing candidate state.
6. The verifier blocks unsupported source claims and forbidden actions such as
   suitability approval, compliance approval, mandate approval, trade/order
   instructions, final recommendations, and client communication.
7. AI explanation results expose `grants_downstream_authority=False`, so AI
   output cannot approve suitability, compliance, mandate, execution, client
   communication, score, lifecycle, review, or conversion state.
8. `tests/unit/test_ai_governance.py` covers redaction, sensitive metadata
   rejection, evidence/lifecycle gates, blocked-evidence missing-evidence
   checks, deterministic fallback, supported-output verification, unsupported
   claim blocking, forbidden-action blocking, request/workflow identity
   validation, and no candidate-state mutation.
9. `src/app/application/ai_governance.py` orchestrates persisted candidate
   snapshot lookup, governed request construction, deterministic fallback,
   verifier evaluation, and source-safe lineage recording without provider
   execution or supported-feature claims.
10. `src/app/api/ai_governance.py` exposes the certified internal endpoint
    `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`.
    It requires `idea.ai-explanation.evaluate`, returns redacted evidence only,
    blocks unsupported claims and forbidden actions, records source-safe
    lineage, emits bounded `ai_explanation` operation events, reports
    `durableStorageBacked` from the active repository provider, and keeps
    `lotusAiRuntimeExecuted=false` and `supportedFeaturePromoted=false`.
11. `src/app/application/ai_governance.py` also exposes a deterministic
    AI-explanation readiness snapshot, and `src/app/api/ai_governance.py`
    publishes it through `GET /api/v1/ai-explanations/readiness` for operator
    model-risk diagnostics. The route requires both the `operator` role and
    `idea.ai-explanation.readiness.read`, reports `readinessStatus=blocked`,
    `supportabilityStatus=not_certified`, `lotusAiRuntimeExecuted=false`,
    `durableAiLineageStoreBacked=false`, and `supportedFeaturePromoted=false`,
    and returns only guardrail availability plus certification blockers.
12. `src/app/domain/persistence.py` adds `AIExplanationLineageRecord` and
    idempotent lineage persistence decisions. `InMemoryIdeaRepository` records
    exactly one lineage record per AI request id, replays identical lineage,
    blocks changed-content conflicts, appends the safe audit event, and does
    not create outbox work for AI explanation evaluation.
13. `migrations/002_ai_explanation_lineage.sql`,
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
14. `tests/unit/test_ai_explanation_readiness.py` proves the readiness snapshot
    stays blocked and not certified until runtime and lineage evidence exist.
15. `tests/integration/test_ai_governance_api.py` covers deterministic
    fallback, verified-output acceptance, unsupported-claim blocking,
    forbidden-action blocking, permission denial, missing candidate handling,
    invalid candidate state, forbidden metadata, and source-safe AI readiness
    diagnostics, plus accepted/replayed/conflicting lineage persistence.
16. `tests/integration/test_api_operation_events.py` proves the API emits the
    bounded `ai_explanation` operation event and the not-certified
    `ai_explanation_readiness_read` operation event.
17. `tests/unit/test_idea_persistence.py` and
    `tests/unit/test_postgres_repository.py` prove in-memory and PostgreSQL
    lineage acceptance, replay, conflict handling, snapshot recovery, and
    source-safe JSON persistence.
18. `tests/integration/test_postgres_runtime_integration.py` proves the
    FastAPI runtime path records AI explanation lineage through the configured
    PostgreSQL repository, replays the same AI request id after repository
    reload, rejects changed lineage with a source-safe `409`, includes
    `idea_ai_explanation_lineage` in rollback/reapply schema proof, and keeps
    prompts, provider payloads, raw source routes, trace ids, correlation ids,
    portfolio ids, client ids, and free-form source payloads out of the stored
    lineage JSON.

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

## Current Governance References

The Slice 09 implementation is aligned to current official AI/model-risk
reference points:

1. NIST AI Risk Management Framework and NIST AI 600-1 Generative AI Profile:
   `https://www.nist.gov/itl/ai-risk-management-framework`
2. MAS FEAT principles for responsible AI/data analytics in financial services:
   `https://www.mas.gov.sg/publications/monographs-or-information-paper/2018/feat`
3. 2026 OCC/Federal Reserve/FDIC revised model-risk management guidance:
   `https://www.occ.gov/news-issuances/bulletins/2026/bulletin-2026-13.html`

These references shape controls only. Lotus product truth remains the code,
tests, RFC evidence, supported-features ledger, CI, and published wiki source.

## Remaining Work

This slice is not yet a supported AI explanation product. Remaining work
includes:

1. `lotus-ai` workflow-pack registration and runtime execution,
2. prompt registry, RAG, evaluation, and provider telemetry owned by
   `lotus-ai`,
3. certified runtime AI lineage-store evidence and model-risk operating proof
   beyond the current PostgreSQL persistence proof,
4. Gateway/Workbench proof,
5. model-risk operations dashboards, trust telemetry, and support runbooks,
6. supported-feature promotion after runtime proof.

## Required Work

1. Define a bounded `lotus-ai` workflow pack for idea explanation or missing
   evidence checking.
2. Send only redacted evidence packets and approved metadata to `lotus-ai`.
3. Persist lineage refs, workflow-pack version, evaluation posture, verifier
   result, fallback state, and review posture.
4. Block unsupported claims, autonomous advice, client communication, and raw
   provider output exposure.

## Acceptance Gate

1. AI unavailable path returns deterministic fallback.
2. Prompt/input redaction tests pass.
3. Unsupported-claim and forbidden-action tests pass.
4. AI output cannot change score, lifecycle, source facts, review state, or
   conversion state.

Runtime `lotus-ai` workflow execution remains planned until a later slice adds
ports/adapters, runtime lineage certification, Gateway/Workbench contracts, and
cross-repository proof.

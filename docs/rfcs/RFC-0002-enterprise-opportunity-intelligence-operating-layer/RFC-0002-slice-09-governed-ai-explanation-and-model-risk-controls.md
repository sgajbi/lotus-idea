# RFC-0002 Slice 09: Governed AI Explanation And Model-Risk Controls

Status: Partially implemented - internal AI governance foundation only

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

Validation evidence from the implementation slice:

1. `.venv\Scripts\python.exe -m ruff check src\app\domain\ai_governance.py src\app\domain\ideas.py src\app\domain\__init__.py tests\unit\test_ai_governance.py`
2. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini`
3. `.venv\Scripts\python.exe -m pytest tests/unit/test_ai_governance.py`

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
3. durable persistence for AI request/result lineage,
4. application orchestration and API/OpenAPI contracts,
5. endpoint certification and Gateway/Workbench proof,
6. model-risk operations dashboards, trust telemetry, and support runbooks,
7. supported-feature promotion after runtime proof.

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
ports/adapters, persistence, API contracts, endpoint certification, and
cross-repository proof.

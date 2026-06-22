# AI Governance And Model-Risk Posture

`lotus-idea` uses AI only as a governed assistance layer. The current
implementation is an internal domain and API foundation; it does not call
providers, does not execute `lotus-ai` runtime workflows, does not persist
durable AI lineage, and does not promote AI-assisted explanation as a supported
feature.

## Current Implementation

RFC-0002 Slice 09 adds `src/app/domain/ai_governance.py`,
`src/app/application/ai_governance.py`, and
`src/app/api/ai_governance.py` with:

1. redacted evidence envelopes for `lotus-ai` workflow-pack requests,
2. approved metadata validation that rejects portfolio, client, raw prompt,
   raw provider output, route, correlation, and trace identifiers,
3. deterministic fallback records for AI-unavailable posture,
4. verifier outcomes for unsupported claims and forbidden actions,
5. safe audit events for AI explanation evaluation,
6. explicit no-downstream-authority semantics for AI output,
7. a certified internal API foundation at
   `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`,
8. bounded operation telemetry through `ai_explanation` events with
   `accepted`, `fallback`, or `blocked` outcomes,
9. a certified internal operator diagnostic at
   `GET /api/v1/ai-explanations/readiness` that reports guardrail availability,
   `not_certified` supportability, and remaining certification blockers without
   invoking `lotus-ai` or exposing prompts, provider payloads, candidate
   identifiers, source routes, portfolio identifiers, or client identifiers.

The API preserves source authority: AI output cannot mutate candidate score,
lifecycle, source facts, review state, conversion state, or downstream workflow
authority. It returns redacted source refs without routes, raw prompts, provider
responses, trace ids, correlation ids, portfolio ids, client ids, request bodies,
or response bodies.

Successful API responses always return:

1. `durableStorageBacked=false`,
2. `lotusAiRuntimeExecuted=false`,
3. `supportedFeaturePromoted=false`,
4. `grantsDownstreamAuthority=false`.

The readiness diagnostic always returns:

1. `readinessStatus=blocked`,
2. `supportabilityStatus=not_certified`,
3. `certificationReady=false`,
4. `durableAiLineageStoreBacked=false`,
5. `lotusAiRuntimeExecuted=false`,
6. `supportedFeaturePromoted=false`.

It requires both the `operator` role and
`idea.ai-explanation.readiness.read` capability.

## Allowed Current Purposes

The internal domain model supports these bounded workflow purposes:

1. missing-evidence checking,
2. unsupported-claim verification,
3. advisor rationale drafting when evidence is ready and the candidate is
   review-ready,
4. meeting-preparation drafting when evidence is ready and the candidate is
   review-ready.

Runtime execution through `lotus-ai` remains planned. `lotus-ai` owns provider
execution, prompt registry, RAG, evaluation, workflow-pack runtime, and AI
telemetry.

## API Behavior

The internal evaluator supports two modes:

1. **Deterministic fallback**: when no workflow output is supplied, the route
   returns a governed fallback explanation over persisted candidate evidence
   and emits a `fallback` operation event.
2. **Verifier evaluation**: when workflow output is supplied, the route checks
   that every claim references source products already present in the redacted
   evidence envelope and that proposed actions are limited to advisor review or
   missing-evidence requests.

Unsupported claims and forbidden actions return `200` with a blocked posture
because the verifier successfully evaluated and rejected the output. Missing
candidates, permission failures, invalid request shape, forbidden metadata, and
invalid candidate lifecycle posture return product-safe Problem Details.

## Prohibited Behavior

AI output must not:

1. create final investment recommendations,
2. approve suitability, compliance, mandate, product eligibility, or trade
   execution,
3. create orders or client communications,
4. expose raw prompts or raw provider responses,
5. introduce unsupported source claims,
6. override deterministic evidence, score, lifecycle, review, or conversion
   state.

## Governance References

The current model-risk posture is aligned to:

1. NIST AI Risk Management Framework and Generative AI Profile,
2. MAS FEAT principles for financial-sector AI/data analytics,
3. 2026 OCC/Federal Reserve/FDIC revised model-risk management guidance,
4. `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`.

These references shape controls only. Product truth is the implementation,
tests, RFC evidence, supported-feature ledger, CI, and published wiki source.

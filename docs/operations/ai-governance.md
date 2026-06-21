# AI Governance And Model-Risk Posture

`lotus-idea` uses AI only as a governed assistance layer. The current
implementation is an internal domain foundation; it does not call providers,
does not expose AI APIs, and does not promote AI-assisted explanation as a
supported feature.

## Current Implementation

RFC-0002 Slice 09 adds `src/app/domain/ai_governance.py` with:

1. redacted evidence envelopes for `lotus-ai` workflow-pack requests,
2. approved metadata validation that rejects portfolio, client, raw prompt,
   raw provider output, route, correlation, and trace identifiers,
3. deterministic fallback records for AI-unavailable posture,
4. verifier outcomes for unsupported claims and forbidden actions,
5. safe audit events for AI explanation evaluation,
6. explicit no-downstream-authority semantics for AI output.

The module preserves source authority: AI output cannot mutate candidate score,
lifecycle, source facts, review state, conversion state, or downstream
workflow authority.

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

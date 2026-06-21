# RFC-0002 Slice 09: Governed AI Explanation And Model-Risk Controls

Status: Planned

## Outcome

Add AI-assisted explanations through `lotus-ai` without weakening deterministic
evidence, review, or source-authority controls.

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

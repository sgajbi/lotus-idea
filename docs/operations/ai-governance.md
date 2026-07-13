# AI Governance And Model-Risk Posture

`lotus-idea` uses AI only as a governed assistance layer. The current
implementation is an internal domain and API foundation; it does not call
providers, does not execute `lotus-ai` runtime workflows, and does not promote
AI-assisted explanation as a supported feature. The evaluator now records
source-safe lineage through the repository port behind API `Idempotency-Key`
replay/conflict protection; when PostgreSQL is configured that lineage is
stored durably. The repo now also carries certified source-safe model-risk
operations dashboard and alert artifacts over
implemented AI explanation telemetry. None of this is certified `lotus-ai`
runtime lineage, live-provider execution, Workbench product proof, or
supported-feature promotion.

It can verify a signed Lotus AI workflow-run attestation supplied with
producer output, bind that output to the exact Idea request, and persist a
bounded verification receipt. This does not make Idea the AI runtime owner.

An attested result may also include a separately signed Lotus AI
provider-retention confirmation. Idea binds it to the verified run, candidate
tenant, provider, provider mode, model, and model version and persists only a
bounded receipt in the same lineage transaction. Prompts, outputs, client
identifiers, and provider secrets are excluded; `PROVIDER_FAILURE` remains
blocked posture and never becomes deletion proof.

This receipt does not grant legal/privacy lifecycle authority, Report policy
authority, Archive posture, suitability, advice, execution, or client
publication. Validate the consumer boundary with
`make ai-provider-retention-contract-gate`.

The provider-retention producer and consumer foundations are merged and
mainline-proven at Lotus AI `51a8e8e` (run `29179866214`) and Lotus Idea
`f496c442` (run `29179489433`). This proves contract delivery, signature and
replay controls, and CI posture only. Provider-native evidence, managed-key and
production-store proof, and bank privacy/outsourcing/model-risk approval remain
required before certification.

## Current Implementation

RFC-0002 Slice 09 adds `src/app/domain/ai_governance.py`,
`src/app/application/ai_governance.py`, and
`src/app/api/ai_governance.py` with:

1. redacted evidence envelopes for `lotus-ai` workflow-pack requests,
2. a single governed workflow-pack contract that accepts public request
   identity `lotus-ai:idea-explanation:v1`, version `v1`, and evaluator
   `lotus-ai:governed-verifier:v1`, deliberately mapped to proof identity
   `idea_explanation.pack@v1`,
3. product-safe fail-closed rejection of unregistered workflow-pack identity
   before candidate lookup or lineage persistence,
4. `lotus-idea.ai-metadata-envelope.v1`, a closed, purpose-scoped metadata
   allowlist that accepts only code-owned operational routing values and
   rejects unknown fields or values before candidate lookup or lineage writes,
5. deterministic fallback records for AI-unavailable posture,
6. verifier outcomes for unsupported claims and forbidden actions,
7. safe audit events for AI explanation evaluation,
8. explicit no-downstream-authority semantics for AI output,
9. a certified internal API foundation at
   `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`,
10. required API `Idempotency-Key` validation for lineage writes with same-key
   replay, same-key conflict, and preserved domain request-id replay/conflict,
11. source-safe lineage persistence for request id, candidate id, evidence
   packet id, evidence content hash, workflow-pack identity, posture, verifier
   outcome, fallback state, reason codes, output summary ids, actor, timestamps,
   and no-downstream-authority posture,
12. bounded operation telemetry through `ai_explanation` events with
   `accepted`, `fallback`, or `blocked` outcomes,
13. a certified internal operator diagnostic at
   `GET /api/v1/ai-explanations/readiness` that reports guardrail availability,
   `not_certified` supportability, and remaining certification blockers without
   invoking `lotus-ai` or exposing prompts, provider payloads, candidate
   identifiers, source routes, portfolio identifiers, or client identifiers.
14. a versioned deterministic proposed-action policy that treats provider
    labels as untrusted, validates both the action enum and normalized label
    content, and replaces every accepted label with server-owned canonical
    wording.
15. versioned output-content integrity that commits to ordered explanation,
    claim, action, workflow/evaluator, and policy content without persisting
    unrestricted provider-authored text.
16. `lotus-idea.ai-execution-provenance-policy.v1`, which allows explicitly
    unattested workflow fixtures only in local/test and rejects workflow output
    in demo, staging, and production until a verified Lotus AI attestation is
    available.
17. evaluation and readiness responses that expose
    `metadataEnvelopeVersion=lotus-idea.ai-metadata-envelope.v1` so consumers
    can verify the active boundary contract.
18. exact Lotus AI producer wire contracts, Ed25519 verification, fixed-path
    signing-key discovery, deterministic input/output digest binding, and
    issuer, audience, workflow, evaluator, model-risk, and time validation.
19. durable replay protection over producer run id and replay nonce, including
    PostgreSQL partial unique indexes and reconstruction after restart.
20. bounded provenance telemetry that excludes signatures, keys, run ids,
    prompts, model content, and client data.

The API preserves source authority: AI output cannot mutate candidate score,
lifecycle, source facts, review state, conversion state, or downstream workflow
authority. It returns redacted source refs without routes, raw prompts, provider
responses, trace ids, correlation ids, portfolio ids, client ids, request bodies,
or response bodies.

Successful API responses always return:

1. `aiLineageRecorded=true` when source-safe lineage was accepted or replayed,
2. `aiLineagePersistenceDecision=accepted|replayed`,
3. `durableStorageBacked=false` only for allowed `local`/`test` process-local
   writes and `true` when the active repository provider is PostgreSQL,
4. `lotusAiRuntimeExecuted=true` only for cryptographically verified,
   request-bound producer execution; fallback and local fixtures remain `false`,
5. `supportedFeaturePromoted=false`,
6. `grantsDownstreamAuthority=false`.

The readiness diagnostic always returns:

1. `readinessStatus=blocked`,
2. `supportabilityStatus=not_certified`,
3. `certificationReady=false`,
4. `durableAiLineageStoreBacked=false` only for allowed `local`/`test`
   diagnostics and `true` when the active repository provider reports durable
   storage,
5. `lotusAiRuntimeExecuted=false`,
6. `supportedFeaturePromoted=false`.
7. `actionContentPolicyVersion=lotus-idea.ai-action-content-policy.v1`.
8. `metadataEnvelopeVersion=lotus-idea.ai-metadata-envelope.v1`.
9. `lotusAiRunAttestationAvailable=true`; producer and consumer mainline
   contract proof is complete, while live runtime execution and the other
   certification blockers remain explicit.

## Provider-Safe Metadata Envelope

Metadata is operational routing data, not an extension point for client or
portfolio context. The API schema is closed and the domain policy revalidates
the mapped request before application orchestration proceeds.

| Field | Allowed value | Allowed workflow purposes |
| --- | --- | --- |
| `channel` | `advisor-workbench` | All four governed purposes |
| `audience` | `internal_advisor_review` | Advisor-rationale and meeting-preparation drafts only |

The envelope permits at most two fields, limits key/value lengths, and rejects
untrimmed or control-character content. Unknown keys and unapproved values
return product-safe `400 invalid_ai_metadata`; API shape errors return the
standard product-safe `400 invalid_request`. Neither path echoes submitted
values. Lineage retains only sorted approved field names, never values.

Local/test fixture policy does not broaden this envelope. Future `lotus-ai`
integration may forward only the validated envelope and must not receive the
original request mapping. This is an internal design boundary in the existing
service; no workload, isolation, ownership, or operability evidence justifies
another runtime process.

## Proposed-Action Content Policy

An allowed action enum is necessary but not sufficient. Provider-authored text
can hide execution, approval, recommendation-publication, or client-contact
instructions behind an otherwise allowed enum. The policy in
`src/app/domain/ai_action_policy.py` therefore applies before claim
verification and fails closed.

| Decision | Result |
| --- | --- |
| Allowed enum and canonical safe intent | Accept the action and return a server-owned canonical label. |
| Execution, rebalance, approval, final-recommendation, publication, or client-communication directive | Block with `forbidden_action_content`. |
| Structurally forbidden enum | Block with `forbidden_action_type`. |
| Oversized, unsupported-script, or non-canonical ambiguous content | Block with `ambiguous_action_content`. |

Rejected raw labels are neither returned nor persisted. Audit and lineage use
bounded reason codes and the policy version, preserving replay identity without
retaining adversarial content. Normalization covers case, punctuation, Unicode
compatibility forms, and common character substitution; unsupported scripts
fail closed rather than relying on incomplete multilingual keyword lists.

It also returns explicit model-risk operations posture:

| Field | Current value | Meaning |
| --- | --- | --- |
| `modelRiskOperationsContractAvailable` | `true` | A repo-owned model-risk operations contract exists and is validated by `make ai-model-risk-ops-contract-gate`. |
| `modelRiskDashboardContractAvailable` | `true` | Dashboard control requirements are declared for implemented AI explanation/readiness telemetry. |
| `modelRiskAlertContractAvailable` | `true` | Alert candidate requirements are declared for implemented AI explanation/readiness telemetry. |
| `modelRiskDashboardCertified` | `true` | The repo-owned Grafana dashboard references only implemented, bounded AI explanation telemetry. |
| `modelRiskAlertCertified` | `true` | The repo-owned Prometheus alert rules reference only implemented, bounded AI explanation telemetry and runbook anchors. |

It requires both the `operator` role and
`idea.ai-explanation.readiness.read` capability.

## Model-Risk Operations Contract

`contracts/observability/lotus-idea-ai-model-risk-operations.v1.json` defines
the current operating contract for AI explanation supportability. It maps
implemented telemetry and endpoints to certified source-safe dashboard controls
and alert rules.

| Control | Implemented source | Current certification |
| --- | --- | --- |
| AI explanation readiness posture | `GET /api/v1/ai-explanations/readiness`, `ai_explanation_readiness_read` events | `certified` |
| AI output verifier posture | `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`, `ai_explanation` events | `certified` |
| AI lineage durability posture | `durable_storage_backed` telemetry label and readiness response | `certified` |

The contract is validated by `make ai-model-risk-ops-contract-gate`, which
blocks sensitive labels, unowned operations, missing source-of-truth paths, and
product-support overclaims. `make ai-model-risk-operations-proof-contract-gate`
certifies the dashboard, alert rules, and runbook artifacts. Passing these
gates is still not `lotus-ai` runtime proof, Workbench proof, data-mesh
certification, client-ready publication, or supported-feature promotion.

## Allowed Current Purposes

The internal domain model supports these bounded workflow purposes:

1. missing-evidence checking,
2. unsupported-claim verification,
3. advisor rationale drafting when evidence is ready and the candidate is
   review-ready,
4. meeting-preparation drafting when evidence is ready and the candidate is
   review-ready.

`lotus-ai` owns provider execution, prompt registry, RAG, evaluation,
workflow-pack runtime, signing keys, key rotation, model approvals, and AI
telemetry. `lotus-idea` owns deterministic evidence binding, verification
policy, replay protection, bounded receipt persistence, and human-review gates.

## Lineage Boundary

The current lineage record is an audit and replay foundation owned by
`lotus-idea`. It is intentionally source-safe and excludes raw prompts,
provider responses, source routes, trace ids, correlation ids, portfolio ids,
client ids, request bodies, response bodies, and free-form source payloads.

### Content Integrity

`lotus-idea.ai-output-integrity.v1` creates a deterministic SHA-256 commitment
for accepted, blocked, and fallback results. The canonical payload covers:

1. explanation text with Unicode NFC and line-ending normalization,
2. ordered claim identifiers, text, and source-product bindings,
3. ordered action types and submitted labels,
4. workflow-pack, evaluator, action-policy, verifier-policy, and fallback metadata.

Order and whitespace remain meaningful. The lineage store retains only the
integrity version and digest, then includes both in the wider lineage hash. The
evaluation API returns the same version and digest, so an authorized caller can
replay an exact governed request and verify content identity without invoking a
provider. Changed explanation text, claim text, action labels, ordering, or
policy metadata produces a distinct digest and a request-id conflict.

PostgreSQL stores the version/digest in dedicated columns and source-safe JSON.
Hydration fails closed when the column and JSON values diverge or when a v1
lineage hash no longer matches. Migration `010` marks records written before
this contract as `pre-v1-unverifiable`; it does not fabricate retroactive
content proof. AI lineage follows
`lotus-idea:regulated-advisory-evidence:seven-year:v1`, subject to legal hold,
erasure, and purge controls in the data-lifecycle contract.

`lotus-ai` remains the owner for runtime workflow execution, prompt registry,
RAG context construction, provider telemetry, evaluation telemetry, and
model-risk operating evidence. Durable repository-backed lineage persistence
is necessary proof, but it is not sufficient certification. The source-safe AI
lineage store proof can clear only the lineage-store blocker in aggregate proof
readiness. The readiness diagnostic therefore remains `not_certified` until
`lotus-ai` runtime execution, workflow-pack runtime certification, runtime
trust telemetry, and Workbench proof exist.

## API Behavior

The internal evaluator supports three modes:

1. **Deterministic fallback**: when no workflow output is supplied, the route
   returns a governed fallback explanation over persisted candidate evidence
   and emits a `fallback` operation event.
2. **Verifier evaluation**: when workflow output is supplied, the route checks
   that every claim references source products already present in the redacted
   evidence envelope and that proposed actions are limited to advisor review or
   missing-evidence requests.
3. **Attested producer evaluation**: producer run id, execution output, and
   signed attestation must be supplied together. The route verifies trusted
   Lotus AI keys and deterministic bindings before mapping output into the Idea
   verifier and atomically writing lineage plus the bounded receipt.

### Execution Provenance Boundary

Self-asserted workflow output is never production evidence.

| Runtime profile | Workflow output | Deterministic fallback |
| --- | --- | --- |
| `local`, `test` | Allowed only as `unattested_local_test_fixture`; cannot clear runtime proof. | Allowed. |
| `demo`, `staging`, `production` | Accepted only as a complete, verified Lotus AI producer bundle; otherwise rejected with product-safe `400 ai_execution_provenance_required` before lineage persistence. | Allowed. |

The evaluation response, audit attributes, and lineage record expose the bounded
provenance posture. Migration `011` marks existing records
`pre_attestation_unverifiable`; it does not infer that historical output came
from Lotus AI. Readiness reports the verifier as available and no longer reports
the completed mainline contract proof as missing. It remains blocked on live
Lotus AI runtime execution, certified lineage-store and runtime-trust proof,
workflow-pack runtime certification, and Workbench product proof.

The producer delivery was completed under `sgajbi/lotus-ai#113` at producer
main commit `162df803a7a835813dc17116be674842f12aa544`, with Main Releasability
run `29153879884`. The Idea consumer is mainline-proven through commit
`f496c4429178eaa5679767bc8f1c3102e17d5eb2` and run `29179489433`. Local source-safe
proof is generated with `make lotus-ai-attestation-contract-proof` and enforced
by `make lotus-ai-attestation-contract-proof-gate`. In isolated repository CI,
where the sibling producer checkout is unavailable, the gate validates only
lotus-idea-owned verification and replay controls; it does not attempt to
re-prove immutable GitHub mainline history. Supplying a producer checkout makes the same
gate require the complete cross-repository contract proof. It clears no
aggregate blocker because branch-local source inspection does not prove
live-provider rollout, Workbench behavior, or supported-feature promotion.
Idea does not own signing keys, provider
execution, model inventory, prompts, RAG, or AI runtime infrastructure.

Unsupported claims and forbidden action types or content return `200` with a blocked posture
because the verifier successfully evaluated and rejected the output. Missing
candidates, permission failures, invalid request shape, metadata outside the
provider-safe envelope, and
invalid candidate lifecycle posture return product-safe Problem Details.

The write route requires `Idempotency-Key`. Same-key/same-request submissions
replay without duplicate lineage records. Same-key/different-request
submissions return product-safe `409 idempotency_conflict`. Distinct-key
replays of the same AI request id still use the lineage store's request-id
replay/conflict guard, so API retry semantics and domain lineage identity do
not diverge.

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

# Security And Governance

`lotus-idea` must follow Lotus banking-grade governance.

This page summarizes current security and governance truth for internal
foundations. It is not a full external product security certification claim.

Current posture: caller-context, entitlement, idempotency, product-safe error,
operation-event, GitHub Security, and AI-governance foundations exist. Full
identity-provider integration, Workbench entitlement UX proof, client-ready
authorization certification, data-product certification, and supported-feature
promotion remain blocked.

## Governance Map

| Concern | Current control | Evidence |
| --- | --- | --- |
| Caller authorization | Role plus `idea.*` capability and trusted caller provenance. | `make caller-context-contract-gate` |
| Entitlement scope | Trusted tenant/book/portfolio/client headers bound to persisted candidate scope. | Review and feedback tests, API gates |
| Idempotency | Required `Idempotency-Key` and replay/conflict posture. | `make api-idempotency-boundary-gate` |
| Product-safe errors | RFC-7807 responses without raw source payloads or secrets. | `make api-problem-details-boundary-gate` |
| Observability | Governed operation metrics and source-safe logs. | `make source-observability-contract-gate`, `make operation-metric-contract-gate` |
| AI assistance | Deterministic evidence, workflow-pack allowlist, type-and-content action policy, canonical server-owned labels, verifier, lineage, and model-risk controls. | AI governance docs and gates |
| License and IP | Exact runtime/CI inventory, SPDX policy, conditional obligations, deterministic notices, expiring exceptions, and digest-bound release evidence. | `make license-compliance-gate` and the operator runbook |

## Signed Lotus AI Output

Idea accepts production-like AI explanation output only as a complete producer
bundle: producer run id, exact execution output, and signed Lotus AI run
attestation. It verifies trusted Ed25519 keys, issuer and audience,
workflow/evaluator/model-risk claims, validity times, and deterministic
input/output digests before domain mapping or lineage persistence.

| Owner | Responsibility |
| --- | --- |
| `lotus-ai` | Provider execution, model approval, attestation issuance, signing keys, and rotation. |
| `lotus-idea` | Evidence binding, signature verification, replay protection, bounded receipt persistence, and human review. |

For attested Idea explanations, an optional Lotus AI provider-retention
confirmation is verified against the same governed key discovery family and
bound to the candidate tenant plus verified run/provider/model identity before
atomic persistence. Confirmation, provider-reference, and nonce replay are
fenced. The posture remains `not_certified`; provider-native evidence,
managed-key/production-SQL proof, and bank approvals are still required.

Linked report evidence uses an independent Archive trust boundary. Idea accepts
only a strict signed `IdeaEvidenceLifecycleDecision` bound to exact Idea-owned
linkage, a maximum five-minute TTL, canonical SHA-256, and an active or rotated
Ed25519 key. Applied decision and digest replay are fenced durably. Archive hold
can block local action, but the receipt cannot authorize that action: signed
bank authority, tenant entitlement, dual approval, retention, and local state
remain mandatory. Raw documents, evidence content, and client identifiers are
excluded from the receipt and audit projection.

Run id and replay nonce are durable unique identities. Operation events expose
only bounded verification/rejection posture; they exclude signatures, keys,
run ids, prompts, provider payloads, and client data. The closed source contract
is enforced by `make ai-attestation-source-contract-gate`. It binds separate
Lotus AI producer and Idea consumer source collections to exact SHA-256 records
and canonical collection digests. Isolated CI validates an explicit
Idea-consumer-only non-proof posture; a supplied Lotus AI checkout activates
full cross-repository source validation. Neither scope proves provider/model
execution, model-risk approval, deployment, production certification,
Workbench behavior, publication, or support. Unknown fields and authority claim
inflation fail closed.

## License And IP Governance

`lotus-idea` service code is proprietary. The versioned compliance policy
classifies every resolved runtime and CI component and fails closed on lock
drift, unknown or denied licenses, missing conditional obligations, stale
notices, and incomplete exceptions. Exceptions require application-owner,
security, and legal approval, immutable evidence, and expiry.

Main Releasability binds policy version, lock hashes, NOTICE digest, SBOM
serial, exception IDs, and the final image digest in release evidence. The
container also carries `LICENSE` and `THIRD_PARTY_NOTICES.md`. Repository
`CODEOWNERS` routes review but does not replace legal or security authority;
base-image package inventory and external asset rights remain distinct review
boundaries. See
[operator runbook](https://github.com/sgajbi/lotus-idea/blob/main/docs/operations/license-ip-compliance.md)
for dependency changes, exceptions, escalation, and failure triage.

Day-one standard:

1. `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`

Required posture:

1. fail-closed entitlement checks,
2. no sensitive data in logs, metrics, docs, screenshots, or public evidence,
3. source refs and lineage on every material claim,
4. human review before conversion,
5. no autonomous advice, compliance approval, mandate approval, execution, or
   client communication,
6. AI through the governed `lotus-ai:idea-explanation:v1` workflow-pack
   contract only, mapped to proof identity `idea_explanation.pack@v1` and
   rejected with product-safe `invalid_ai_workflow_pack` when caller-supplied
   identity is unregistered,
7. endpoint certification and OpenAPI quality gates,
8. proposed data-product declarations, repo-native data-mesh contract gate,
   blocked static trust telemetry, source-safe runtime trust telemetry preview
   and snapshot evidence, and planned SLO/access/evidence policies before mesh
   promotion,
9. AST-backed monetary-float guard enforcement for money-like application
   fields and conversions,
10. production-like caller-context headers accepted only from trusted ingress,
11. branch protection and CI lane governance,
12. live GitHub Security posture verification through
    `make github-security-posture-check`.

GitHub Security posture:

1. Dependabot alerts/security updates, secret scanning with push protection,
   private vulnerability reporting, and CodeQL default setup for Python and
   GitHub Actions are required mutable repository settings,
2. CodeQL default setup uses the governed `default` query suite and `remote`
   threat model,
3. `make github-security-posture-check` verifies those settings and requires
   zero open code-scanning, secret-scanning, and Dependabot alerts,
4. the live check warns when `SECURITY.md` or `.github/dependabot.yml` are
   absent from the default branch that GitHub renders publicly, so unmerged
   branch truth is not mistaken for active Security-tab posture,
5. GitHub currently reports non-provider secret patterns and secret validity
   checks as disabled even after an admin API enable attempt, so they remain
   advisory future controls and are not release-evidence claims.
6. Main Releasability SBOM evidence is explicitly runtime-dependency scoped.
   `make release-sbom` inventories `requirements/runtime-resolved.lock.txt`
   with the pinned CycloneDX tool, and `release-evidence.json` ties that SBOM
   to the published service image reference, local image id, registry digest,
   keyless signature subject, and provenance/SBOM attestation URLs. Container OS
   package posture remains covered by the Trivy image scan, not by the runtime
   dependency SBOM. Images are pushed by CI only and must be promoted by digest,
   not rebuilt per environment. The `requirements/requirements.txt` mirror exists only to
   keep GitHub Dependency Graph updates parseable and is gated against the
   resolved runtime lock.
7. Dependabot Python updates use one grouped root-dependency stream. Routine
   version-update PRs are paused with `open-pull-requests-limit: 0` while RFC
   delivery is active; dependency suggestions are manually regenerated or
   cherry-picked into the active implementation branch before repo-native gates.
   Separate `/requirements` lock-only PRs are prohibited because they can strand
   lock truth away from root pins; `make dependency-refresh` regenerates both
   runtime lock files from the active closure before merge validation.

Mesh certification rule:

1. no `lotus-idea` product is certified from static declarations alone,
2. static trust telemetry must remain blocked until runtime implementation
   exists,
3. the repo-native data-mesh contract gate is pre-certification evidence only,
4. generated runtime telemetry snapshots are pre-certification evidence only,
5. platform source-manifest inclusion and certification gates are required
   before Gateway or Workbench expose the product as supported.

Caller-context governance:

1. `local` and `test` profiles may simulate caller subject, roles,
   capabilities, and entitlement scope through `X-Caller-*` headers for
   developer and automated-test ergonomics,
2. `demo`, `staging`, and `production` profiles reject those privileged
   headers unless the request also carries
   `X-Lotus-Trusted-Caller-Context` matching
   `LOTUS_IDEA_TRUSTED_CALLER_CONTEXT_TOKEN`,
3. the marker represents bounded trusted-ingress provenance only; it is not an
   identity-provider integration, signed assertion, mutual TLS service identity,
   Workbench entitlement proof, client-ready authorization certification, or
   supported-feature promotion,
4. `make caller-context-contract-gate` blocks route-local caller-header clones
   that fail to bind and forward the trusted marker.

`GET /api/v1/data-mesh/readiness` is the current internal operator diagnostic
for this posture. It requires the `operator` role and
`idea.mesh.readiness.read`, reports `not_certified` with explicit blockers, and
returns `supportedFeaturePromoted=false`. It is not data-product certification
or product discovery.
Its blockers are deliberately mapped to the platform promotion path:
source-manifest inclusion, catalog inclusion, SLO certification, access-policy
certification, evidence-policy certification, Gateway/Workbench discovery, and
supported-feature promotion.

`GET /api/v1/data-mesh/trust-telemetry/runtime-preview` is the current internal
operator diagnostic for pre-certification runtime telemetry preview. It
requires the `operator` role and
`idea.mesh.trust-telemetry.preview.read`, reports aggregate counts only, and
does not expose candidate identifiers, source routes, evidence hashes,
portfolio identifiers, client identifiers, platform source-manifest inclusion,
or product certification.
It now includes product coverage for every producer product declared in
`contracts/domain-data-products/lotus-idea-products.v1.json`, including
explicit `blocked_not_runtime_backed` posture where a declared product is not
independently materialized at runtime. This is coverage transparency, not data
mesh certification.

`make runtime-trust-telemetry-snapshot-check` emits the source-safe runtime
snapshot for `IdeaCandidate:v1` under ignored `output/trust-telemetry/runtime/`.
The snapshot includes the same product coverage posture and is contract-shaped
evidence for operators and CI, not product certification or supported-feature
promotion.
`GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot` exposes the same
contract-shaped posture as a certified internal operator diagnostic. It
requires the `operator` role and `idea.mesh.trust-telemetry.snapshot.read`,
reports blocked/not-certified posture, and must not expose candidate
identifiers, source routes, evidence hashes, portfolio identifiers, or client
identifiers.

`GET /api/v1/ai-explanations/readiness` is the current internal operator
diagnostic for AI explanation model-risk supportability. It requires both the
`operator` role and `idea.ai-explanation.readiness.read`, reports
`not_certified` blockers, and returns `supportedFeaturePromoted=false`. It does
not call `lotus-ai`, expose prompts or provider payloads, certify runtime AI
lineage, or create Gateway/Workbench support.

AI proposed-action labels are untrusted provider content. The versioned domain
policy validates the enum and normalized label before claim verification,
blocks execution, approval, final-recommendation, publication, and client-contact
directives, and fails closed on ambiguous or unsupported-script content.
Accepted actions use canonical server-owned labels. Rejected raw labels are not
returned, persisted, or copied into audit attributes; bounded policy reasons
and the policy version remain available for model-risk review and replay.

Every accepted, blocked, and fallback result also carries
`lotus-idea.ai-output-integrity.v1`. Its digest commits to ordered explanation,
claim, action, workflow/evaluator, and policy content. Only the digest and
version enter lineage and audit evidence; unrestricted provider text does not.
Exact governed replay verifies the digest without another provider call, while
changed content conflicts. PostgreSQL reload rejects column/JSON/hash mismatch,
and pre-v1 records remain explicitly unverifiable.

`lotus-idea.ai-execution-provenance-policy.v1` prevents self-asserted AI output
from crossing the production trust boundary. Local/test fixtures are visibly
unattested and cannot clear runtime proof. Demo, staging, and production reject
workflow output before candidate lookup or lineage persistence; deterministic
fallback remains available. Signed run/model attestation is producer-owned and
was completed under `lotus-ai#113`; Idea-side verification and replay fencing
are also mainline-proven. Readiness remains blocked on live runtime execution,
runtime trust, Workbench proof, and supported-feature promotion rather than a
missing attestation contract.

Provider-bound metadata is governed by
`lotus-idea.ai-metadata-envelope.v1`. The closed API schema and domain policy
allow only `channel=advisor-workbench` for governed workflows and
`audience=internal_advisor_review` for the two drafting purposes. Unknown,
oversized, untrimmed, control-character, or unapproved values fail before
candidate lookup or lineage persistence. Responses and lineage expose only the
policy version and approved field names; raw metadata values are not persisted
or logged. Local/test fixtures use the same envelope and cannot clear model-risk
or runtime-readiness blockers.

Operation-event governance:

1. high-cash, candidate persistence, candidate evidence replay, lifecycle,
   AI explanation, AI explanation readiness, advisor queue, review, feedback,
   conversion, and report evidence-pack foundation APIs emit bounded operation events for accepted,
   replayed, duplicate, suppressed, not-eligible, fallback, blocked, conflict,
   not-found, permission-denied, invalid-request, and invalid-state outcomes,
2. operation metrics use only bounded labels and keep identifiers, payloads,
   trace ids, and correlation ids out of metric labels,
3. operation events retain `foundation_only` supportability until durable
   persistence, downstream proof, Gateway/Workbench proof, and supported-feature
   promotion are completed.

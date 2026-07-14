# Data Mesh Readiness

Status: Planned data-mesh posture with internal readiness, runtime telemetry
preview, source-safe runtime snapshot diagnostics, repo-owned mesh policy
proof, and bounded platform source-manifest/catalog onboarding proof.

Certification status: not certified.

`lotus-idea` is a day-one data-mesh participant in design and repository
governance. It is not yet a certified data-mesh producer because business
runtime behavior is intentionally not implemented.

## Source Truth

1. Producer declarations:
   `contracts/domain-data-products/lotus-idea-products.v1.json`.
2. Consumer declarations:
   `contracts/domain-data-products/lotus-idea-consumers.v1.json`.
3. Mesh readiness posture:
   `contracts/domain-data-products/mesh-readiness.v1.json`.
4. Trust telemetry fallback:
   `contracts/trust-telemetry/idea-candidate.telemetry.v1.json`.
5. SLO, access, and evidence policies:
   `contracts/mesh-slo/`, `contracts/mesh-access/`, and
   `contracts/mesh-evidence/`.
6. Platform data mesh standard:
   `../../../lotus-platform/docs/standards/Lotus Data Mesh Standard.md` from the
   sibling checkout.

## Promotion Rule

Every `lotus-idea` product remains `proposed` until:

1. endpoint behavior is implemented and certified,
2. every source-owned input has provenance, freshness, and trust metadata,
3. runtime telemetry replaces static fallback evidence,
4. platform source-manifest inclusion and mesh certification pass,
5. Gateway and Workbench discovery expose only supported behavior,
6. README, repo context, supported features, RFC evidence, and wiki source are
   updated on `main`.

The static telemetry snapshot is deliberately blocked so operators and future
agents cannot treat the day-one contract baseline as runtime certification.
The runtime telemetry preview and generated snapshot described below are
implementation-backed diagnostic evidence, but they remain pre-certification
evidence until mesh certification, Gateway discovery, Workbench discovery, and
supported-feature promotion evidence exist. The platform catalog source-contract path
can validate source-manifest and catalog inclusion separately; that is catalog
visibility, not mesh certification.
The mesh policy source-contract path validates and digest-binds local readiness,
SLO, access, and evidence-pack policy declarations separately; that is source
provenance, not policy or platform-mesh certification.

The controlling platform standard is
[Lotus Data Mesh Standard](../../../lotus-platform/docs/standards/Lotus%20Data%20Mesh%20Standard.md).
`lotus-idea` follows it as a future-wave, catalog-visible onboarding participant
until runtime trust telemetry, policy, Gateway, Workbench, evidence, and
supported-feature proof are complete.

## Runtime Diagnostic

`GET /api/v1/data-mesh/readiness` returns the current repo-authored readiness
posture for internal operators. It requires:

1. `X-Caller-Roles: operator`
2. `X-Caller-Capabilities: idea.mesh.readiness.read`

The response includes:

1. `certificationStatus: not_certified`,
2. `runtimeTelemetryBacked: false`,
3. `platformCertified: false`,
4. `supportedFeaturePromoted: false`,
5. source-of-truth paths for the producer, consumer, telemetry, SLO, access,
   and evidence-policy contracts,
6. explicit blockers for certification and promotion.

This endpoint is endpoint-certified as an operator diagnostic. It is not data
product certification, platform source-manifest inclusion, Gateway discovery,
Workbench discovery, runtime lineage proof, or a supported-feature claim.
Its blocker list is intentionally aligned to the platform mesh certification
families so operators and future agents can see the exact missing promotion
proof: source-manifest inclusion, catalog inclusion, SLO certification, access
policy certification, evidence-policy certification, Gateway/Workbench
discovery proof, and supported-feature promotion.

`GET /api/v1/data-mesh/trust-telemetry/runtime-preview` returns aggregate
runtime telemetry preview posture from the active repository provider. It
requires:

1. `X-Caller-Roles: operator`
2. `X-Caller-Capabilities: idea.mesh.trust-telemetry.preview.read`

The response includes:

1. `productId: lotus-idea:IdeaCandidate:v1`,
2. aggregate candidate and source-reference counts,
3. source-authority, freshness, supportability, and lifecycle count maps,
4. aggregate review, feedback, conversion, and report evidence-pack counts,
5. `productCoverage` entries for every producer product declared in
   `contracts/domain-data-products/lotus-idea-products.v1.json`,
6. explicit `coverageStatus`, source-safe counts, lineage/materialization
   posture, consumer exposure posture, and certification blockers per product,
7. `runtimeTelemetryBacked: true` for the preview artifact,
8. `platformCertified: false`,
9. `certificationStatus: not_certified`,
10. explicit certification blockers.

Product coverage is intentionally explicit. `IdeaCandidate`,
`IdeaEvidencePacket`, `AdvisorOpportunityQueue`, workflow event products, and
`IdeaTrustTelemetry` have source-safe runtime posture derived from the active
repository snapshot. `OpportunitySignalCandidate` remains
`blocked_not_runtime_backed` until Lotus Idea independently materializes that
declared product. This coverage model is also recorded in
`contracts/trust-telemetry/lotus-idea-product-coverage.telemetry.v1.json`; data
mesh readiness reports
`runtime_trust_telemetry_product_coverage_incomplete` while coverage is not
complete.

The preview deliberately omits candidate identifiers, portfolio identifiers,
client identifiers, raw source routes, evidence hashes, request payloads, and
response payloads. It is endpoint-certified as an internal operator diagnostic,
not as data-product certification or product discovery.

`GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot` returns the same
contract-shaped runtime snapshot as an internal operator diagnostic. It
requires:

1. `X-Caller-Roles: operator`
2. `X-Caller-Capabilities: idea.mesh.trust-telemetry.snapshot.read`

The response preserves the platform trust-telemetry contract field names,
reports `blocking.blocked: true`, and uses aggregate active-repository state
only. It deliberately omits candidate identifiers, portfolio identifiers,
client identifiers, raw source routes, evidence hashes, request payloads, and
response payloads.

`make runtime-trust-telemetry-snapshot-check` writes the contract-shaped runtime
snapshot to:

```text
output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json
```

The endpoint and generated artifact use the same active repository provider as
the preview and emit platform-compatible trust telemetry fields for
`lotus-idea:IdeaCandidate:v1` plus a `product_coverage` section for every
declared producer product. They are source-safe and remain blocked with
explicit certification blockers. The generated file is ignored by Git. Neither
surface replaces the checked-in static fallback contract, promotes producer
products, or certifies the platform mesh.

`scripts/data_mesh/generate_platform_catalog_source_contract.py` reads sibling
`lotus-platform` source-manifest, generated catalog, dependency graph, maturity
matrix, and mesh handoff evidence. The v2 artifact is explicitly
`source_contract` evidence and binds the first four authority files by
repository, ref, and SHA-256. A valid, current artifact satisfies only
`platform_source_manifest_inclusion_missing` and
`platform_catalog_inclusion_missing` in aggregate readiness. It preserves
`data_mesh_not_certified`, `producer_products_not_active`,
SLO/access/evidence certification, Gateway/Workbench discovery, and
supported-feature blockers. Its closed-field validator also requires runtime
publication, deployment, production certification, and product-support claims
to remain absent or false.
`make implementation-proof-readiness-check` now generates this default proof
from `LOTUS_PLATFORM_ROOT=../lotus-platform` into ignored
`output/data-mesh/platform-catalog-source-contract.json` and consumes it in the
aggregate readiness artifact unless
`LOTUS_IDEA_PLATFORM_CATALOG_SOURCE_CONTRACT_PROOF` overrides the path. Missing
sibling platform evidence writes an invalid non-proof artifact and keeps the
blockers; drift in present sibling evidence remains a failing contract
condition.

`make runtime-trust-telemetry-proof-contract-gate` validates the separate
source-safe runtime trust telemetry proof contract used by aggregate
implementation readiness. The generated proof under ignored
`output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json` can clear
only the seeded candidate-snapshot blocker
`runtime_candidate_snapshot_missing` while declared product coverage remains
incomplete. Its product-coverage summary preserves
`runtime_trust_telemetry_product_coverage_incomplete`,
`certified_runtime_trust_telemetry_missing`, and
`data_mesh_runtime_telemetry_not_certified` until every declared producer
product has complete runtime coverage. It is not platform mesh certification
and does not promote `IdeaCandidate:v1` from proposed posture.

`scripts/data_mesh/generate_mesh_policy_source_contract.py` validates and
SHA-256 binds the repo-owned readiness, SLO, access, and evidence-pack policy
sources for `lotus-idea:IdeaCandidate:v1`. The artifact declares
`evidenceClass=source_contract`; it proves source presence and coherence, not
policy certification. A valid current artifact adds supporting evidence while
retaining these aggregate implementation-readiness blockers:

1. `mesh_slo_policy_certification_missing`,
2. `mesh_access_policy_certification_missing`,
3. `mesh_evidence_policy_certification_missing`.

`make implementation-proof-readiness-check` generates this default source
contract under ignored `output/data-mesh/mesh-policy-source-contract.json` and
consumes it unless `LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF` overrides the
path. It keeps `data_mesh_not_certified`,
`producer_products_not_active`, platform source-manifest/catalog,
Gateway/Workbench discovery, and supported-feature blockers intact.

The Docker image copies `contracts/` into `/app/contracts` so containerized
diagnostics read the same contract truth as local validation.

## Repo-Native Gate

Run:

```powershell
make data-mesh-contract-gate
make mesh-policy-source-contract-proof-gate
make platform-catalog-source-contract-proof-gate
make runtime-trust-telemetry-proof-contract-gate
make runtime-trust-telemetry-preview-check
make runtime-trust-telemetry-snapshot-check
```

The gate validates:

1. producer products remain `proposed`,
2. consumer dependencies name current source-authority repositories and
   products,
3. placeholder mesh files are absent from governed contract and operations
   paths,
4. static trust telemetry remains blocked and unknown,
5. SLO, access, and evidence policies stay coherent for
   `lotus-idea:IdeaCandidate:v1`,
6. optional sibling `lotus-platform` catalog/source-manifest evidence catches
   source-product drift and validates governed `lotus-idea` onboarding without
   treating catalog visibility as certification.
7. the runtime telemetry preview generator still emits source-safe
   not-certified evidence from the active repository provider.
8. the runtime telemetry snapshot endpoint and generator still emit
   contract-shaped, source-safe, blocked runtime snapshot evidence.
9. the mesh policy source contract remains source-safe, deterministic, and
   limited to supporting evidence while all SLO/access/evidence policy
   certification blockers remain.
10. the runtime telemetry proof contract remains source-safe, deterministic, and
   limited to clearing repo-owned runtime telemetry blockers.

This gate is not mesh certification. It is a pre-certification guardrail so
future implementation slices cannot accidentally promote proposed contracts or
consume non-governed source products.

## Current Consumer Source Map

The repo-local consumer declaration names the source-authority products needed
by the RFC-0002 first-wave map. The first high-cash / idle-liquidity journey
uses Core-owned portfolio state, holdings/cash balance, cash movement, and
cashflow projection evidence. Later first-wave families reference
Performance-owned returns and mandate performance health, Risk-owned risk
metrics and scenario/mandate risk posture, Advise-owned proposal/policy/copilot
records, Manage-owned action register posture, and Report-owned client report
evidence.

These dependencies are not runtime certification. They are the source-owner
contract skeleton that later implementation slices must consume through ports,
supportability handling, tests, and certification evidence.

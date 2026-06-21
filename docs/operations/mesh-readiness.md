# Data Mesh Readiness

Status: Planned data-mesh posture with an internal readiness diagnostic.

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

The Docker image copies `contracts/` into `/app/contracts` so containerized
diagnostics read the same contract truth as local validation.

## Repo-Native Gate

Run:

```powershell
make data-mesh-contract-gate
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
   source-product drift or premature `lotus-idea` source-manifest inclusion.

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

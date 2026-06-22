# RFC-0002 Slice 14: Data Product Promotion, Trust Telemetry, And Platform Hardening

Status: Partially implemented - internal not-certified mesh readiness, runtime telemetry preview, and source-safe runtime snapshot diagnostics

## Outcome

Promote only implemented `lotus-idea` products into the Lotus data mesh and
platform trust plane. This slice must prove `lotus-idea` is a real governed
data product producer, not only an API service with planned metadata.

## Current Implementation Evidence

This slice now has internal operator diagnostic foundations only:

1. `src/app/application/data_mesh_readiness.py` reads repo-owned producer,
   mesh-readiness, and trust-telemetry contracts and builds a closed
   `planned` / `not_certified` readiness snapshot.
2. `GET /api/v1/data-mesh/readiness` exposes that snapshot to callers with the
   `operator` role and `idea.mesh.readiness.read` capability.
3. The endpoint returns explicit blockers:
   `data_mesh_not_certified`, `producer_products_not_active`, and
   `certified_runtime_trust_telemetry_missing`.
4. The endpoint returns `runtimeTelemetryBacked=false`,
   `platformCertified=false`, and `supportedFeaturePromoted=false`.
5. The endpoint emits a bounded `mesh_readiness_read` operation event with
   `not_certified` supportability and no sensitive labels.
6. `Dockerfile` copies `contracts/` into the runtime image so containerized
   diagnostics use the same repo-authored contract truth as local validation.
7. `docs/operations/endpoint-certification-ledger.json` certifies the endpoint
   as an internal diagnostic operation, not as mesh certification.
8. `src/app/application/runtime_trust_telemetry.py` builds a source-safe
   runtime trust telemetry preview from the active repository snapshot.
9. `GET /api/v1/data-mesh/trust-telemetry/runtime-preview` exposes aggregate
   candidate, source-authority, freshness, supportability, lifecycle, review,
   feedback, conversion, and report evidence-pack counts to callers with the
   `operator` role and `idea.mesh.trust-telemetry.preview.read` capability.
10. `scripts/generate_runtime_trust_telemetry_preview.py` and
    `make runtime-trust-telemetry-preview-check` generate the same
    pre-certification preview as source-safe automation evidence.
11. The preview returns `runtimeTelemetryBacked=true` for the diagnostic
    artifact while preserving `certificationStatus=not_certified`,
    `platformCertified=false`, `certificationReady=false`, and
    `supportedFeaturePromoted=false`.
12. `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot` exposes the same
    contract-shaped runtime trust telemetry snapshot to callers with the
    `operator` role and `idea.mesh.trust-telemetry.snapshot.read` capability.
13. `scripts/generate_runtime_trust_telemetry_snapshot.py` and
    `make runtime-trust-telemetry-snapshot-check` generate a contract-shaped
    runtime trust telemetry snapshot under ignored
    `output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json`.
14. The endpoint and generated snapshot use platform trust telemetry fields for
    `lotus-idea:IdeaCandidate:v1`, remain blocked, and omit candidate ids,
    portfolio ids, client ids, raw source routes, and raw evidence hashes.

Evidence:

1. `tests/unit/test_data_mesh_readiness.py`
2. `tests/integration/test_data_mesh_readiness_api.py`
3. `tests/unit/test_runtime_trust_telemetry.py`
4. `tests/integration/test_runtime_trust_telemetry_api.py`
5. `scripts/generate_runtime_trust_telemetry_preview.py`
6. `scripts/generate_runtime_trust_telemetry_snapshot.py`
7. `tests/unit/test_generate_runtime_trust_telemetry_snapshot.py`
8. `scripts/endpoint_certification_gate.py`
9. `scripts/openapi_quality_gate.py`

## Current Non-Goals

1. No producer product is promoted from `proposed`.
2. No platform source-manifest inclusion is claimed.
3. No runtime trust telemetry preview, runtime snapshot endpoint, or generated
   runtime snapshot replaces the blocked static fallback for platform
   certification.
4. No Gateway or Workbench discovery contract is created.
5. No supported feature is promoted.

## Required Work

1. Promote implemented producer products from `proposed` to implementation-backed
   repo-native declarations.
2. Replace blocked static trust telemetry with current runtime trust telemetry
   and certification evidence.
3. Promote SLO, access, freshness, evidence, compatibility, and supportability
   policies from planned posture to certification inputs.
4. Update platform catalogs and validators where required.
5. Verify every active producer product has source authority, schema validation,
   lineage, owner, consumer contract, freshness/completeness posture,
   support runbook, access policy, and supported-feature evidence.
6. Verify downstream consumers use certified `lotus-idea` endpoints and do not
   reconstruct idea truth locally.
7. Review API posture, OpenAPI quality, metadata quality, discoverability,
   dependency hygiene, vulnerability posture, CI coverage, Docker readiness,
   and production guardrails.
8. If contract cleanup requires breaking changes, update every affected
   downstream Lotus consumer inside RFC-0002 before product promotion.
9. Record reusable platform or scaffold gaps as platform changes, not local
   `lotus-idea` exceptions.

## Remaining Gap

The diagnostic endpoints deliberately report blocked / not-certified posture.
The runtime telemetry preview, runtime snapshot endpoint, and generated
snapshot are implementation-backed pre-certification evidence, but they do not
activate producer declarations or replace the blocked static fallback for
platform mesh certification. Full Slice
14 completion still requires implementation-backed active product declarations,
platform catalog/source-manifest inclusion, Gateway/Workbench discovery proof,
certified consumer contracts, platform mesh certification, and supported-feature
evidence. Until those exist, `lotus-idea` remains a planned data-mesh
producer/consumer with repo-native anti-drift controls and source-safe runtime
telemetry evidence only.

## Acceptance Gate

1. No proposed product is marked active before implementation proof.
2. Platform aggregation and certification pass.
3. `/platform/capabilities` or equivalent product discovery reflects only
   supported behavior.
4. Consumer dependencies remain explicit and certified.
5. Data-mesh validation proves owner contract, source authority, consumer
   contract, lineage, freshness/completeness, SLO/access policy, runtime trust
   telemetry, and supportability evidence for every promoted product.
6. CI, dependency, security, Docker, API certification, OpenAPI, and platform
   governance checks pass or have explicit accepted-risk treatment.
7. Every platform/scaffold improvement discovered during the slice is either
   implemented in `lotus-platform` or recorded as an explicit blocked state with
   owner, risk, and closure condition.

## Current Acceptance Status

1. Gate 1 is preserved: no proposed product is marked active.
2. Gates 2 through 5 remain blocked pending platform and runtime mesh
   certification.
3. Gate 6 is partially satisfied for the diagnostic endpoints and generated
   runtime evidence through OpenAPI, endpoint-certification, runtime-preview
   endpoint/generator, runtime-snapshot endpoint/generator, and
   unit/integration evidence.
4. Gate 7 has no new platform/scaffold blocker from this diagnostic slice.

# RFC-0002 Slice 14: Data Product Promotion, Trust Telemetry, And Platform Hardening

Status: Partially implemented - internal not-certified mesh readiness diagnostic only

## Outcome

Promote only implemented `lotus-idea` products into the Lotus data mesh and
platform trust plane. This slice must prove `lotus-idea` is a real governed
data product producer, not only an API service with planned metadata.

## Current Implementation Evidence

This slice now has an internal operator diagnostic foundation only:

1. `src/app/application/data_mesh_readiness.py` reads repo-owned producer,
   mesh-readiness, and trust-telemetry contracts and builds a closed
   `planned` / `not_certified` readiness snapshot.
2. `GET /api/v1/data-mesh/readiness` exposes that snapshot to callers with the
   `operator` role and `idea.mesh.readiness.read` capability.
3. The endpoint returns explicit blockers:
   `data_mesh_not_certified`, `producer_products_not_active`, and
   `runtime_trust_telemetry_blocked`.
4. The endpoint returns `runtimeTelemetryBacked=false`,
   `platformCertified=false`, and `supportedFeaturePromoted=false`.
5. The endpoint emits a bounded `mesh_readiness_read` operation event with
   `not_certified` supportability and no sensitive labels.
6. `Dockerfile` copies `contracts/` into the runtime image so containerized
   diagnostics use the same repo-authored contract truth as local validation.
7. `docs/operations/endpoint-certification-ledger.json` certifies the endpoint
   as an internal diagnostic operation, not as mesh certification.

Evidence:

1. `tests/unit/test_data_mesh_readiness.py`
2. `tests/integration/test_data_mesh_readiness_api.py`
3. `scripts/endpoint_certification_gate.py`
4. `scripts/openapi_quality_gate.py`

## Current Non-Goals

1. No producer product is promoted from `proposed`.
2. No platform source-manifest inclusion is claimed.
3. No runtime trust telemetry replaces the blocked static fallback.
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

The diagnostic endpoint deliberately reports blocked posture. Full Slice 14
completion still requires implementation-backed product declarations, runtime
trust telemetry, platform catalog/source-manifest inclusion, Gateway/Workbench
discovery proof, certified consumer contracts, and supported-feature evidence.
Until those exist, `lotus-idea` remains a planned data-mesh producer/consumer
with repo-native anti-drift controls only.

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
3. Gate 6 is partially satisfied for the diagnostic endpoint through OpenAPI
   and endpoint-certification evidence.
4. Gate 7 has no new platform/scaffold blocker from this diagnostic slice.

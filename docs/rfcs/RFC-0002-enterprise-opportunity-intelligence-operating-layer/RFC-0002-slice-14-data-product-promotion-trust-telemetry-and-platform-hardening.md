# RFC-0002 Slice 14: Data Product Promotion, Trust Telemetry, And Platform Hardening

Status: Planned

## Outcome

Promote only implemented `lotus-idea` products into the Lotus data mesh and
platform trust plane. This slice must prove `lotus-idea` is a real governed
data product producer, not only an API service with planned metadata.

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

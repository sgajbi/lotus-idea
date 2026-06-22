# Security And Governance

`lotus-idea` must follow Lotus banking-grade governance.

Day-one standard:

1. `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`

Required posture:

1. fail-closed entitlement checks,
2. no sensitive data in logs, metrics, docs, screenshots, or public evidence,
3. source refs and lineage on every material claim,
4. human review before conversion,
5. no autonomous advice, compliance approval, mandate approval, execution, or
   client communication,
6. AI through `lotus-ai` workflow packs only,
7. endpoint certification and OpenAPI quality gates,
8. proposed data-product declarations, repo-native data-mesh contract gate,
   blocked static trust telemetry, and planned SLO/access/evidence policies
   before mesh promotion,
9. AST-backed monetary-float guard enforcement for money-like application
   fields and conversions,
10. branch protection and CI lane governance.

Mesh certification rule:

1. no `lotus-idea` product is certified from static declarations alone,
2. static trust telemetry must remain blocked until runtime implementation
   exists,
3. the repo-native data-mesh contract gate is pre-certification evidence only,
4. platform source-manifest inclusion and certification gates are required
   before Gateway or Workbench expose the product as supported.

`GET /api/v1/data-mesh/readiness` is the current internal operator diagnostic
for this posture. It requires the `operator` role and
`idea.mesh.readiness.read`, reports `not_certified` with explicit blockers, and
returns `supportedFeaturePromoted=false`. It is not data-product certification
or product discovery.

Operation-event governance:

1. high-cash, candidate persistence, candidate evidence replay, lifecycle,
   AI explanation, advisor queue, review, feedback, conversion, and report
   evidence-pack foundation APIs emit bounded operation events for accepted,
   replayed, duplicate, suppressed, not-eligible, fallback, blocked, conflict,
   not-found, permission-denied, invalid-request, and invalid-state outcomes,
2. operation metrics use only bounded labels and keep identifiers, payloads,
   trace ids, and correlation ids out of metric labels,
3. operation events retain `foundation_only` supportability until durable
   persistence, downstream proof, Gateway/Workbench proof, and supported-feature
   promotion are completed.

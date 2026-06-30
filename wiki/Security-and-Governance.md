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
   blocked static trust telemetry, source-safe runtime trust telemetry preview
   and snapshot evidence, and planned SLO/access/evidence policies before mesh
   promotion,
9. AST-backed monetary-float guard enforcement for money-like application
   fields and conversions,
10. branch protection and CI lane governance,
11. live GitHub Security posture verification through
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

Mesh certification rule:

1. no `lotus-idea` product is certified from static declarations alone,
2. static trust telemetry must remain blocked until runtime implementation
   exists,
3. the repo-native data-mesh contract gate is pre-certification evidence only,
4. generated runtime telemetry snapshots are pre-certification evidence only,
5. platform source-manifest inclusion and certification gates are required
   before Gateway or Workbench expose the product as supported.

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

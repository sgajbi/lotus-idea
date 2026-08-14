# Validation And CI

This page explains which checks to run, what each lane proves, and where the
gate details live. `lotus-idea` has many implementation-backed contract gates;
the structure below keeps the decision path separate from the detailed
evidence inventory.

Current summary: branch or PR success is necessary but not sufficient for
durable RFC/docs/wiki/support closure. Release truth requires merge to `main`,
green mainline checks, synchronized docs/wiki/context/support posture, and
clean branch hygiene.

## Quick Decision Map

| Situation | Run | Result needed |
| --- | --- | --- |
| Small code or docs edit | `make lint`, focused tests | Fast local proof before commit. |
| API contract change | `make openapi-gate`, `make endpoint-certification-gate`, focused API tests | Runtime/OpenAPI/certification agreement. |
| Supported-feature claim | `make supported-features-gate`, `make implementation-truth-gate`, `make implementation-proof-closure-manifest-gate`, `make blueprint-scope-coverage-gate` | No unproved support or certification language; every proof blocker and blueprint capability has issue, evidence, slice, and non-promotion truth. |
| Dependency or container vulnerability posture change | `make dependency-vulnerability-posture-gate`, `make security-audit`, release lane for image scan/SBOM/signing/provenance | Exact stable runtime, CI, and build-system dependency pins; lock mirror truth; governed Python vulnerability audit; Trivy/release hook wiring; issue-backed exceptions; and platform exception-register linkage. |
| Persistence or migration change | `make migration-contract-gate`, `make migration-execution-gate`, focused repository tests | Apply/rollback and query-shape proof. |
| PostgreSQL recovery change | `make disaster-recovery-contract-gate`, real restore/resume proof, `make disaster-recovery-proof-gate` | RPO/RTO, restored invariants, replay/fencing, and no-mutation evidence. |
| Canonical source-proof run | `make canonical-opportunity-source-proofs` with governed runtime arguments | Source-specific live evidence, traceability, and fail-closed blocker posture. |
| Lotus AI runtime proof | `python scripts/generate_ai_workflow_pack_runtime_execution_proof.py --generated-at-utc <utc> --lotus-ai-base-url <lotus-ai-base-url> --output output/ai/ai-workflow-pack-runtime-execution-proof.json` | Actual review-gated `idea_explanation.pack@v1` execution and a source-safe receipt whose completion time is not after proof `generatedAtUtc`; live provider remains blocked. |
| AI lineage-store certification | Main Releasability `make postgres-integration-gate`, then `make ai-lineage-store-ci-proof` | Exact-main PostgreSQL behavior, uploaded test-artifact digest, and a closed CI execution receipt; no live-provider or supported-feature claim. |
| Durable repository CI proof | Main Releasability `make postgres-integration-gate`, then `make durable-repository-ci-proof` | Exact-main migration, persistence/replay, concurrency/audit/outbox, and repository-side pagination assertions bound to the uploaded test artifact. |
| Release-grade local proof | `make ci-release` | Full local release evidence. |
| Wiki source change | wiki audit, wiki check-only, publish after merge | Repo source and published wiki agree. |

`lotus-idea` starts with the Lotus backend lane model:

1. Feature Lane for branch feedback.
2. PR Merge Gate for required merge readiness.
3. Main Releasability Gate for post-merge truth.
4. Merged PR Main Releasability Dispatch as the authoritative post-merge
   trigger, with manual reruns through `workflow_dispatch`; the gate does not
   also run on `push` to `main`, avoiding expected cancelled duplicate runs.
5. Non-suppressed auto-merge token enforcement through `LOTUS_AUTOMERGE_TOKEN`;
   without that secret, the helper warns, skips auto-merge, and requires a
   human/release actor to rebase merge.

## Gate Map

| Lane | Main proof | What it protects |
| --- | --- | --- |
| Feature Lane | Fast lint, typecheck, unit, action lint | Branch feedback without write permissions |
| PR Merge Gate | Integration, coverage, Docker, PostgreSQL, security | Merge readiness and runtime parity |
| Main Releasability | Release evidence, SBOM, Docker, PostgreSQL | Post-merge truth on `main` |
| Protected deployment migration | Exact signed digest, release-bound PostgreSQL history, source-safe attested evidence | Controlled schema change eligibility; not rollout certification by itself |
| Scheduled PostgreSQL DR | Real logical backup/restore, resume proof, evidence attestation | Weekly recovery regression detection; not provider PITR certification |
| Local contract gates | Makefile, docs, source safety, mesh, endpoint certification | Future-agent drift and unsupported claims |

### Evidence Classes

Proof consumers distinguish source contracts, test execution, CI execution,
runtime execution, deployment, and production certification. A lower class
cannot clear a blocker owned by a higher class. In particular, source files,
Make targets, and workflow text cannot prove that a test ran successfully.

AI lineage-store certification requires the closed
`lotus-idea.ai-lineage-store-ci-execution-receipt.v1` receipt. It binds the
trusted repository, workflow, PostgreSQL job, run id and attempt, exact main
commit and ref, successful conclusion, uploaded artifact SHA-256, and the exact
lineage persistence assertion. The aggregate proof remains blocked when the
receipt is absent, malformed, or inconsistent.

Durable repository proof follows the same evidence class without sharing AI
policy. Its persistence-specific receipt is derived from governed PostgreSQL
JUnit cases and must match the trusted mainline workflow/job, exact commit and
main ref, run identity, successful conclusion, artifact digest, proof time, and
complete assertion set. Source files, Make targets, PR runs, stale receipts,
or a named CI lane cannot clear the two persistence blockers. Production
database deployment and supported-feature promotion remain separate.

Deployment-migration repository controls merged through PR `#373`. Exact-main
Main Releasability run `29261043056` and CodeQL run `29261035371` passed on
`6ba9618a`; release evidence binds the signed and attested image digest to its
SHA tag, OCI labels, `/version`, SBOM, scan, and digest-only deployment posture.
Protected migration execution and rollout-health evidence remain separate
certification requirements. [Issue #375](https://github.com/sgajbi/lotus-idea/issues/375)
tracks the remaining execution gap. Protected staging and production
environments now exist with protected-branch rules, and production requires
reviewer approval. The environment-scoped database secret, governed target,
approved connectivity path, and live rollout evidence remain absent. The
workflow uses GitHub's ephemeral `ubuntu-latest` runner, consistent with the
other Lotus applications; runtime-only secret injection remains mandatory.

```mermaid
flowchart LR
    Local["Local contract gates"]
    Feature["Feature Lane"]
    PR["PR Merge Gate"]
    Main["Main Releasability"]
    Wiki["Wiki publication after merge"]

    Local --> Feature --> PR --> Main --> Wiki
    Local -->|"source-ingestion output contract"| PR
```

## Wiki Publication Control

Repo-local `wiki/` is the authored source. The live GitHub wiki is a publication
target and must not carry durable truth that is absent from `main`.

| Step | Command | Expected result |
| --- | --- | --- |
| Pre-merge wiki check | `C:\Users\Sandeep\projects\lotus-platform\automation\Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-idea` | Local source and publish target are compared without mutation. |
| Post-merge publish | `C:\Users\Sandeep\projects\lotus-platform\automation\Sync-RepoWikis.ps1 -Publish -Repository lotus-idea` | Published wiki matches the repo-local source from merged `main`. |
| Documentation gate | `make documentation-contract-gate` | Same-wiki links omit `.md`, required wiki surfaces exist, and governed anti-claim language remains present. |

## Command Groups

| Group | Primary commands | Use |
| --- | --- | --- |
| Aggregate lanes | `make check`, `make ci`, `make ci-release` | Routine local proof, broad CI-equivalent proof, and release evidence. |
| Contract and documentation | `make ci-contract-gate`, `make foundation-structure-gate`, `make documentation-contract-gate`, `make implementation-truth-gate`, `make supported-features-gate`, `make blueprint-scope-coverage-gate`, `make rfc0002-github-issue-execution-ledger-gate`, `make rfc0002-github-issue-execution-state-audit`, `make rfc0002-github-issue-execution-summary`, `make rfc0002-cross-repo-issue-posture`, `make rfc0002-github-issue-learning-pattern-gate` | Prevent workflow, docs, support, blueprint, issue-lifecycle, issue-learning, cross-repo status drift, and certification drift. |
| Dependency and vulnerability posture | `make dependency-vulnerability-posture-gate`, `make security-audit`, `make container-image-scan`, `make release-sbom` | Govern mature supported runtime, CI, and build-system dependencies, Python vulnerability scan evidence, container scan wiring, SBOM/signing/provenance hooks, issue-backed vulnerability exceptions, and platform exception-register linkage. |
| API and OpenAPI | `make openapi-gate`, `make endpoint-certification-gate`, `make api-route-metadata-gate`, `make caller-context-contract-gate` | Keep runtime API and published contract truth aligned. |
| Persistence and runtime | `make migration-contract-gate`, `make migration-execution-gate`, `make deployment-migration-contract-gate`, `make postgres-integration-gate`, `make disaster-recovery-contract-gate`, `make disaster-recovery-proof-gate`, `make container-runtime-smoke` | Prove durable storage, local migration plans, protected exact-image migration controls, restore/resume, and runtime behavior. |
| Mesh and proof artifacts | `make data-mesh-contract-gate`, `make mesh-policy-source-contract-proof-gate`, `make implementation-proof-readiness-check`, `make full-live-opportunity-journey-proof`, `make full-live-opportunity-journey-proof-gate`, `make implementation-proof-closure-manifest-gate`, `make blueprint-scope-coverage-gate`, `make canonical-opportunity-source-proofs`, `make runtime-trust-telemetry-snapshot-check` | Validate data-mesh, source-contract, proof-readiness, full-live journey composition, blocker ownership, and blueprint scope posture without conflating policy declarations, stale screenshots, or aggregate proof artifacts with certification. |
| Quality and maintainability | `make maintainability-gate`, `make duplicate-implementation-gate`, `make quality-scorecard-gate`, `make architecture-boundary-gate` | Prevent modularity and maintainability regression. |

Use the [Makefile](https://github.com/sgajbi/lotus-idea/blob/main/Makefile) as
the authoritative complete command inventory. This page groups the commands by
decision path so it stays readable.

`make architecture-boundary-gate` is the durable blocking architecture proof.
It also validates the tracked `quality/architecture_boundary_report.json`
freshness contract, including schema, source import digest, source file count,
rule digest, status, violations, and rule body. `make architecture-boundary-report`
regenerates that deterministic report. This is design-boundary evidence only;
it does not certify runtime behavior, Gateway/Workbench support, data-mesh
certification, or supported-feature promotion.

`make ci` is the broad local aggregate for lint, typecheck, contract gates,
OpenAPI, migrations, integration/e2e/coverage, and dependency audit. It must
not be cited as PostgreSQL runtime, Docker build, container smoke, image scan,
SBOM, or release evidence unless those targets were run separately.
`make ci-release` is the governed full-lane local command: it runs `make ci`
plus `implementation-proof-readiness-check`,
`runtime-trust-telemetry-snapshot-check`, `postgres-integration-gate`,
`docker-build`, `container-runtime-smoke`, `container-image-scan`, and
`release-sbom`. Run and cite `make ci-release` only when local Docker and
disposable PostgreSQL prerequisites are available.
`make ci-contract-gate` blocks drift if the full-lane target drops any of those
heavy proof families.

Baseline required checks include lint, format check, typecheck, architecture boundary enforcement,
repository hygiene, maintainability thresholds, protected private import boundary enforcement, documentation contract enforcement,
quality-scorecard truth, monetary precision guarding, no-sensitive-content evidence guarding,
OpenAPI quality, source-observability contract enforcement, API route metadata governance, API DTO base-model governance, shared signal DTO governance, API ProblemDetails boundary governance, API idempotency boundary and OpenAPI required-header governance, OpenAPI ProblemDetails example governance, signal API contract enforcement, operation metric contract enforcement, implementation-truth gate, supported-feature gate, endpoint-certification gate,
AI model-risk operations contract enforcement, AI model-risk operations proof contract enforcement,
unit tests, integration tests, e2e tests, data-mesh contract validation,
mesh policy source-contract validation, migration contract validation, coverage gate,
safe migration execution dry-run validation, protected exact-image deployment
migration contract validation, PostgreSQL runtime proof in PR/main GitHub lanes,
durable repository proof contract validation,
runtime trust telemetry test-execution contract validation,
Risk high-volatility and drawdown live-proof contract validation,
closed v2 Advise mandate/restriction runtime-evidence contract validation,
Advise mandate/restriction source-product proof contract validation,
report-intake route proof contract validation,
Workbench read-path source-contract proof validation,
Gateway/Workbench contract proof contract validation,
Gateway/Workbench discovery contract proof contract validation,
AI lineage store proof contract validation,
AI workflow-pack registration proof contract validation,
AI workflow-pack runtime execution proof contract validation,
source-ingestion worker manifest and source-safe output-contract validation,
scheduled source-ingestion worker source/deployment contract validation and
source-safe artifact-ref recording in aggregate implementation-proof readiness,
receipt-bound source-ingestion v2 `runtime_execution` validation with
aggregate-current provenance consumption, implementation-proof readiness release-lane artifact
generation, runtime trust telemetry preview validation and runtime trust
telemetry snapshot release-lane artifact generation,
security audit, Docker build validation, runtime-only Docker dependency posture,
non-root container execution, governed Docker base/scanner image identity,
commit-tagged image publication, registry digest capture in release evidence,
keyless image signing, provenance attestation, runtime Python dependency SBOM
evidence tied to the published service image reference/id/digest, packaged container startup
smoke proof over health/live/readiness, bounded GitHub job timeouts, no soft-failed
critical jobs, immutable GitHub Action SHA pins with version provenance, and workflow lint. The
scheduled-worker image contract additionally checks that every Compose-declared worker asset is
present in the build context and copied into the image, including the canonical manifest and
entrypoint helper modules. A local worker check is not enough: validate the built image with
`docker run --rm lotus-idea-lotus-idea-source-ingestion-worker python scripts/run_scheduled_source_ingestion_worker.py --check-only --manifest /app/docs/examples/source-ingestion/canonical-high-cash-worker.manifest.json`.

The typed Advise source-product gates use one capability-owned generator and
validator with separate profiles. They bind the current Advise product and
trust-telemetry files by digest, preserve blocked telemetry, and reject unknown
or authority-bearing claims. The documentation contract also reconciles every
aggregate proof CLI input with its application argument, evidence class,
tracking issue, and inventory row. Scheduled-worker deployment evidence remains
absent until a deployment controller emits a matching observed receipt. Issue
`#508` implements the fail-closed source-contract and deployment-evidence
contracts; static Compose declarations are not treated as a deployment receipt.

### Executable Proof Effects

The registry's blocker effect is enforced at runtime. Standard aggregate,
opportunity-archetype, source-ingestion, downstream, and scheduler consumers
must resolve one classified registry entry and match their intended
`blocker_clearing` or `supporting_evidence` behavior before accepting an
artifact. Unknown, duplicate, pending, or wrong-effect wiring fails closed.

Aggregate downstream contracts now pass through one provenance-aware
consumption boundary. A source contract outside the 24-hour aggregate freshness
window cannot appear in aggregate evidence merely because a nested readiness
model recognizes its static contract shape. This is an internal modularity and
correctness control; it does not prove route serving, deployment, production
certification, or supported-feature readiness.

`make ci-contract-gate` target explicitly fails if current blocking lint gates are removed from
`make lint`, if artifact-producing implementation-proof readiness or runtime
trust telemetry snapshot generation is added back to `make lint`, or if
`make ci-release` drops those release/review evidence generators, so enforcement
cannot silently degrade into optional local commands.
It also fails if Main Releasability regains a `push` trigger while the merged-PR
dispatch workflow remains active, because normal merges should produce one
authoritative release-proof run rather than a paired cancelled run and
successful dispatch run.

The GitHub Security tab posture is governed in both repository settings and
source-controlled files. Dependabot alerts/security updates are enabled, secret
scanning with push protection is enabled, private vulnerability reporting is
enabled, and CodeQL default setup is configured for GitHub-owned static
analysis over Python and GitHub Actions. `SECURITY.md` defines supported
security review scope, private reporting expectations, and source-safe report
content, while `.github/dependabot.yml` defines a single grouped Python
dependency-closure root update stream plus grouped GitHub Actions dependency
monitoring. Routine Dependabot version-update PRs are paused with
`open-pull-requests-limit: 0` while RFC delivery is active; manually regenerate
or cherry-pick dependency suggestions into the active implementation branch and
validate them through repo-native gates. It must not define a separate
`/requirements` lock-only Python update stream; use `make dependency-refresh`
to regenerate runtime lock truth from root pins before merge validation. GitHub currently reports non-provider
secret patterns and secret validity checks as disabled for this repository even
after an admin API enable attempt, so they are advisory future controls and are
not release-evidence claims. `make github-security-posture-check` verifies the
live mutable GitHub posture, including required enabled settings, CodeQL
`default` query suite with `remote` threat model, private vulnerability
reporting, and zero open code-scanning, secret-scanning, and Dependabot alerts.
`make ci-contract-gate` fails if the source-controlled controls are removed or
weakened.

CI timing and signal-quality evidence is retained as report-only release
support evidence. Feature Lane, PR Merge Gate, and Main Releasability run an
`if: always()` CI Signal Evidence job that reads GitHub job timing metadata with
`actions: read`, writes source-safe `ci-signal-evidence.json`, and uploads a
lane-specific artifact. The job must quote the composed
`repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs` argument passed
to `gh api` so workflow lint stays free of ShellCheck word-splitting
annotations. Main Releasability release evidence references
`main-releasability-ci-signal-evidence` and `ci-signal-evidence.json`.
The artifact distinguishes workflow feedback time from longest individual job
duration: `workflowWallClockSeconds` and `criticalPathSeconds` measure first
job start through last job completion, while `longestJobName` and
`longestJobSeconds` identify the largest single job. `make ci-signal-evidence-contract-gate`
validates the artifact schema and keeps `thresholdEnforced` false; `make ci-contract-gate` blocks
removal of the workflow wiring. No CI duration threshold is enforced yet.

Main Releasability SBOM evidence is runtime-dependency scoped. `make release-sbom`
generates `sbom.cdx.json` from `requirements/runtime-resolved.lock.txt` with the pinned
CycloneDX tool, and `release-evidence.json` records the SBOM scope, generator,
dependency source, project metadata, target service image reference, local image
id, registry digest, digest deployment reference, signature subject, and
provenance/SBOM attestation URLs.
`make runtime-dependency-closure-gate` blocks direct-only runtime locks by
checking the resolved lock against the installed transitive dependency closure
for the `pyproject.toml` runtime roots and against the
`requirements/requirements.txt` GitHub Dependency Graph mirror.
`make dependency-refresh` is the governed Python dependency PR reconciliation
command: it installs from root pins without a stale runtime-lock constraint,
then regenerates `requirements/runtime-resolved.lock.txt` and
`requirements/requirements.txt` from the active runtime closure.
Build isolation uses exact stable `pyproject.toml:build-system.requires` pins,
mirrored in `requirements/build-system.lock.txt`; `make security-audit` scans
that build-system lock alongside runtime and CI locks so build backend/tooling
resolver drift cannot bypass vulnerability posture.
Container OS/package posture remains the Trivy image scan's responsibility;
the generated SBOM remains runtime-dependency scoped rather than a full
container filesystem SBOM.

Images are pushed by CI only. Main Releasability lower-cases the GHCR
repository, tags the service image with `${GITHUB_SHA}`, scans and smoke-tests
the same tag, authenticates to GHCR with bounded fail-closed retry, pushes it
only after the release gates pass, resolves
`RELEASE_IMAGE_DIGEST_REF`, signs that digest with keyless Cosign, and creates
GitHub provenance and SBOM attestations. Environments must promote the same
`repository@sha256:<digest>` reference; deployment by mutable tag or
environment rebuild is not a supported release path.

### Image Identity Contract

`lotus.image-identity.v1` separates immutable build identity from the final
registry manifest digest. The image carries commit, branch, build timestamp,
repository, CI run, and build ID labels plus an explicit
`runtime-release-manifest` digest-binding label. It does not carry a value that
pretends to be its own final digest.

After publication, Main Releasability pulls and runs the exact
`repository@sha256:<digest>` image, captures OCI labels and `/version`, and runs
`make release-image-identity-contract-gate`. The gate compares build identity,
registry digest, Kubernetes deployment reference, signature subject,
provenance/SBOM attestation subjects, and runtime metadata. Placeholder values,
mutable-tag deployment, subject drift, or digest mismatch fail the release.
Published environments inject the resolved digest pair from governed release
or deployment metadata; missing or invalid bindings make readiness degraded.

Local Compose passes the same seven non-secret build-identity fields through
the governed `LOTUS_IDEA_BUILD_*` namespace. Canonical Workbench automation
must set exact Idea commit, branch, build time, repository, run, build, and
version values before rebuilding. The default `unknown`/`local` posture is
acceptable for ad hoc diagnostics only; it is not canonical provenance,
release evidence, or permission to pass secrets through Docker build inputs.

The same Compose contract requires the separate Advise, Manage, and Report
realization base/path pairs. Generic source-read URLs cannot stand in for
downstream handoff configuration; `make ci-contract-gate` blocks missing
realization wiring before canonical runtime validation.

PR Merge Gate and Main Releasability also run `make container-runtime-smoke`
after the Docker image build. The target starts the built image, probes
`/health` and `/health/live` for `200`, requires `/health/ready` to be reachable
with either `200` or the default-profile fail-closed `503`, prints container
logs on failure, and removes the container. This is packaged runtime startup
proof, not production deployment, live upstream connectivity, Workbench,
data-mesh certification, client publication, or supported-feature proof.

The runtime Dockerfile preserves cacheable dependency layers. It installs
`requirements/runtime-resolved.lock.txt` before copying `src`, then installs the
local package with `--no-deps` so source-only changes do not force the full
runtime dependency closure to reinstall. `make ci-contract-gate` blocks
source-before-dependency-install ordering and dependency reinstall drift while
leaving Docker build, runtime smoke, image scan, and SBOM evidence intact.

Docker build context hygiene stays aligned with generated-artifact cleanup.
`.dockerignore` excludes coverage data, `coverage.xml`, `sbom.cdx.json`,
`output`, and generated quality reports so local validation byproducts do not
become Docker builder inputs. `make ci-contract-gate` blocks Docker-context
generated-artifact parity drift without changing the runtime Dockerfile input
set.

Duplicate implementation enforcement is split by command. `make duplicate-implementation-inventory`
scans exact function-body duplicates across `src/app` and `scripts`, writes no artifacts, and
reports `thresholdEnforced: false` for review evidence. `make duplicate-implementation-gate` runs
the same scanner with `--fail-on-duplicates`, reports `thresholdEnforced: true`, and is wired into
`make lint` as the zero-cluster regression blocker. The initial six-line baseline scanned 1,750
functions and reported 31 exact duplicate clusters, including the known proof source-safety helper
families. The
first proof-helper consolidations moved source-safety traversal into
`scripts/proof_source_safety.py` and live-proof generator timeout/output plumbing plus
generated-at UTC parsing into `scripts/proof_generator_io.py`, and shared proof timestamp
validation, make-target evidence checks, and cross-repository file-evidence checks into
`src/app/application/source_safe_cross_repo_proof.py`, and AST call-name parsing into
`scripts/ast_gate_helpers.py`, and Core live-proof base URL resolution into
`scripts/proof_generator_io.py`, and Advise/Manage proof evidence request construction into
`scripts/proof_request_builders.py`, and mutating API reason-code validation into
`app.api.request_validation`, and bounded API telemetry count buckets into
`app.api.telemetry_buckets`, and caller-supplied signal response DTO projection into
`app.api.signal_models.SignalEvaluationResponse`, and application-layer portfolio-only signal
review scopes into `app.application.access_scope`, and source-reference/access-scope write-side
payload projection into `app.ports.evidence_payloads`, and API persistence-summary response
projection into `app.api.persistence_summary`, and API review access-scope DTOs into
`app.api.access_scope_models`, and blocked signal-result construction into
`app.domain.signal_evaluation.blocked_signal_result`, and optional proof-artifact JSON object
loading into `app.runtime.proof_artifact_files`, and source-product proof payload text-sequence
normalization into `app.application.source_product_proof_values`, and outbox contract
forbidden-text traversal into `scripts.contract_text_guards`, and operations-contract payload,
operation, and label validation into `scripts.operations_contract_validators`; the report-only
quality baseline now uses the same pass/ellipsis-only protocol-stub classifier as the blocking
maintainability and duplicate scanners, and emits POSIX-normalized report paths so Windows and
Linux runs produce deterministic quality evidence. The current local generated quality baseline
reports 9,252 executable source/test/script function rows, and the current duplicate
implementation gate reports 0 exact duplicate clusters across 2,953 source/script functions. The
CI contract gate protects the report-only and blocking target split, strict
`--fail-on-duplicates` enforcement, and `make lint` lane placement.
The exact duplicate-code threshold is promoted for first-party implementation bodies; broader
near-duplicate or generated-pattern similarity checks remain unpromoted until they have their own
measured baseline and exception policy.

Protected `main` uses strict branch protection. Required PR Merge Gate status checks are:

1. `PR Merge Gate / Workflow Lint`
2. `PR Merge Gate / Lint Typecheck Security`
3. `PR Merge Gate / Tests (unit)`
4. `PR Merge Gate / Tests (integration)`
5. `PR Merge Gate / Tests (e2e)`
6. `PR Merge Gate / Coverage Gate (Combined)`
7. `PR Merge Gate / PostgreSQL Runtime Proof`
8. `PR Merge Gate / Validate Docker Build`

The PostgreSQL runtime proof is required explicitly, not only as a Docker-build dependency, because
it proves durable repository behavior, migration rollback/reapply, idempotency replay,
source-ingestion recovery, concurrent review/feedback resource-identity
serialization, and source-safe AI explanation lineage persistence against real
`postgres:18-alpine` state.

Persistence adapter validation:

1. `tests/unit/test_postgres_repository.py` exercises the PostgreSQL repository
   adapter with a fake Postgres cursor across candidate persistence,
   idempotency replay, lifecycle history, audit events, review decisions,
   feedback, conversion intent/outcome, report evidence-pack requests, snapshot
   hydration, commit behavior, rollback on flush failure, optimistic stale
    same-candidate update rejection, idempotency primary-key collision retry,
    review/feedback resource-identity collision retry to governed replay or
    identity conflict, and atomic rollback of failed mutation attempts.
2. `tests/unit/test_postgres_idempotency_precheck.py` proves durable review,
   feedback, and conversion-intent replay/conflict prechecks read
   `idea_idempotency_record` by key plus candidate-detail projection without
   hydrating unrelated outbox or downstream state. Review and feedback also use
   bounded primary-key identity reads and reserve a new transport key only for
   equivalent resource content.
3. `tests/unit/test_repository_state.py` proves repository provider selection,
   runtime profile semantics, local/test process-local write allowance,
   production-like durable-write blockers, `PostgresIdeaRepository` when
   `LOTUS_IDEA_DATABASE_URL` is configured, psycopg mapping-row configuration,
   provider caching, durable-storage status, and connection close/reset
   behavior.
3. `tests/unit/test_security_caller_context.py` and
   `tests/integration/test_caller_context_boundary_api.py` prove that
   production-like profiles reject self-asserted `X-Caller-*` authorization
   headers without trusted-ingress provenance, while valid
   `X-Lotus-Trusted-Caller-Context` propagation still authorizes through the
   existing role plus capability policies. Representative signal, lifecycle,
   review, AI, report, downstream, and readiness routes preserve exact
   400/403 ProblemDetails, `application/problem+json`, sanitized correlation,
   and source-safe diagnostic categories without raw header or scope values.
   `make caller-context-contract-gate` blocks exception, handler, protected
   route, OpenAPI, media-type, and route-local parser drift.
4. `tests/integration/test_high_cash_signal_api.py` pins route-level
   `durableStorageBacked` derivation with an injected durable repository so
   future changes cannot hardcode repository-backed API posture to `false`.
5. `tests/integration/test_postgres_runtime_integration.py` is the first real
   PostgreSQL runtime proof. GitHub PR Merge Gate and Main Releasability run it
   against `postgres:18-alpine` with
   `LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED=1`; local runs skip unless
   `LOTUS_IDEA_POSTGRES_INTEGRATION_URL` is configured. The proof covers
   high-cash persistence/replay plus the first advisor queue, lifecycle,
   review, feedback, conversion intent/outcome, report evidence-pack request,
   internal source-ingestion replay/conflict recovery, and AI explanation
   lineage accepted/replayed/conflict workflow paths against real PostgreSQL
   state, plus schema rollback/reapply recovery.
5. `tests/unit/test_source_ingestion.py` now also proves the bounded run-once
   source-ingestion batch worker foundation: duplicate work-item replay,
   changed-source conflict, batch decision counts, timezone validation, maximum
   item enforcement, and correlation propagation.
6. `tests/unit/test_source_ingestion_worker.py` and
   `make source-ingestion-worker-check` prove the versioned run-once worker
   manifest contract plus source-safe check-only output contract and aggregate
   blocked-reason diagnostics without calling Core or writing repository state.
7. `tests/unit/test_source_ingestion_scheduled_worker.py`,
   `tests/unit/source_ingestion_scheduler/`, and
   `make source-ingestion-scheduled-worker-check` prove scheduler configuration,
   opt-in Docker Compose wiring, source-contract digest binding, deployment
   identity reconciliation, source-safe output, and non-clearing static
   evidence.
8. `tests/unit/source_ingestion_runtime_evidence/test_runtime_execution.py`,
   `tests/unit/source_ingestion_runtime_evidence/test_contract_gate.py`, and
   `make source-ingestion-runtime-execution-contract-gate` prove the closed v2
   `runtime_execution` contract. Positive fixtures traverse the application
   use case and repository; mutation tests reject unknown claims, non-current
   or wrong-authority Core refs, evidence-hash/scope/count drift, missing
   persistence receipts, mixed outcomes, in-memory posture, and claim
   inflation. Valid current evidence changes only the family live-Core posture
   and high-cash archetype live-Core blocker.
9. `tests/unit/test_generate_implementation_proof_readiness.py` and
   `make implementation-proof-readiness-check` prove the aggregate RFC-0002
   implementation-proof readiness artifact, including source-ingestion proof
   artifact refs, durable repository proof, runtime trust telemetry
   test-execution supporting evidence, non-AI operator workflow operations proof consumption,
   and default durable output at `output/implementation-proof/readiness-current.json`
   unless `IMPLEMENTATION_PROOF_OUTPUT` intentionally overrides the ignored artifact path,
   Workbench read-path source-contract proof consumption, Gateway/Workbench
   source-contract proof consumption, Gateway/Workbench discovery contract
   proof consumption, bounded outbox broker source-contract proof consumption,
   default digest-bound Advise and Manage route source-contract generation and
   supporting-evidence consumption without live-blocker clearance,
   optional closed v3 Manage mandate runtime-evidence consumption,
   optional receipt-bound Core benchmark-assignment runtime evidence consumption,
   optional receipt-bound Core portfolio-state runtime evidence consumption,
   optional closed v2 Core missing-benchmark runtime-evidence consumption,
   optional closed v2 Performance benchmark-readiness runtime-evidence
   consumption,
   default Report intake route source-contract generation and consumption, default
   Report materialization source-contract generation and consumption, default
   platform catalog source contract generation and
   consumption, AI lineage store proof generation and consumption, and AI
   workflow-pack registration/runtime execution proof generation and consumption,
   plus opportunity archetype scenario readiness from the governed contract, can be
   generated without starting the service and
   without exposing candidate, portfolio, client, prompt, outbox event, raw
   idempotency, broker, or source payload identifiers.
10. `tests/unit/runtime_trust_telemetry/test_test_execution_contract.py` and
    `make runtime-trust-telemetry-test-execution-contract-gate` validate the
    source-safe v2 `test_execution` contract. Aggregate readiness records valid
    current evidence as provenance but clears no blocker, preserving
    `runtime_candidate_snapshot_missing`, `durable_repository_not_configured`,
    `runtime_trust_telemetry_product_coverage_incomplete`,
    `certified_runtime_trust_telemetry_missing`, and
    `data_mesh_runtime_telemetry_not_certified` until declared product coverage
    is complete.
11. `tests/unit/workbench/test_read_path_source_contract.py` and
    `make workbench-read-path-source-contract-proof-gate` prove the source-safe
    Workbench queue/detail read-path v2 `source_contract`. Aggregate readiness
    records its evidence reference but preserves
    `workbench_gateway_bff_consumption_proof_missing` until runtime serving,
    consumption, entitlement, and browser evidence exists.
12. `tests/unit/workbench/test_contract_proof.py` and
    `make gateway-workbench-contract-proof-contract-gate` prove the
    source-safe bounded Gateway/Workbench contract proof. Aggregate readiness
    records the `source_contract` evidence reference but preserves
    `gateway_workbench_proof_missing` for source-ingestion and outbox-delivery
    until machine-verifiable runtime execution evidence exists.
13. `tests/unit/workbench/test_discovery_contract_proof.py` and
    `make gateway-workbench-discovery-contract-proof-contract-gate` prove the
    source-safe bounded Gateway/Workbench discovery contract proof. Aggregate
    readiness adds its reference to data-mesh and runtime-trust evidence but
    preserves `gateway_workbench_discovery_proof_missing` until
    machine-verifiable runtime evidence exists.

    `tests/unit/workbench/test_owner_mainline_evidence.py` and
    `make gateway-workbench-owner-mainline-evidence-gate` validate the
    RFC-0002 Slice 11 owner-mainline evidence index. The contract binds exact
    merged-main Gateway and Workbench PR/CI evidence while preserving
    production identity, browser/accessibility, canonical runtime,
    data-product certification, and supported-feature promotion blockers.
14. `tests/unit/workbench/test_runtime_execution.py` and
    `make gateway-workbench-runtime-execution-proof-gate` validate the optional
    Gateway/Workbench runtime-execution proof consumer. The artifact consumes
    Workbench canonical `live-validation-summary.json`, `SHOT-INDEX.md`, and
    the owner-mainline evidence index. Aggregate readiness can clear only
    `workbench_gateway_bff_consumption_proof_missing` from a valid
    aggregate-current artifact; production identity, browser accessibility,
    canonical demo runtime certification, data-product publication,
    client-publication authority, suitability/execution authority, and
    supported-feature promotion remain blocked.
15. `tests/unit/outbox/broker/test_source_contract_proof.py`,
    `tests/unit/outbox/broker/test_readiness_consumption.py`,
    `tests/unit/outbox/test_outbox_consumer_contract_proof.py`,
    `tests/unit/outbox/test_outbox_consumer_runtime_execution.py`,
    `tests/unit/outbox/test_outbox_consumer_runtime_readiness.py`,
    `tests/unit/outbox/platform_mesh/test_source_contract_proof.py`,
    `tests/unit/outbox/platform_mesh/test_readiness_consumption.py`,
    `make outbox-consumer-contract-gate`,
    `make outbox-broker-source-contract-proof-gate`,
    `make outbox-consumer-contract-proof-contract-gate`, and
    `make outbox-consumer-runtime-execution-proof-gate`,
    `make outbox-platform-mesh-event-source-contract-proof-gate` prove the
    declared downstream consumer contract, source-safe bounded outbox broker
    source contract that clears no readiness blocker, bounded downstream
    consumer source-contract proof, bounded domain-consumer runtime execution
    proof, and bounded platform-mesh event source-contract proof. Aggregate
    readiness records source-contract evidence without clearing runtime
    blockers, and may clear only `downstream_consumer_runtime_proof_missing`
    when the runtime proof consumes valid Advise, Manage, and Report receipts.
    `platform_mesh_event_publication_proof_missing` remains until runtime
    publication evidence exists.
15. `tests/unit/report/test_intake_route_source_contract.py`,
    `tests/unit/report/test_intake_runtime_execution.py`,
    `tests/unit/report/test_intake_runtime_readiness.py`,
    `tests/unit/test_downstream_realization_readiness.py`,
    `tests/integration/test_downstream_realization_readiness_api.py`,
    `make report-intake-route-source-contract-proof-gate`, and
    `make report-intake-runtime-execution-proof-gate` separate Report intake
    source-contract provenance from runtime serving proof. The runtime proof may
    clear only `lotus_report_live_intake_route_proof_missing`; tests reject
    inflated materialization, render, archive, publication, production identity,
    certification, and promotion claims.
16. `tests/unit/report/test_materialization_source_contract.py` and
    `make report-materialization-source-contract-proof-gate` validate the
    source-safe `lotus-report` materialization source contract. The v3 artifact
    records `reportOwnerMaterializationContractConsumed=true` and links
    `sgajbi/lotus-report#152` as the closed owner proof. Downstream and
    aggregate readiness may cite the artifact but clear no blocker. Tests keep
    `report_evidence_pack_live_materialization_proof_missing`,
    `rendered_output_creation_missing`, `archive_record_creation_missing`,
    client-publication, certification, and promotion blockers, and reject
    inflated runtime or authority claims.
17. `tests/unit/report/test_materialization_runtime_execution.py` and
    `make report-materialization-runtime-execution-proof-gate` validate the
    receipt-bound `lotus-report` materialization runtime-execution proof. A
    valid current artifact must bind source-safe Report materialization
    receipts to exact Render #65/PR #67 and Archive #72/PR #73 owner-mainline
    evidence. It clears `report_evidence_pack_live_materialization_proof_missing`,
    `rendered_output_creation_missing`, and `archive_record_creation_missing`
    while preserving client-publication, production-identity, legal/retention,
    support, final certification, and supported-feature blockers.
18. `tests/unit/test_ai_lineage_store_proof.py` and
    `make ai-lineage-store-proof-contract-gate` prove the source-safe AI
    lineage store proof contract that aggregate readiness consumes to clear
    only `certified_ai_lineage_store_missing`, without leaking prompt,
    provider response, candidate, portfolio, client, request-body,
    response-body, or database URL material.
18. `tests/unit/ai_workflow_pack_registration/test_source_contract_proof.py` and
    `make ai-workflow-pack-registration-proof-contract-gate` prove the bounded
    sibling `lotus-ai` workflow-pack registration source contract. A valid v2
    artifact adds an evidence reference but clears no aggregate blocker. It
    preserves `workflow_pack_runtime_contract_not_certified`, `lotus-ai`
    runtime/provider, Workbench, client-ready, and supported-feature blockers.
19. `tests/unit/test_ai_workflow_pack_runtime_execution_proof.py`,
    `tests/unit/test_lotus_ai_workflow_runtime.py`, and
    `make ai-workflow-pack-runtime-execution-proof-contract-gate` prove the
    actual deterministic `lotus-ai` runtime execution receipt contract.
    A valid artifact clears only `lotus_ai_runtime_execution_missing` in
    aggregate readiness, adds `lotus_ai_live_provider_execution_missing`, and
    preserves workflow-pack registration, Workbench, client-ready, and
    supported-feature blockers. `lotus-ai` PR #123 on main
    `937501833b4c2a9d3031a108368ca113204b5db9` with Main Releasability
    `30402022877` is bounded deterministic local-dev
    `idea_explanation.pack@v1` proof-contract evidence only; live-provider,
    model-risk, retention/deletion, Workbench, publication, and final journey
    blockers remain open.
20. `tests/unit/runtime_trust_telemetry/test_telemetry.py`,
    `tests/unit/runtime_trust_telemetry/test_snapshot_cli.py`,
    `tests/integration/test_runtime_trust_telemetry_api.py`,
    `make runtime-trust-telemetry-preview-check`, and
    `make runtime-trust-telemetry-snapshot-check` prove the source-safe runtime
    trust telemetry preview, API-certified contract-shaped snapshot diagnostic,
    and contract-shaped generated snapshot can be produced without exposing
    candidate identifiers, source routes, evidence hashes, portfolio
    identifiers, or client identifiers, and without promoting mesh
    certification.
21. `tests/unit/test_opportunity_archetype_contract_gate.py` and
    `make opportunity-archetype-contract-gate` prove the governed opportunity
    archetype/scenario contract preserves source-authority ownership, keeps
    high cash / idle liquidity as the first partially implemented journey, and
    blocks external demo promotion, client-publication,
    data-mesh-certification, and supported-feature claims.
    The same test pack now proves every implemented caller-supplied signal API
    recorded in the archetype contract is also required by the contract gate:
    API module, route, and integration-test evidence cannot drift apart.
    Representative Core, Risk, Performance, and Advise signal API tests also
    prove wrong `sourceSystem` or `productId` source refs are rejected before
    candidate creation or high-cash persistence, with product-safe
    `400 invalid_request` responses and source-safe invalid-request telemetry.
    `tests/unit/risk_concentration_runtime_evidence/` and
    `make risk-concentration-live-proof-contract-gate` prove the optional Lotus
    Risk concentration live-proof artifact remains source-safe and can clear
    only the namespaced live Risk source blocker when valid evidence is supplied.
    `tests/unit/high_volatility_runtime_evidence/` and
    `make high-volatility-live-proof-contract-gate` prove the optional Lotus
    Risk volatility evidence is a closed v2 `runtime_execution` receipt. It
    binds current `RiskMetricsReport:v1` evidence to the authoritative Idea
    evaluation-and-persistence result, rejects tampering and in-memory claims,
    and can clear only the namespaced volatility source blocker. The required
    PostgreSQL lane proves accepted persistence, repository reload, and replay.
    `tests/unit/test_opportunity_archetype_contract_gate.py` and
    `make opportunity-archetype-contract-gate` also require the
    high-volatility API module, route, and integration test as archetype
    evidence.
    `tests/unit/risk_drawdown_runtime_evidence/`,
    `tests/integration/source_runtime_evidence/test_postgres_replay.py`, and
    `make risk-drawdown-live-proof-contract-gate` prove the optional Lotus Risk
    drawdown artifact is a closed v2 `runtime_execution` receipt. It binds
    current `DrawdownAnalyticsReport:v1` evidence to the authoritative Idea
    evaluation-and-persistence result, rejects tampering and in-memory claims,
    and can clear only the namespaced drawdown source blocker. The required
    PostgreSQL lane proves accepted persistence, repository reload, and replay.
    `tests/unit/test_opportunity_archetype_contract_gate.py` and
    `make opportunity-archetype-contract-gate` also require the drawdown API
    module, route, and integration test as archetype evidence.
    `tests/unit/performance_underperformance_runtime_evidence/` and
    `make performance-underperformance-live-proof-contract-gate` prove the
    optional Lotus Performance underperformance artifact is closed v2
    `runtime_execution` evidence. It must bind current Performance evidence to
    accepted or replayed durable Idea persistence and can clear only the
    namespaced live Performance source blocker.
    `tests/unit/core_benchmark_assignment_runtime_evidence/` and
    `make core-benchmark-assignment-live-proof-contract-gate` prove the
    optional Lotus Core benchmark-assignment artifact is closed v2
    `runtime_execution` evidence. It binds pseudonymous request scope to one
    exact current Core source receipt and can clear only the namespaced
    benchmark-assignment source-ref blocker. The read-only use case has no
    fabricated Idea persistence receipt.
    `tests/unit/core_portfolio_state_runtime_evidence/` and
    `make core-portfolio-state-live-proof-contract-gate` prove the optional
    Lotus Core portfolio-state artifact is closed v2 `runtime_execution`
    evidence. It binds a named read-only use case, pseudonymous request scope,
    and complete current `PortfolioStateSnapshot:v1` receipt, and can clear only
    the namespaced Core portfolio-state source-ref blocker. Missing snapshot
    identity, reconciliation, policy, section, scope, time, or hash trust fails
    closed; lotus-core issue `#790` tracks the current producer gap.
    `tests/unit/bond_maturity_runtime_evidence/` and
    `make bond-maturity-live-proof-contract-gate` prove the optional Lotus Core
    maturity-summary artifact is closed v2 `runtime_execution` evidence. It
    binds pseudonymous request scope to one exact current
    `PortfolioMaturitySummary:v1` receipt and upstream `HoldingsAsOf:v1`
    content identity. Partial/stale evidence, scope or digest mismatch,
    projected holdings, unsupported lifecycle features, unknown reconciliation,
    inconsistent dates/counts, and tampering fail closed. A supported empty
    window completes without creating an opportunity. The artifact can satisfy
    only the namespaced bond-maturity live Core source blocker; lotus-core issue
    `#792` tracks missing producer reconciliation, tenant, and correlation
    metadata.
    `tests/unit/low_income_cashflow_runtime_evidence/` and
    `make low-income-core-cashflow-live-proof-contract-gate` prove the optional
    Lotus Core cashflow artifact is closed v2 `runtime_execution` evidence. It
    binds pseudonymous request scope, exact movement-summary and projection
    receipts, projection arithmetic, movement counts, and deterministic
    candidate or no-opportunity outcome. Unknown, stale, degraded,
    scope-inconsistent, arithmetically invalid, or tampered evidence fails
    closed; zero cashflow remains valid no-opportunity evidence. It can satisfy
    only the namespaced low-income Core cashflow source blocker. Core issue
    `#796` tracks producer trust metadata required for live qualification.
    `tests/unit/advise_missing_suitability_runtime_evidence/test_runtime_execution.py`,
    `tests/unit/advise_missing_suitability_runtime_evidence/test_generator.py`,
    `tests/unit/advise_missing_risk_profile_runtime_evidence/test_runtime_execution.py`,
    `tests/unit/advise_missing_risk_profile_runtime_evidence/test_generator.py`,
    `make missing-suitability-live-proof-contract-gate`, and
    `make missing-risk-profile-live-proof-contract-gate` prove the optional
    Lotus Advise policy-evaluation and risk-profile evidence remains
    source-safe and can clear only its namespaced Advise source blocker when
    valid evidence is supplied. Both use closed v2 runtime-execution contracts
    over exact request, workflow, and evaluation receipts, invoke one named use
    case with one fetch, and accept deterministic candidate or truthful
    no-opportunity outcomes. Unknown fields, scope/time/hash/posture drift,
    stale evidence, tampering, and raw identifiers fail closed.
    `tests/unit/test_implementation_proof_readiness.py`,
    `tests/unit/test_generate_implementation_proof_readiness.py`, and
    `tests/integration/test_implementation_proof_readiness_api.py` also prove
    that aggregate readiness exposes those scenario blockers as namespaced
    `opportunity_archetype_*` operator evidence without clearing product
    support.
    Historical canonical evidence generated on 2026-07-05 for
    `PB_SG_GLOBAL_BAL_001` exercised Risk concentration and the former flat
    Performance proof families. The retired Performance artifacts no longer
    qualify after the closed v2 underperformance and benchmark-readiness
    contracts. A fresh run must bind exact runtime receipts and matching
    aggregate provenance before either Performance blocker can clear. Core,
    Manage, Workbench, data-mesh, client-publication, and supported-feature
    blockers remain independent.
16. `tests/unit/test_downstream_realization_contract_gate.py` and
   `make downstream-realization-contract-gate` prove the governed downstream
   realization contract plan remains planned, source-authority preserving,
   blocker-backed, and free of route-existence, downstream-execution, or
   supported-feature claims.
17. `tests/unit/test_downstream_realization_readiness.py` and
   `tests/integration/test_downstream_realization_readiness_api.py` prove the
   downstream realization readiness diagnostic for blocked supportability,
   role plus capability enforcement, product-safe payloads, source-authority
   boundaries, planned downstream contract-readiness records, and bounded
   `not_certified` operation events without calling Advise, Manage, Report,
   Render, or Archive.
18. `tests/unit/test_downstream_outcome_certification.py` and
   `make downstream-outcome-certification-proof-gate` prove the #379 aggregate
   downstream outcome certification boundary. The proof composes Advise,
   Manage, and Report owner runtime receipts with Idea durable
   submission/reconciliation coverage for accepted, rejected,
   duplicate/replay, idempotency-conflict, timeout-before-response,
   response-before-local-commit, restart reconciliation, and operator
   reconciliation replay windows. It clears no new blocker and keeps
   suitability, rebalance/execution, report-rendering/archive,
   client-publication, production-identity, supported-feature, and
   certification-closure claims false. Mainline evidence is PR #742 on
   `0a4e7a55495cb3b979672f52b08ba2630603cf94` with Main Releasability
   `30323405962`, wiki commit `ce29814` with strict `DiffCount 0`, followed by
   PR #743 ledger reconciliation on current main
   `8ccee32d9a25fb6c47c723e105e2c48d1c4b3c70` with Main Releasability
   `30324178801`. Issue #379 remains open in `status/blocked`, not
   QA-pending: owner-app local implementation evidence is merged, while
   production/certification evidence, trusted IdP caller context, and Archive
   legal/privacy lifecycle conformance remain open. Report-owned
   retention-policy conformance is closed through `sgajbi/lotus-report#136`
   on lotus-report main `f8d220d74dd21d0c51cc310c117264c96b879d62`
   with Main Releasability run `30898036781` and current-main focused QA.

   Slice 18 issue-posture reconciliation also records the current #340 and
   #380 truth. PR #745 reconciled #340 to `open_merged_main_qa_pending` at
   `eeabfc683f595b4cbc9ffb5aa0aa51c3e5622903`; Main Releasability
   `30326431318` and CodeQL `30326422515` passed. Final QA closed #340 on
   2026-07-29 after Idea-side attestation/governance/lineage/API proof and
   producer-side `lotus-ai` workflow-run attestation proof passed against
   current mainline evidence. PR #746 corrected stale ready
   posture for #380 and reconciled it to `open_blocked` at
   `6f8875dc6784dd17975e6700c09b9ff71d66fb8b`; Main Releasability `30327202465`
   and CodeQL `30327193673` passed. The RFC-0002 execution summary now has 54
   tracked issues, 29 closed complete, 25 open, no
   `open_merged_main_qa_pending`, 1 `open_in_progress`, no `open_pr_raised`,
   14 `open_blocked`, and
   no ready issues. #379 is `open_blocked`, not QA-pending because
   Idea now consumes the `sgajbi/lotus-manage#620` temporal receipt identity
   fields through closed v3 Manage mandate runtime evidence, while
   production/certification evidence remains open through
   `sgajbi/lotus-manage#624` and `sgajbi/lotus-archive#55`. #685 is
   `open_blocked`, not QA-pending: the 2026-07-29 governed Workbench startup
   attempt via `npm run live:stack:up` restored core portfolio readiness for
   `PB_SG_GLOBAL_BAL_001`; valuation and aggregation jobs drained to zero,
   positions/cash data quality reached `COMPLETE`, and analytics/return-path
   dates reached `2026-04-10`. The run then failed in the DPM command-center
   action-register seed because the Manage rebalance simulation endpoint
   returned HTTP 424 with `DPM_CORE_CONTEXT_INCOMPLETE`. The current blocker is
   tracked in `sgajbi/lotus-core#840`. Fresh Gateway/BFF-backed Workbench
   queue/detail runtime evidence remains required before #685 can move to
   merged-main QA.
   Platform PR `sgajbi/lotus-platform#631` fixes the prior Manage seed
   authorization failure; #686 is blocked, not QA-pending, until
   `sgajbi/lotus-core#840` restores canonical DPM source readiness and Workbench
   live browser action-control proof can be rerun. #340 is closed for the signed
   attestation trust boundary without claiming supported-feature promotion,
   client-ready publication, Workbench proof, autonomous advice, prompt/RAG
   infrastructure, model training, or broader production rollout. #380 remains blocked for
   production principal/session, authenticated Workbench BFF, core-owned
   canonical runtime, mesh onboarding, entitlement-denied, and supported-feature
   promotion evidence, and #693 is blocked rather than QA-pending until
   protected capacity-production-like runner/environment, protected attestations,
   and matching FinOps evidence exist. #690 is now closed complete after
   PR #774 merged to main at `5f53c4ac6ac519c7e6b0019e00f5286109e1628c`,
   PR #775 synchronized source truth to main at
   `800f682c4f7ae20a2c0634eb112323d7936cca73`, Main Releasability
   `30430120214` and CodeQL `30430108647` passed, wiki publication completed at
   `lotus-idea.wiki` commit `3ebd0f0` with strict `DiffCount 0`, branch cleanup
   completed, and final QA passed `make report-intake-runtime-execution-proof-gate`
   plus `make implementation-proof-readiness-check`. The bounded Report intake
   runtime proof clears only `lotus_report_live_intake_route_proof_missing`
   after aggregate-current validation; client publication, production identity,
   supported-feature promotion, report rendering authority, Archive production
   trust, legal/privacy approval, and final Slice 13 certification remain
   unclaimed. PR #776 then synchronized that final QA closure truth to exact
   main `aa492aedd46f30b854c8478edb919605dbdd58fc`; Main Releasability
   `30432065538` and CodeQL `30432058627` passed, wiki publication completed at
   `lotus-idea.wiki` commit `c08509a` with strict `DiffCount 0`, branch cleanup
   completed. PR #777 then synchronized #681 evidence after #690 QA closure to
   exact main `39d51c5cb63df360f1e97e6e9e862784a9ad9178`; Main Releasability
   `30434057675`, CodeQL `30434051218`, wiki publication commit `d0a1fa1`,
   strict `DiffCount 0`, and branch cleanup passed. PR #787 corrected the live
   cross-repo posture command on exact main
   `39a480ddf115649acc3f6793a69596d4e5912bc8`; Main Releasability
   `30451401411`, Push on main `30451387946`, wiki publication commit
   `d06f46b`, strict `DiffCount 0`, and branch cleanup passed. PR #789 then
   classified blocked issue actionability on exact main
   `01ae36ba89f975508bde47b4361190ef5c083597`; Main Releasability
   `30456433618`, Main CodeQL/Push run `30456425304`, wiki publication commit
   `c926899`, strict `DiffCount 0`, and branch cleanup passed. PR #790 then
   synchronized that evidence into source-controlled execution truth on exact
   main `f23c72d7d95d1676b8f673f538a9336e4b704fbc`; Main Releasability
   `30458163573`, Main CodeQL/Push run `30458146092`, wiki publication commit
   `bbd9e2f`, strict `DiffCount 0`, and branch cleanup passed. PR #791 then
   synchronized PR #790 evidence into source-controlled execution truth on exact
   main `65e11890aaddb70fea4cf9d80e836ce1625a6c44`; Main Releasability
   `30460122600`, Main CodeQL `30460101418`, wiki publication commit
   `2453c3006722ee40e48762d884581fb6b3893bbe`, strict `DiffCount 0`, and branch
   cleanup passed. Workbench PR #505 narrowed the BFF principal-boundary blocker
   on Workbench main `1b4afb92f4c810c99921fc26e451b04bca731e28`; Pull Request
   Merge Gate `30464152669`, branch head
   `c4add59871bc3f0e78dc6602c8857c5e141e6367`, Main Releasability
   `30465110912`, Workbench wiki publication `3b4f78f`, strict `DiffCount 0`,
   and branch cleanup passed. Platform PR #639 hardened stale PR-text payload
   guidance on platform main `641aabe9f303a178f3a4e489c52b3d789d8339d3` with
   Main Releasability `30475978275` passing. PR #801 then synchronized the final
   #797/#681 evidence on Idea main
   `95c47d27f45e09369f6b709588fa2de1a1f8700b`; exact-main Main Releasability
   `30487277416` passed. PR #802 then synchronized current RFC-0002 posture
   truth on Idea main `7df8fbff1fbab3acb5568a8e95eb7d5d58c8dcdd`; exact-main
   Main Releasability `30488990343` passed and wiki publication reached
   `ec05a36` with strict `DiffCount 0`. PR #803 then synchronized PR #802
   evidence truth on Idea main `31e5157de796e0accd0f23d3a80102ecd0871c71`;
   exact-main Main Releasability `30490458612` passed and wiki publication
   reached `3743f01` with strict `DiffCount 0`. PR #804 then synchronized PR #803
   evidence truth on Idea main `615e3ba848af551801c897dd9b0a52f964801da0`;
   exact-main Main Releasability `30491918891` passed and wiki publication
   reached `05026e8` with strict `DiffCount 0`. At that synchronized snapshot,
   the then-current cross-repo RFC-0002 posture checked the governed
   13-repository owner/dependency set: 93 label-backed tracked issues, 56
   complete, and 37 open, split into 27 blocked, 2 in-progress, and
   8 tracker issues. The blocked subset has 0 app-actionable
   blocked issues, 4 Core dependencies, and 23 external/protected-evidence
   blockers after fresh canonical validation reopened `sgajbi/lotus-core#836`
   as `status/in-progress`. #683 and #684 remain
   prerequisite-gated and must not carry `status/ready`; #691, #692, and #699 remain blocked rather
   than QA-pending because their merged implementation tranches preserve only
   bounded Render/Archive, mesh-readiness, and proof-control evidence;
   lifecycle-safe publication authority, production identity, Archive production
   trust/legal evidence, platform mesh certification, Gateway/Workbench
   discovery proof, supported-feature promotion, and final live-journey evidence
   remain open.

   Slice 15 operations blockers have explicit no-claim boundaries. #343 remains
   blocked, not QA-pending: logical restore/resume validation and DR runbooks
   are repository-owned proof, while managed-provider backup topology,
   encrypted backup/WAL inventory, continuous WAL/PITR health, physical restore,
   failover/cutover approval, rollback-window evidence, and provider evidence
   retention/signature proof remain absent. #344 remains blocked, not
   QA-pending: repository data-lifecycle controls and signed Archive lifecycle
   posture consumption exist, while live bank producer/key discovery, policy
   approval, managed Archive trust/key/store proof, provider-native AI deletion,
   and production authorized purge proof remain absent. #375 remains blocked,
   not QA-pending: `lotus-idea-staging` and `lotus-idea-production`
   environments exist, but the 2026-07-29 recheck found no environment-scoped
   `LOTUS_IDEA_DATABASE_URL` secrets and no `Deployment Migration Evidence`
   workflow runs.
19. `tests/unit/test_source_ingestion_readiness.py` and
   `tests/integration/test_source_ingestion_readiness_api.py` prove the
   operator readiness diagnostic for blocked/configured posture,
   permission-denied behavior, relative manifest resolution, and bounded
   `not_certified` operation events without calling Core. The integration
   suite also proves the source-ingestion run-once operator action blocks
   without durable storage or runtime configuration, executes the configured
   domain batch path source-safely, enforces operator capability, and emits a
   bounded `source_ingestion_run_once` event.
20. `tests/unit/test_review_queue_application.py`,
   `tests/unit/test_postgres_review_queue.py`,
   `tests/integration/test_review_queue_api.py`, and
   `tests/integration/test_api_operation_events.py` prove the advisor queue
   readiness diagnostic for aggregate queue posture, permission-denied
   behavior, timestamp validation, product-safe payloads, and bounded
   `not_certified` operation events without exposing candidate identifiers or
   access-scope identifiers. The PostgreSQL test proves the durable readiness
   aggregate reads only candidate records and avoids unrelated state-family
   hydration.
20. `tests/unit/test_ai_explanation_readiness.py`,
   `tests/integration/test_ai_governance_api.py`, and
   `tests/integration/test_api_operation_events.py` prove the AI explanation
   readiness diagnostic for blocked model-risk posture, operator/capability
   enforcement, product-safe payloads, and bounded `not_certified` operation
   events without invoking `lotus-ai` or exposing prompts, provider payloads,
   candidate identifiers, source routes, portfolio identifiers, or client
   identifiers. `tests/integration/test_postgres_runtime_integration.py` proves
   the configured PostgreSQL runtime records, same-key replays, distinct-key
   request-id conflict-checks, and API idempotency-gates source-safe AI
   explanation lineage through the API without promoting `lotus-ai` runtime
   execution or AI explanation support.
21. `tests/unit/outbox/test_outbox_delivery_readiness.py` and
   `tests/unit/outbox/test_postgres_readiness.py`, plus
   `tests/integration/outbox/test_delivery_readiness_api.py`, prove the
   outbox delivery readiness diagnostic and run-once operator action for
   aggregate backlog/status posture, durable repository posture, broker
   configuration posture, publisher-adapter presence, blocked-without-broker
   behavior, configured-publisher delivery path, operator plus capability
   enforcement, PostgreSQL repository-side readiness projection without
   whole-snapshot hydration, route-owned broker publisher cleanup after
   run-once execution, source-safe publisher-cleanup failure isolation,
   product-safe payloads, UTC request validation, and bounded `not_certified`
   operation events without exposing event identifiers, raw
   idempotency keys, source payloads, broker payloads, or downstream contract
   details.
22. Runtime API database wiring is opt-in and still requires deploy migration
   evidence, certified long-running scheduled source-worker proof, live Core
   source-worker proof, and mesh/support promotion evidence before any
   supported durable product claim. Scheduler source/deployment evidence is
   validated separately by `make source-ingestion-scheduled-worker-check`.

The CI contract gate is blocking from day one. It prevents accidental removal of bank-buyable
controls from the Makefile or GitHub lanes, including least-privilege workflow permissions,
verified immutable action SHA pins with version provenance, 99% combined coverage in merge/releasability lanes, Docker build
validation, pinned CycloneDX SBOM generation, pinned Trivy container image scanning,
SBOM/release evidence with resolved base/scanner image digests, endpoint certification, supported-feature promotion control,
data-mesh contract validation, downstream realization contract validation,
migration contract validation, migration execution dry-run
validation, source-ingestion worker manifest and output-contract validation,
source-ingestion runtime-execution receipt contract validation, PostgreSQL runtime
proof, durable repository proof contract validation, workflow-dispatch access, non-suppressed auto-merge token
usage, merged-PR main-releasability dispatch, bounded job timeouts, no `continue-on-error: true`
in critical lanes, maintainability enforcement, quality-scorecard truth,
repository-hygiene enforcement, no-sensitive-content evidence guarding,
implementation-truth enforcement, and source-safe local quality gates.
It also has unit coverage for current-repository pass behavior and failure cases for floating
action tags, wrong verified SHAs, missing version provenance comments, weakened focused test target
wiring, missing critical e2e workflow proof, and raw workflow `pytest` shortcuts.
The e2e lane is not only a health probe: it must retain a deterministic internal
idea workflow proof covering candidate persistence, advisor queue projection,
review approval, conversion intent, report evidence-pack request, and authority
boundaries. `make test-unit`, `make test-integration`, and
`make test-e2e` default to their full suite paths while allowing scoped fix-forward runs through
`UNIT_TESTS`, `INTEGRATION_TESTS`, and `E2E_TESTS` overrides:

```powershell
make test-unit UNIT_TESTS=tests/unit/runtime_trust_telemetry/test_telemetry.py
make test-integration INTEGRATION_TESTS=tests/integration/test_runtime_trust_telemetry_api.py
make test-e2e E2E_TESTS=tests/e2e/test_critical_idea_workflow.py
```

Use these overrides for fast local diagnosis. PR evidence should still state whether the full
repo-native target or a focused target was run.

Integration and E2E API tests must construct clients through
`tests.support.http.managed_test_client`. The integration and E2E fixtures enter
the application lifespan and close all clients after each test, including
failure paths. `make test-client-lifecycle-gate` is blocking through
`make lint` and rejects direct FastAPI or Starlette `TestClient` imports and
construction in both suites. This keeps shutdown behavior explicit and prevents
cumulative event-loop socket exhaustion during repeated Windows suites and the
critical idea workflow E2E lane.

GitHub test and coverage lanes must stay repo-native:

```powershell
make test-unit
make test-unit-coverage
make test-integration-coverage
make test-e2e-coverage
make test-coverage
```

The PR Merge and Main Releasability matrices call the suite-level coverage targets and publish the
same `.coverage.<suite>` artifacts. `make ci-contract-gate` rejects raw workflow `pytest` shortcuts
so GitHub cannot drift away from the local Makefile contract.

The repository-hygiene gate blocks tracked generated artifacts and local runtime byproducts:
Python cache files, coverage outputs, build/dist outputs, dependency directories, local
environment files, logs, and local databases. It is intentionally based on `git ls-files` so
developers can keep ignored local working files while CI protects the durable source tree.
Use `make clean` to remove ignored local residue from tests, coverage, build output, and Python
bytecode caches. The cleanup utility prunes `.git`, `.venv`, and dependency cache directories, and
the CI contract gate fails if the Makefile cleanup path is weakened or removed.

The maintainability gate blocks oversized Python files/functions in source, test, and script
trees. It is calibrated above the current baseline so new agentic work must split or refactor
large additions instead of normalizing hard-to-review modules.

The private import boundary gate blocks direct imports from private helpers in
protected module surfaces: `app.domain.*` and
`app.application.implementation_proof_capability_updates`, and
`app.infrastructure.postgres_codecs`. Domain modules may use private local
helpers internally, shared proof-readiness composition uses public
`apply_blocker_proof` and `build_capability_readiness` functions, and
PostgreSQL repository code uses public row, JSON, datetime, and domain
serialization codec APIs. The gate is intentionally scoped to measured
boundaries and does not claim complete application-helper or adapter-internal
codec cleanup.

`make foundation-structure-gate` is the foundation-posture guard introduced by RFC-0002 Slice 2. It keeps
the current surface in foundation-only posture by checking the support registry,
README, repository context, RFC index, supported-features wiki, and this
validation page against the same planned-versus-supported truth. It also
reuses the architecture-boundary gate, including the domain ban on Pydantic DTO
framework imports, so design modularity stays internal and no runtime service
split is implied.

The monetary-float guard blocks money-like `float` annotations, literals, and
conversions in application source. It is AST-backed and intentionally allows
non-monetary operational floats, such as timeout seconds, so the guard protects
private-banking precision without creating noisy exceptions.

The no-sensitive-content guard scans local evidence, log, and output artifacts
for forbidden sensitive marker names such as portfolio, client, account,
holding, transaction, request-body, response-body, and raw entitlement failure
markers. It is blocking through `make lint` and has focused pass/fail unit
coverage so future evidence artifacts cannot quietly leak sensitive material.

The documentation contract gate blocks deletion, thinning, missing anchors,
placeholder text, and unstructured operator text dumps across the required
README, repository context, standards, runbooks, quality, evidence, and wiki
surfaces. Proof and readiness guides must keep a polished operator structure:
current-truth table, proof boundary, non-proof boundary, blockers,
response-shape table, implementation evidence, and executable example. The
gate keeps enterprise operating context intact for future implementation
agents without promoting any business capability.

The RFC-0002 GitHub issue execution ledger gate protects issue-lifecycle truth.
Open, partial, blocked, or merged-main-QA-pending execution issues must carry
`allowPullRequestAutoClose=false` and explicit `Keep #<issue> open` wording in
`contracts/implementation-proof/rfc0002-github-issue-execution-ledger.v1.json`.
Use this gate before opening or updating partial RFC PRs so source-contract or
evidence-consumption work cannot accidentally close live runtime, downstream,
publication, support, or supported-feature proof issues.

`make rfc0002-github-issue-execution-state-audit` is the GitHub-backed
companion audit. It calls the GitHub CLI and compares current GitHub issue
state, lifecycle labels, and `rfc/RFC-0002` label coverage with the repository
ledger. Run it before quoting RFC-0002 fixed/open counts, after issue
reopen/close/label corrections, and before final Slice 18 or Slice 20 closure
evidence. It fails if a GitHub issue is labeled `rfc/RFC-0002` but is missing
from the ledger, if a ledger issue loses the RFC label in GitHub, or if an
`open_tracker` parent issue lacks `status/tracker`. It is not part of offline CI
because it depends on GitHub state, but its parsing and failure modes are
unit-tested.

`make rfc0002-github-issue-pr-text-gate` prevents partial RFC PR title/body text
from mixing `Keep #<issue> open` with standalone GitHub auto-close keywords.
The target is no-op when PR text is not supplied locally; PR Merge Gate supplies
the GitHub pull-request title and body and fails early if a keep-open issue is
paired with verbs such as `fixes`, `closes`, or `resolves`. Use neutral verbs
such as `updates`, `records`, `reconciles`, or `addresses` until QA-backed
closure is intended. Negated issue references such as `does not close #681` are
also unsafe because GitHub still matches the closing keyword and issue
reference; say the PR `does not complete Slice 18` or use another neutral
non-issue-reference phrase.

When this gate fails, a manual PR body edit is necessary but may not be
sufficient for an Actions rerun. Reruns reuse the original pull-request event
payload, so push a small durable source correction or otherwise create a fresh PR
event before expecting the remote gate to observe corrected title/body text.
Run the gate as a fail-closed precondition before `gh pr create`, `gh pr edit`,
or any branch-head refresh intended to prove corrected PR text. PowerShell
automation must check `$LASTEXITCODE` immediately after the gate and exit on
failure; do not group the gate with a later GitHub mutation in a command block
that can continue after unsafe keep-open wording is rejected. This mirrors the
platform-wide guardrail from `sgajbi/lotus-platform#653` / PR #654.

`make rfc0002-github-issue-execution-summary` renders the source-controlled
RFC-0002 issue execution summary after the ledger and learning-pattern gates
pass. Use it for implementation handoff and issue-count reporting after the live
state audit, so active issue counts and learning-pattern lenses come from
durable source rather than chat memory or assignee-only filters. The Markdown
summary lists final-closure-pending and post-completion-pending issues
separately from ready, blocked, active, QA-pending, and tracker issues so
status reports cannot hide Slice 20 or Slice 21 work behind a generic ready
bucket.

Current Slice 18 handoff truth is anchored by `lotus-idea#681`. The source
ledger records the PR #765, #767, #768, #769, #770, #772, #775, #776, #777,
#779, #785, #787, #789, #790, and #791 historical evidence chain through exact
main `65e11890aaddb70fea4cf9d80e836ce1625a6c44`, Main Releasability
`30460122600`, Main CodeQL `30460101418`, wiki commit
`2453c3006722ee40e48762d884581fb6b3893bbe`, strict wiki parity, then-current
Idea RFC-0002 ledger posture of 42 tracked issues, 24 open, and 18 closed,
then-current cross-repo RFC-0002 posture of 77 tracked issues, 40 complete, and
37 open across 13 repositories, and a classified blocked posture of 26 blocked
issues, 0 app-actionable blocked issues, 5 Core dependencies, and 21
external/protected-evidence blockers. PR #803 later synchronized that posture to
43 tracked Idea RFC-0002 issues, 24 open, and 19 closed, with live cross-repo
RFC-0002 posture of 80 tracked issues, 43 complete, and 37 open across 13
repositories. PR #809 synchronized #807 final QA closure truth on Idea main
`c340daa01b41097410bbc8a802d9a8d1f9f24135`; exact-main Main Releasability
`30499444726` passed with lint/typecheck/security, unit, integration, e2e,
PostgreSQL runtime proof, combined coverage, Docker build, runtime smoke, image
scan, release identity/license evidence binding, and CI signal evidence.
PR #810 synchronized PR #809 main evidence and Core/Workbench handoff posture
on Idea main `fe7f0efac9fca86a3e19302e8b8436e8941f3d0c`; exact-main Main
Releasability `30500588217` passed with workflow lint, lint/typecheck/security,
unit, integration, e2e, PostgreSQL runtime proof, combined coverage,
Docker/release validation, image scan, commit-tagged image publish and digest
proof, published-digest runtime proof, image signing, provenance/SBOM
attestations, release metadata, release identity/license evidence binding, and
CI signal evidence. Repo-authored wiki publication reached `lotus-idea.wiki`
commit `f0f9293` with strict `DiffCount 0`. Current source truth after the
#814 Core-blocker sync records 54 tracked Idea RFC-0002 issues, 25 open, and
29 closed, with live cross-repo RFC-0002 posture of 93 label-backed tracked issues, 56
complete, and 37 open across 13 repositories after
`sgajbi/lotus-manage#626` closed with
`status/merged-main`. That dependency handoff was anchored on
`sgajbi/lotus-core#836`, `sgajbi/lotus-core#840`,
`sgajbi/lotus-workbench#500`, #685, and #686. Workbench #500 is now closed
with `status/merged-main` after Workbench PR #501 and Idea PR #837; current
active blockers are anchored by `sgajbi/lotus-core#882`,
`sgajbi/lotus-core#885`, #814, #685, and #686, while
`sgajbi/lotus-manage#626` records the closed Manage PR #627 tax-lot identity fix on
main `5ba2757c1235ce3e28c630afd44257327c91edf3` with Main Releasability
`30536615979` passing and branch cleanup complete.
Workbench PR #505 additionally records
merged BFF principal-boundary hardening while preserving production
IdP/session/token-claims and canonical browser proof blockers. #814 is now
blocked by reopened Core #836 after Idea PR #815, Workbench PR #515, and
Workbench PR #516 merged; the original authorization and Workbench validator
defects are no longer the active failure path. The latest canonical rerun
drained valuation and aggregation queues and reached current Core/Gateway dates,
but Core positions data quality remained `UNKNOWN`. It remains open until Core
readiness converges and fresh full canonical validation produces mainline
capacity-seed evidence.
PR #819 then reached Idea main
`3b2cc0bb4472a158cb4617b277276244c0e4a22b` with the then-current #380
Core-blocker reference synchronized to `sgajbi/lotus-core#856`. Main Releasability
`30555536256` and CodeQL `30555528134` passed for that exact SHA; wiki source
did not change in that tranche and strict parity stayed `DiffCount 0`. Current
governed posture remains 54 tracked Idea RFC-0002 issues, 25 open, and 29
closed; cross-repo RFC-0002 posture remains 93 label-backed issues, 37 open,
and 56 closed, split into 27 blocked, 2 in-progress, and 8 tracker issues. The
blocked subset remains 27 blocked issues, 0 app-actionable blocked issues, 4
Core dependencies, and 23 external/protected-evidence blockers after fresh
canonical validation reopened `sgajbi/lotus-core#836` as the active Core
positions data-quality metadata blocker.

PR #824 then synchronized the Core #836 canonical QA-failure posture to Idea
main `f4904af523cb2e54cd18db0c5eb71c8725998df8`. Exact-main Main
Releasability `30620242970` and CodeQL `30620237795` passed for that SHA,
including release-image build/smoke/scan, image push, digest inspection,
signing, provenance/SBOM attestations, release manifest, and release evidence
upload. Repo-authored wiki source was published to `lotus-idea.wiki` commit
`5e63705` with strict `DiffCount 0`, and local/remote branch cleanup completed
with no unmerged remote branches. This is Slice 18 source-truth synchronization
only; #681 and the remaining blocker issues stay open.

PR #825 then synchronized PR #824 merged-main evidence to Idea main
`8e76736148e9cd2078a1adfd692884da7d78a95f`. PR Merge Gate `30621485539`,
post-merge Main Releasability `30621899968`, and post-merge CodeQL
`30621893764` passed. Repo-authored wiki source was published to
`lotus-idea.wiki` commit `eefd44a` with strict `DiffCount 0`; the remote PR
branch was deleted, the local feature branch was deleted after exact
tree-equivalence verification, the local branch list contained only `main`, and
no unmerged remote branches remained. This is Slice 18 source-truth
synchronization only; #681 remains open and no Core readiness, canonical browser
proof, production identity/session-token authority, supported-feature
promotion, client-publication, or final RFC-0002 closure is claimed.

PR #826 then synchronized PR #825 source truth to Idea main
`6fd8159495ca3a7294ade2d819c80ea6aaa350fd`. PR Merge Gate `30623781720`,
Feature Lane `30623778382`, CodeQL `30624121200`, and exact-main Main
Releasability `30624125739` passed. Repo-authored wiki source was published to
`lotus-idea.wiki` commit `272f7cf` with strict `DiffCount 0`; remote branch
cleanup completed, the local feature branch was absent after fetch/prune, the
local branch list contained only `main`, and no unmerged remote branches
remained. #681 returned to `open_in_progress` because Slice 18 remains a
continuing synchronization issue. This is merged-main evidence synchronization
only; no Core readiness, canonical browser proof, production identity/session
authority, supported-feature promotion, client-publication, or final RFC-0002
closure is claimed.

The 2026-07-31 writable-dependency audit keeps that posture intact. Current-main
focused validation passed in the owning repositories for platform
cost-attribution and BFF principal-session source contracts, lotus-ai Idea
workflow-pack and provider-retention seams, Manage temporal receipt/action
intake, Report Idea evidence intake/materialization and retention policy,
Archive Idea lifecycle decisions, and Workbench opportunities/BFF action
controls. Durable evidence is recorded on the owning GitHub issues and
coordinated through `lotus-idea#681`. These checks are source-side evidence
only; the issues stay open where production identity, Core readiness,
protected FinOps/runtime, provider/model-risk, legal/lifecycle, canonical
browser, client publication, supported-feature, or final closure proof remains.
Keep #681 open until the remaining documentation, wiki,
support, context, and supported-feature truth is complete;
`sgajbi/lotus-manage#624` remains the production trusted IdP caller-context
boundary, and production vulnerability
posture remains uncertified until release evidence exists.

`make rfc0002-cross-repo-issue-posture` now renders blocker actionability from
`contracts/implementation-proof/rfc0002-cross-repo-blocker-classification.v1.json`.
It also lists every blocked issue with the GitHub URL, actionability, blocker
class, and remaining authority so the Core-vs-protected/external split is
auditable without chat memory or one-off GitHub queries.
Current live posture is 205 label-backed RFC-0002 issues across 13
repositories: 167 closed and 38 open. The open split is 25 `status/blocked`,
0 `status/fixed-local`, 1 `status/in-progress`, 1 `status/merged-main`, 2
`status/merged-to-main`, 1 `status/pr-open`, 8 `status/tracker`;
`sgajbi/lotus-idea#1104` is PR-open for Slice 19 supported-feature gate fixture
hardening; `sgajbi/lotus-idea#1101` is closed after PR #1102 for AI workflow evaluator
hardening. `sgajbi/lotus-idea#1098`,
`sgajbi/lotus-idea#1094`, `sgajbi/lotus-idea#1091`,
`sgajbi/lotus-idea#1088`, and `sgajbi/lotus-idea#1084` are the latest
QA-closed Idea maintainability hardening issues after local, PR, or
exact-main validation, wiki publication where required, and branch cleanup
where applicable.
`sgajbi/lotus-idea#681` remains the Slice 18 synchronization issue and has PR
#1097 open; older QA-closed hardening issues remain in the
execution ledger and are not repeated here as current work.
Blocked actionability remains 0 app-actionable blocked issues, with 25
external/protected/canonical-proof evidence blockers. Counts are label-backed
by `rfc/RFC-0002`; title-only references are reported separately and excluded
from governed counts unless deliberately labeled and ledgered. This
keeps “blocked” aligned to Core, IdP/session authority, protected runtime or
deployment evidence, provider/bank/legal approval, or certification proof. If a
writable non-Core app-code gap appears, it should not remain blocked; it should
move to ready or in-progress and receive implementation/PR evidence.

The RFC-0002 issue-learning pattern gate keeps repeated defect lessons
source-controlled. `contracts/implementation-proof/rfc0002-issue-learning-patterns.v1.json`
maps every non-complete RFC-0002 execution issue to at least one learning
cluster, durable control, future-agent rule, and non-claim boundary.
`make rfc0002-github-issue-learning-pattern-gate` is part of `make lint`; it
does not call GitHub, but it prevents new RFC execution work from escaping the
same-pattern review lens.

The quality-scorecard gate keeps the bank-buyable control matrix executable. It
requires the standard control rows, approved readiness statuses, non-empty
evidence/gap/next-slice cells, implementation-backed evidence anchors, and
stale scaffold-era underclaim detection after internal API, persistence,
observability, and test foundations have landed.

The source-observability contract gate blocks ad hoc application logging in
`src/app`. Feature code must use bounded operation events or the central
request diagnostic helper rather than raw `print()`, direct Python logging, or
low-level `log_event` calls. Request diagnostics log route templates rather
than raw URL paths. It also blocks source adapters from inferring current
freshness from readiness, supportability, coverage, health-state,
data-quality, or `ready` predicates; current freshness must be explicitly
source-authored as freshness metadata.

The API route metadata gate blocks local `RouteMetadata` and
`SignalRouteMetadata` clones in route modules so route registration metadata
uses the shared `app.api.route_metadata.RouteMetadata` contract. The
API CamelModel boundary gate blocks route-local `CamelModel` and
`ConfigDict(populate_by_name=True)` clones so camel-case DTO alias handling uses
`app.api.base_model.CamelModel`. The API signal model boundary gate blocks shared
source-ref, review access scope, source-ref response, and candidate summary DTOs
from being imported through concrete signal route modules; those DTOs live in
`app.api.signal_models`. This is design modularity inside one deployable
service, not a runtime signal microservice or supported-feature promotion. The
ProblemDetails boundary gate blocks API route modules and the app entrypoint
from importing low-level `app.errors` directly, keeping runtime ProblemDetails
helpers behind `app.api.problem_details`. The OpenAPI ProblemDetails example
gate blocks public `ProblemDetails` responses that lack product-safe examples.
Workflow and operator routes plus app-entrypoint exception handlers use
`app.api.problem_details` for concrete 400/403/404/409/503 examples;
caller-supplied signal routes keep their stricter route-family metadata in
`app.api.signal_api_support`.

When one HTTP status can return multiple stable `ProblemDetails` codes, route
metadata must merge named examples instead of spreading duplicate response keys.
`tests/unit/test_api_problem_details.py::test_downstream_submission_openapi_problem_codes_match_runtime_contract`
guards the downstream submission routes so generated OpenAPI preserves
runtime codes such as `downstream_realization_not_configured`,
`durable_repository_unavailable`, `unsupported_downstream_realization_target`,
and `idempotency_conflict`.

The signal API contract gate blocks duplicated caller-supplied signal API
authorization, source-authority, operation-event, and error-model mechanics.
Signal routes must use shared signal API support, including the ordered
`evaluate_caller_supplied_signal` boundary, and that support must require both
advisor role and `idea.signal.evaluate` capability before source-owned evidence
evaluation. This keeps DTO mapping, application evaluation, domain policy, and
source-contract checks in a predictable path so future slices do not reintroduce
copy-pasted policy, role-only authorization, or inconsistent problem-detail
behavior.

The caller-context contract gate also covers adjacent protected API modules,
including nested route packages under `src/app/api/**`. When a route policy
declares both `allowed_roles` and an `idea.*` capability, the route must use
`require_role_and_capability`. This preserves the same least-privilege posture
for advisor queue, candidate detail, outbox, and operator route families
instead of letting broad role membership substitute for a published operation
capability. It also requires typed caller-boundary exceptions, exact stable
codes and bounded error categories, preservation by the global handler,
RFC 7807 runtime media, and generated 400/403 examples under both supported
media types for every protected operation. Mutation tests fail when any one of
those layers is weakened.

The API idempotency boundary gate blocks route-local `Idempotency-Key`
validator clones and verifies generated OpenAPI for certified idempotent
mutations. A route listed in `app.api.idempotency` must publish
`Idempotency-Key` as a required header with no default value, even when the
runtime keeps product-specific validation inside the route handler.

The review identity contract gate protects the distinct business-resource
boundary. It requires application prechecks before domain mutation, repeated
adapter enforcement, identity claims before PostgreSQL candidate mutation,
typed collision retry, named OpenAPI conflict examples, and the architecture
standard. Its mutation test fails if atomic review identity claiming is removed.

The conversion outcome contract gate protects source-event identity and
lifecycle independently of transport retries. It requires bounded application
prechecks, repeated provider enforcement, atomic PostgreSQL ID/version claims,
legacy-history quarantine, current-posture validation, named OpenAPI conflict
examples, and the architecture standard. Its mutation test fails if atomic
outcome claiming is removed.

`make postgres-integration-gate` adds the behavioral proof: two connections
race equivalent outcome identity and competing versions, and a migration test
proves contradictory legacy rows remain intact while quarantine and readiness
fail closed. These checks do not certify downstream route execution,
Gateway/Workbench behavior, data-mesh promotion, or supported features.

The operation-metric contract gate validates
`contracts/observability/lotus-idea-operation-metrics.v1.json` against the
code-owned operation, outcome, supportability, and metric-label vocabulary. It
blocks sensitive labels and prevents the metric catalog from being rewritten as
dashboard certification, alert certification, data-mesh certification,
Gateway/Workbench proof, or supported-feature promotion.

The AI model-risk operations contract gate validates
`contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`
against implemented AI explanation and readiness telemetry. It blocks missing
dashboard controls, missing alert candidates, sensitive labels, unsupported
operation names, missing source-of-truth paths, and premature model-risk
dashboard, alert, `lotus-ai`, Workbench, or supported-feature certification
claims. The companion source-contract proof gate validates file content and
adds a readiness evidence reference, but clears no blocker and cannot prove
dashboard provisioning, rule evaluation, alert delivery, or deployment.

The operator workflows operations contract gates validate
`contracts/observability/lotus-idea-operator-workflows-operations.v1.json`
and the repo-owned Grafana dashboard, Prometheus alert rules, and runbook for
source ingestion, outbox delivery, downstream realization, runtime trust, and
implementation-proof readiness telemetry. They block unsupported operation
names, sensitive labels, missing runbook refs, unimplemented metrics, and
premature live-source, external-broker, downstream-execution,
Gateway/Workbench, data-mesh, or supported-feature claims. The proof artifact
is classified as `source_contract`, adds provenance without clearing aggregate
blockers, and rejects claims of dashboard provisioning/query execution,
alert-rule loading/evaluation/delivery, deployment, or production
certification.

The AI workflow-pack registration proof contract gate validates the bounded
cross-repo `lotus-ai` workflow-pack registration source contract consumed by
aggregate implementation-proof readiness. It checks source-safe evidence refs,
sibling registry/binding/queue-policy/supportability/test coverage,
`source_contract` classification, empty blocker clearance, and explicit
non-execution/non-deployment posture. Runtime registry observation, provider
invocation, model-risk operations certification, Workbench proof, and
supported-feature promotion remain blocked.

The implementation-truth gate scans README, repository context, operations/demo docs, quality docs,
and wiki source for unqualified current-state claims that imply demo readiness, production support,
certification, live source ingestion, Gateway/Workbench support, or client-ready publication while
no supported feature is implemented. RFC target-state planning text is excluded; current-state
surfaces must describe unsupported, planned, blocked, or evidence-required posture explicitly. The
gate also blocks stale scaffold-era underclaims in demo documentation when current implementation
and CI evidence prove a stronger foundation, so future agent work cannot leave outdated scaffold
truth behind while adding real APIs or gates.

The endpoint-certification gate blocks weak certified API posture. It keeps the OpenAPI surface and
endpoint certification ledger synchronized, validates JSON-shaped examples, proves test evidence
references resolve to real pytest functions, keeps health/metadata routes at `baseline_certified`,
and requires certified business/operator endpoints to name an `idea.*` capability, document
product-safe 403 behavior, cite the OpenAPI quality gate, and preserve Gateway, Workbench, and
supported-feature-promotion boundaries. It also requires bounded operation-event test evidence for
every certified business/operator endpoint, so API certification and operator telemetry proof stay
coupled. Certified business/operator endpoints must also cite at least one non-operation-event
integration API behavior test and at least one negative or degraded-path test. That keeps endpoint
promotion aligned to the test pyramid instead of allowing schema examples, unit-only assertions, or
telemetry-only evidence to stand in for executable API behavior. When an endpoint has implemented
bounded read-only Gateway publication, the gate requires the ledger to cite the exact
`lotus-gateway` route and still preserve Workbench, data-product, client-ready publication, and
supported-feature boundaries. For every certified endpoint that names an `idea.*` capability, the
gate also validates generated OpenAPI caller-context publication: `LotusCallerContext` security,
`x-lotus-caller-context` required capabilities, trusted caller-context provenance wording, and
descriptions for the key caller-context headers.

The signal API contract gate blocks weak caller-supplied opportunity signal API posture. It requires
shared advisor-role plus `idea.signal.evaluate` authorization, source-authority, operation-event,
outcome-mapping, and product-safe 400/403 `ProblemDetails` OpenAPI response metadata, so new signal
families cannot introduce copy-pasted role-only authorization or weaker error-model documentation.
Runtime route code now separately validates caller-supplied source refs against each route's
governed source contract before domain evaluation, so copied route families cannot accept a valid
shape from the wrong source authority or data product.

Core-backed source routes additionally require exactly one trusted caller
tenant before runtime construction. The tenant is carried through the
application command and Core source port, into tenant-aware Core snapshot
payloads, and into candidate access scope, deterministic identity, and
generated ingestion identity. The source adapter rejects blank values, does
not supply a production default, and does not invent parameters for Core routes
that are not tenant-aware. The blocking `signal-api-contract-gate` checks route
opt-in; `trusted-tenant-context-gate` checks the full API-to-adapter and
persistence contract. Integration tests prove tenant A/B isolation plus
missing, ambiguous, untrusted-header, and request-body override rejection
without calling Core under the wrong scope. Operation events expose only a
bounded scope-provenance enum; raw tenant IDs are forbidden attributes and
metric labels.
The same gate requires every Core live-proof CLI to accept explicit
`--tenant-id` and pass it into the typed source request. Worker manifests and
proof fixtures carry `tenantId`, preventing local tests or certification
automation from reintroducing an implicit production tenant.

Data-mesh foundation checks:

1. repo-owned proposed producer and consumer declarations must exist,
2. mesh placeholder files must not exist in contract or operations paths,
3. planned trust telemetry must remain blocked and `not_certified`,
4. SLO, access, and evidence policies must be present before promotion work,
5. optional sibling platform catalog/source-manifest evidence is used to catch
   source-product drift and validate governed `lotus-idea` onboarding without
   treating catalog visibility as certification,
6. `make platform-catalog-source-contract-proof-gate` validates the bounded
   cross-repo v3 `source_contract` when a sibling `lotus-platform` checkout is
   available. It checks closed fields, exact blocker scope, explicit false
   runtime/certification claims, repository/ref/SHA-256 authority for the
   source manifest, catalog, dependency graph, and maturity matrix, and the
   unpromoted platform posture where `IdeaCandidate:v1` may be a non-blocking
   certification candidate while all Idea producer products remain proposed. The
   aggregate readiness command generates an invalid non-proof artifact and
   keeps blockers when sibling platform evidence is absent,
7. the sibling [Lotus Data Mesh Standard](https://github.com/sgajbi/lotus-platform/blob/main/docs/standards/Lotus%20Data%20Mesh%20Standard.md)
   remains the controlling platform rule,
8. platform mesh certification is required before any supported mesh claim.

The internal data-mesh-readiness endpoint is covered by OpenAPI, endpoint
certification, unit tests, and integration tests. Its passing checks certify the
diagnostic route only; they do not certify the data products it reports as
blocked. The endpoint's blocker contract is part of the anti-promotion control
and must continue to name SLO certification, access-policy certification,
evidence-policy certification, Gateway/Workbench runtime discovery evidence,
and supported-feature promotion until those are implementation-backed and
platform-certified. Source-manifest and catalog-inclusion blockers may be
cleared only by a valid, current platform catalog source contract. That
contract is not runtime publication, policy certification, platform mesh
certification, product activation, Gateway/Workbench discovery, deployment,
production certification, or supported-feature evidence.

The internal runtime trust telemetry preview endpoint is covered by OpenAPI,
endpoint certification, unit tests, integration tests, and a repo-native
generator check. Its passing checks certify source-safe pre-certification
telemetry preview only; they do not certify data products, platform
source-manifest inclusion, Gateway/Workbench discovery, or supported-feature
promotion.

The internal runtime trust telemetry snapshot endpoint is covered by OpenAPI,
endpoint certification, unit tests, integration tests, and a repo-native
generator check. The repo-native generator check uses a deterministic
source-safe local/test candidate exercise so it proves candidate-presence
coverage without relying on process-local residue from another command. Its
passing checks certify only that source-safe, contract-shaped snapshot evidence
can be emitted while remaining blocked, non-durable, and not certified.

The internal source-ingestion-readiness endpoint is covered by OpenAPI,
endpoint certification, unit tests, and integration tests. Its passing checks
certify the diagnostic route only. A valid proof artifact can clear only the
live-Core-source blocker; the route still does not certify scheduled execution,
long-running scheduled runtime, data-product
promotion, Gateway/Workbench support, or supported-feature promotion.
Scheduler source and deployment contracts are covered separately by
`make source-ingestion-scheduled-worker-check`. Source declarations are
non-clearing `source_contract` evidence. Only deployment evidence that binds
the exact source contract, immutable image, Git revision, environment,
controller run, and completed workload rollout may clear the scheduler
deployment blocker. Aggregate readiness records both validated references and
keeps scheduled execution, production certification, and product support
blocked.
The internal source-ingestion-run-once endpoint is covered by OpenAPI,
endpoint certification, unit tests, and integration tests. Its passing checks
certify the bounded operator action only; they do not certify live Core
ingestion, scheduler deployment or execution, long-running
scheduled runtime, data-product promotion, Gateway/Workbench support, or
supported-feature promotion.

The internal advisor-queue-readiness endpoint is covered by OpenAPI, endpoint
certification, unit tests, and integration tests. Its passing checks certify
the diagnostic route, durable PostgreSQL repository-side page projection, and
durable PostgreSQL readiness aggregate projection only; they do not certify
Gateway/Workbench support, data-product promotion, PM/compliance queue support,
client-ready publication, or supported-feature promotion.

The internal outbox-delivery-readiness endpoint is covered by OpenAPI,
endpoint certification, unit tests, and integration tests. Its passing checks
certify the diagnostic route and durable PostgreSQL repository-side outbox
status/due-ready-count projection only; they do not certify external broker
publication, downstream delivery, platform mesh event publication,
Gateway/Workbench support, client-ready publication, or supported-feature
promotion.

The internal AI-explanation-readiness endpoint is covered by OpenAPI, endpoint
certification, unit tests, and integration tests. Its passing checks certify
the diagnostic route only; they do not certify `lotus-ai` runtime execution,
provider invocation, Gateway/Workbench support, data-product promotion,
client-ready publication, or supported-feature promotion. The AI lineage store
proof is consumed only by aggregate implementation-proof readiness. The AI
model-risk operations source-contract proof validates repo-owned dashboard, alert-rule, and
runbook artifacts against implemented operation telemetry while still leaving
`lotus-ai` runtime, live provider, Workbench, client-ready, and supported-feature
gaps unpromoted.

The internal outbox-delivery-readiness and outbox-delivery-run-once endpoints
are covered by OpenAPI, endpoint certification, unit tests, and integration
tests. Passing checks certify the diagnostic route and bounded operator action
only; they do not certify live broker runtime, downstream consumer delivery,
platform-mesh event runtime publication evidence, Gateway/Workbench support, data-product
promotion, client-ready publication, or supported-feature promotion.

`make outbox-recovery-contract-gate` protects operator authorization,
idempotent one-attempt recovery, source-safe responses, immutable failure
history, and exact PostgreSQL opaque-reference selection. It rejects the prior
fixed-window scan pattern. The required PostgreSQL runtime lane additionally
proves migration execution, qualified delivery claim SQL, dead-lettering,
connection reload, exact recovery claim, durable audit replay, and
rollback/reapply. These checks certify local recovery control only, not broker
publication or downstream receipt.

The internal downstream-realization-readiness endpoint is covered by OpenAPI,
endpoint certification, unit tests, and integration tests. Its passing checks
certify the diagnostic route only; planned contract records are not downstream
route-existence proof. Report intake and materialization source-contract
artifacts clear no blocker. These checks do not certify report-job execution,
rendered output, archive creation, Advise suitability,
Manage rebalance/action authority, Gateway/Workbench support, data-product
promotion, authorize client publication, or promote a supported feature.

The downstream-realization contract gate validates
`contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`.
It blocks missing contract rows, owner/source-authority drift, current-route
claims, premature certification, missing blockers, and missing evidence refs.
Its passing checks certify contract-plan hygiene only; they do not prove
downstream route existence or execution.

## Candidate-State Contract Gate

`make candidate-state-contract-gate` protects the
`idea-candidate-state-v1` lifecycle/review-posture matrix across domain
construction, transition normalization, review actions, PostgreSQL queue
quarantine, migration/rollback, stable API diagnostics, and the architecture
standard. Matrix, terminal-action, legacy JSON, raw-row queue, API telemetry,
and migration tests provide behavioral evidence; the gate prevents future
agents from deleting one enforcement layer while leaving documentation claims
behind.

This gate proves the internal invariant only. It does not promote review
features, certify Gateway/Workbench behavior, validate the migration constraint
against production data, or publish supported-feature truth.

## Review Queue Snapshot Contract Gate

`make review-queue-snapshot-contract-gate` protects the advisor queue temporal
contract across application command, repository port, PostgreSQL adapter, SQL,
API query, response metadata, and stable error codes. It requires candidate
created-at filtering, opaque snapshot identity, continuation-token enforcement,
and an adapter-side before/after fingerprint comparison.

Behavioral proof is broader than the static gate:

1. domain/application tests cover exact timestamp equality, future exclusion,
   source-date non-reinterpretation, and stale continuation conflict,
2. API tests cover missing, malformed, stale, and future-insert cases,
3. fake PostgreSQL tests prove query parameter and fingerprint behavior,
4. `make postgres-integration-gate` proves the same traversal semantics against
   a real migrated PostgreSQL database.

Passing this gate certifies the internal paging contract only. It does not
certify Workbench behavior, data-product support, client publication, or a
supported feature.

## RFC-0002 Current Execution Posture

RFC-0002 execution is tracked through GitHub issue state plus the
source-controlled implementation-proof ledgers. The current governed posture is
205 label-backed RFC-0002 issues across 13 repositories: 167 closed and 38 open.
The open set is 25 `status/blocked`, 0 `status/fixed-local`, 1 `status/in-progress`, 1 `status/merged-main`, 2 `status/merged-to-main`, 1 `status/pr-open`, 8 `status/tracker`,
and 0 app-actionable blocked issues. #1104 is PR-open for Slice 19 supported-feature
gate fixture hardening; #1101 is closed after PR #1102 for AI workflow
evaluator hardening; #1098 is the latest
release-CI hardening closure; #1094, #1091, #1088, and #1084 are the
latest closed Idea maintainability hardening issues, while #681 remains open
after PR #1097 merged.
Idea PR #838 synchronized PR #837 exact-main evidence to main
`2c2d35667643ad5efae83924475574ab6c16be03`, passed Main Releasability
`30723235065`, and published wiki source to `lotus-idea.wiki` commit
`ee15dc3`. Idea PR #839 synchronized PR #838 merged-main evidence to main
`71867084c2832d053342db048557e03720a3773a`, passed Main Releasability
`30724145516`, published wiki source to `lotus-idea.wiki` commit `c2258e6`,
completed branch cleanup, and returned #681 to `status/in-progress` because
Slice 18 remains a continuing synchronization issue.
Idea PR #842 synchronized PR #841 evidence to main
`4e2dd20c3f1b7f17a30eda016e79c62e631b2a2f`, passed exact-main Main
Releasability `30727100273` and CodeQL `30727098069`, and had no wiki-source
change. Idea PR #843 merged the posture-snapshot documentation guard to main
`2ed353b0394a625dd212b437fb93c0d5d4c02a89`, passed exact-main Main
Releasability `30728039165` and CodeQL `30728037050`, published wiki source to
`lotus-idea.wiki` commit `87dd4e4` with strict DiffCount 0, and completed
branch cleanup.
Idea PR #844 synchronized PR #843 evidence to main
`c21deeb55dcb1d46395c02c95053ab6149ef6ad6`, passed exact-main Main
Releasability `30728738511` and CodeQL `30728733346`, published wiki source to
`lotus-idea.wiki` commit `b47cbcb` with strict DiffCount 0, recorded final
#681 GitHub evidence in the
[#681 PR #844 final evidence comment](https://github.com/sgajbi/lotus-idea/issues/681#issuecomment-5154685336),
and completed branch cleanup.

Evidence-only Slice 18 synchronization PRs must not create an infinite
source-sync loop merely to record their own post-merge proof. Their final proof
is durable when recorded as a #681 GitHub issue comment with PR URL, merged main
SHA, exact-main Main Releasability run, wiki publication or no-wiki-change
decision, and branch/worktree hygiene. PR #845 is the current example, recorded
in the
[#681 PR #845 final evidence comment](https://github.com/sgajbi/lotus-idea/issues/681#issuecomment-5154811626).
Implementation truth, blocker state, support posture, wiki source, context, or
policy changes still require source-controlled ledger/docs/wiki/context updates.

Platform PR `sgajbi/lotus-platform#646` merged the reusable keep-open PR
guidance hardening to platform main
`c041a7e13358feb322b8e92b3827f3ed2a834b43`, with exact-main Main
Releasability run `30731910564` passing. The platform-owned
`gh-issue-fix-qa-loop`, `lotus-pr-premerge-gate`, and `PR-LOOP-PLAYBOOK.md`
now reject negated closing-keyword issue references for keep-open PRs, and
platform tests cover the rule across the issue-loop, premerge, and PR-loop
surfaces. This is execution-control guidance only; it does not clear RFC-0002
product, Core, protected-evidence, supported-feature, or final-closure
blockers.

The blocked-actionability classifier reports 0 app-actionable blocked issues.
The blocked set is currently 25 external/protected/canonical-proof evidence
blockers. Core `sgajbi/lotus-core#882` and `sgajbi/lotus-core#885` closed on
2026-08-09 and are no longer live blocker-classifier rows. The canonical
Workbench/Idea live proof path now requires fresh PB_SG_GLOBAL_BAL_001
Gateway-backed queue/detail/action evidence after those Core fixes, not stale
artifacts or downstream hash fabrication. Source-side Workbench action-control
tests do not replace full-stack machine-readable validation output,
screenshot/index evidence, or final supported-feature promotion proof.
`sgajbi/lotus-core#917` is open as `status/in-progress` for the core-side
report-only pilot of the platform technology-governance policy introduced by
`sgajbi/lotus-platform#595` and PR #652.

Platform protected-lane queue hygiene is separate from protected evidence. The
stale queued Platform End-to-End Validation run `30603744637` was recorded on
`sgajbi/lotus-platform#599`, cancelled, and the post-cancel detector returned
`Stale workflow runs: 0`. That cleanup improves queue clarity only; it does not
provision a protected runner, certify cost attribution, prove deployment
promotion, or clear RFC-0002 production-readiness blockers.

2026-08-09 SGT execution posture refresh:

1. `make rfc0002-github-issue-execution-state-audit`, `make
   rfc0002-github-issue-execution-summary`, and `make
   rfc0002-cross-repo-issue-posture` passed from current `lotus-idea` main.
2. The current Idea ledger has 58 tracked RFC-0002 issues, 32 closed and
   26 open after adding `#871` for the execution-ledger gate-policy refactor.
3. At that sync point, the governed cross-repo posture was 127 label-backed
   RFC-0002 issues across 13 repositories, 88 closed and 39 open: 25 blocked,
   no PR-open issues, 2 in-progress issues (`#681` and `#871`), 4
   merged-main or merged-to-main QA-pending dependencies, and 8 tracker issues.
4. The blocked-actionability classifier reported 0 app-actionable blocked
   issues; the remaining blocked issues require production identity/session
   authority, protected runtime/deployment evidence, provider/bank/legal
   approval, final-closure prerequisites, or certification evidence.
5. `sgajbi/lotus-core#882`, `#885`, and `#917` are closed with
   `status/merged-main`; they no longer justify app-code blocking by
   themselves. Fresh canonical Workbench/Gateway/Idea proof is still required
   before #814/#685/#686 can close.
6. `#871` later closed as a Slice 18 maintainability issue. It keeps static
   RFC-0002 execution-ledger gate policy in a versioned contract while Python
   remains responsible for validator behavior.
7. The policy refactor does not change supported-feature posture, product
   certification, production identity, or protected runtime evidence.
8. `sgajbi/lotus-platform#653` closed through PR #654 on platform main
   `e0ad0596afcda7bc8cf33909f8ece04b1d944647` after Main Releasability
   `31256159863` passed. The durable lesson is execution hygiene only: partial
   RFC PR text gates must fail closed before PR mutation and PowerShell scripts
   must check `$LASTEXITCODE` immediately.
9. `sgajbi/lotus-platform#647` remains open/blocked for protected/self-hosted
   runner capacity. Stale scheduled run `31235891576` was cancelled and the
   detector returned zero stale runs, but this queue hygiene does not clear
   protected evidence.
10. Current Core main release instability is tracked outside RFC-0002 through
   Core `#795` for same-SHA `Performance Load Gate (Full)` drain timeout; the
   earlier PR #897 merge-SHA migration rollback failure is already represented
   by Core `#730` / PR #899.
9. 2026-08-08 stranded-truth reconciliation first found only active Dependabot
   `cryptography-50.0.0` branches touching `pyproject.toml`, with no unique
   RFC, docs, wiki, context, contract, or workflow truth.
10. The same source-sync PR incorporated the runtime dependency security
    remediation by pinning `cryptography==50.0.0`, because GitHub PR Merge Gate
    `security-audit` reported `cryptography 49.0.0` as vulnerable with fixed
    version `50.0.0`.

2026-08-09 SGT Workbench and Manage exact-main refresh:

1. Workbench PR #555 merged `sgajbi/lotus-workbench#549`, `#550`, `#556`, and
   `#557` to main `afd0474524f20bc7d001ccb764a6e587f81d02c5`.
2. Workbench Main Releasability run `31285317629` passed for that exact SHA,
   including workflow lint, lint/typecheck/coverage/build, Playwright smoke,
   Docker build/security/SBOM, and CI-local Docker parity.
3. Manage PR #631 moved `sgajbi/lotus-manage#629` to `status/merged-main` on
   main `a6bc609f379b8efadb226c9a2084d7c97b2e26e7`; Main Releasability run
   `31268949391` passed for that exact SHA.
4. Then-current live `make rfc0002-cross-repo-issue-posture` reported 124 label-backed
   RFC-0002 issues across 13 repositories: 75 closed and 49 open. The open set
   is 28 blocked, 1 in-progress issue (#681), 10 `status/merged-main`, 2
   `status/merged-to-main`, and 8 tracker issues.
5. Blocked actionability remained 0 app-actionable blocked issues: 6 Core
   dependencies and 22 external/protected-evidence dependencies.
6. This was source-truth synchronization only. It did not close QA-pending
   merged-main issues, clear the remaining runtime/protected-evidence blockers, promote supported features,
   certify product support, or replace production identity/session authority,
   protected runtime, provider, legal, client-publication, support, or final
   RFC-0002 closure evidence.

2026-08-09 SGT Core blocker closure sync:

1. Live `make rfc0002-cross-repo-issue-posture` now reports 128 label-backed
   RFC-0002 issues across 13 repositories: 91 closed and 37 open.
2. Open status is 25 `status/blocked`, 0 `status/fixed-local`, 1 `status/in-progress`
   (`sgajbi/lotus-idea#681`), 2
   `status/merged-main`, 2 `status/merged-to-main`, and 8 `status/tracker`.
3. Blocked actionability remains 0 app-actionable blocked issues. The live
   blocker classifier contains 25 external/protected/canonical-proof evidence
   blockers and no Core dependency rows.
4. `sgajbi/lotus-core#882` and `sgajbi/lotus-core#885` are closed. Idea
   `#814`, `#685`, and `#686` now require fresh governed runtime evidence for
   Idea seed, Gateway-backed Workbench queue/detail reads, and browser
   review-action/feedback/conversion-intent controls.
5. `sgajbi/lotus-core#917` is closed with `status/merged-main` after Core PR
   #929 reached exact main `6bc937bb173051e0bd4ee9a07ffebd54face0163` and
   Main Releasability run `31308743764` passed. This is report-only
   technology-governance pilot evidence; it does not certify production
   vulnerability posture or promote any Lotus Idea supported feature.

This refresh is coordination and evidence hygiene only. It does not clear
RFC-0002 blockers, promote supported features, certify product support, or
replace Core, production identity, protected runtime, provider, legal,
client-publication, support, or final closure evidence. The dependency pin
change is limited to governed vulnerability posture.

2026-08-09 SGT #871 closure-truth sync:

1. Idea PR #872 merged the RFC-0002 execution-ledger gate-policy refactor to
   Idea main `f7aca4746e16d3d851c892654a8007743d7ec87a`.
2. Main CodeQL `31321978400` and exact-main Main Releasability `31321981636`
   passed, including workflow lint, lint/typecheck/security,
   unit/integration/e2e, PostgreSQL runtime proof, combined coverage,
   Docker/release validation, image scan, SBOM, signed published image digest,
   provenance/SBOM attestations, release metadata manifest, and release
   identity/license binding.
3. Repo-authored wiki source was published to `lotus-idea.wiki` commit
   `852ba82` with strict `DiffCount 0`.
4. The Idea ledger now has 59 tracked RFC-0002 issues, 34 closed and 25 open;
   `#681` is the in-progress Slice 18 tracker. Live cross-repo posture has
   128 label-backed RFC-0002 issues, 91 closed and 37 open, with 25
   `status/blocked`, 0 `status/fixed-local`, 1 `status/in-progress`, 1 `status/pr-open`, and 0 app-actionable blocked
   issues.
5. This sync closes only the ledger-gate maintainability issue. It does not
   close Workbench/Gateway runtime-proof blockers, production identity/session
   blockers, protected runtime evidence, supported-feature promotion, or final
   RFC-0002 closure.

CI warning policy:

1. use current approved action versions,
2. pin actions to verified immutable upstream tag SHAs with readable version comments,
3. fix owned warning sources,
4. suppress only known upstream runner noise with an explicit rationale,
5. do not downgrade action versions to make logs quieter.

Branch hygiene policy:

1. after a PR is merged to `main`, delete the remote feature branch,
2. delete the corresponding local feature branch,
3. re-run branch audits before final closure,
4. keep no durable RFC/docs/wiki/context truth outside `main`.

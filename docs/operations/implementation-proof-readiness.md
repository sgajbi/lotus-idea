# Implementation Proof Readiness

| Field | Current Truth |
| --- | --- |
| Status | Certified internal operator diagnostic |
| Audience | Operators, implementation reviewers, demo leads, and release reviewers |
| Required role | `operator` |
| Required capability | `idea.implementation-proof.readiness.read` |
| Required query | Timezone-aware `evaluatedAtUtc` |
| Supportability | `not_certified` while blockers remain |
| Product claim | Bounded live source-ingestion, runtime trust telemetry, digest-bound Advise/Manage/Report route source contracts, Advise idea-intake runtime execution, Report materialization, outbox broker/consumer/platform-mesh source contracts, outbox broker runtime-execution proof artifacts, Gateway/Workbench source contracts/discovery, optional Gateway/Workbench runtime-execution proof, mesh policy, platform catalog source contract, receipt-bound mainline AI lineage-store CI execution, AI workflow-pack registration/runtime execution proof artifacts, and opportunity archetype scenario readiness can be consumed. Source contracts add provenance without clearing live blockers; runtime-class Risk/Performance/Core/Manage/Advise/outbox-broker and Gateway/Workbench proofs clear only their named blockers when valid and current. No full live journey, live AI provider execution, suitability/rebalance/risk-profile/restriction-clearance/benchmark-assignment authority, platform mesh certification, external broker or platform-mesh publication without an accepted broker runtime artifact, downstream delivery beyond the named bounded proof, full Gateway/Workbench product certification, client-ready publication, or supported-feature promotion is proven. |

`GET /api/v1/implementation-proof/readiness` is the internal operator
diagnostic for RFC-0002 implementation proof posture.

It aggregates current evidence and blockers across:

1. source-owned high-cash signal ingestion,
2. deterministic advisor review queue,
3. AI-assisted explanation governance,
4. data-mesh producer and consumer certification,
5. source-safe runtime trust telemetry preview, snapshot endpoint, and snapshot generation,
6. internal outbox delivery foundation and bounded run-once operator action,
7. Workbench product realization,
8. opportunity archetype scenario readiness,
9. downstream Advise, Manage, Report, Render, and Archive realization,
10. supported-feature promotion.

## What It Proves

The diagnostic proves that `lotus-idea` can produce a source-safe, aggregate
readiness view over the current RFC-0002 implementation foundations and known
proof blockers.

It returns:

1. the current aggregate proof posture,
2. source-ingestion readiness posture,
3. advisor queue readiness posture,
4. AI explanation readiness posture,
5. data-mesh readiness posture,
6. runtime trust telemetry preview, snapshot endpoint, generated snapshot, and
   candidate-snapshot test-execution posture,
7. outbox delivery readiness and run-once posture,
8. Workbench realization blockers,
9. opportunity archetype scenario blockers from the governed contract,
10. downstream realization blockers and internal submission route evidence,
11. supported-feature promotion blockers,
12. source-of-truth implementation paths.

## Supported-Feature Reconciliation

Supported-feature readiness is derived by
`app.application.supported_feature_promotion`, the same evaluator used by
`make supported-features-gate`. A status string alone cannot clear promotion
blockers. Missing, malformed, unresolved, future-dated, or stale registry
evidence remains source-safely blocked; valid current evidence is projected
consistently by the application snapshot, API response, and generated proof
artifact. `make supported-feature-promotion-contract-gate` prevents those
consumers from restoring independent counting or hard-coded output.

## Blocker Closure Manifest

`contracts/implementation-proof/rfc0002-blocker-closure-manifest.v1.json`
is the durable RFC-0002 blocker-to-issue map. It records each current
implementation-proof blocker, the owning Lotus GitHub issue, any sibling-repo
dependency issues, the required evidence class, the slice association, and the
supported-feature effect. Each sibling dependency issue must also declare a
source-safe `dependencyRole` explaining why that owner issue blocks the
manifest group. `make implementation-proof-closure-manifest-gate`
builds the strict default readiness snapshot with no optional proof artifacts
and fails closed when a blocker is missing, duplicated, stale, assigned to an
unknown evidence class, linked to an inconsistent issue URL, missing a
dependency role, or using drifted group, slice, blocker, closure-status, or
supported-feature-effect vocabulary.

The manifest is source-contract governance only. It does not close runtime,
deployment, production, Workbench, data-mesh, publication, or supported-feature
blockers by itself. It exists so unresolved RFC-0002 work is durable in GitHub
and executable source, not hidden in chat memory.

## GitHub Issue Execution Ledger

`contracts/implementation-proof/rfc0002-github-issue-execution-ledger.v1.json`
is the durable RFC-0002 issue-execution ledger for the current slice backlog.
It records the active RFC execution issues, their slice labels, open versus
closed posture, and whether a PR is allowed to use GitHub auto-close wording
for the issue.

`make rfc0002-github-issue-execution-ledger-gate` fails closed when an open or
partially progressed issue allows PR auto-close, lacks the explicit
`Keep #<issue> open` instruction, omits a current execution issue such as
`#690`, duplicates an issue, or describes a closed issue without closed
evidence. The ledger includes the current slice execution issues and legacy
RFC-labeled blockers, so every GitHub issue carrying `rfc/RFC-0002` must be
represented in durable execution truth. The gate is part of `make lint` so
partial source-contract or evidence-consumption PRs can link issues without
silently closing work that still needs live runtime, downstream, publication,
support, or supported-feature proof.

`make rfc0002-github-issue-execution-state-audit` compares the ledger with
current GitHub issue state through the GitHub CLI. It is intentionally a
GitHub-backed audit rather than a CI lint gate: run it before PR evidence, after
manual label or reopen/close changes, and whenever the RFC issue count is used
as delivery truth. The audit fails when a ledger-tracked issue is missing from
GitHub output, GitHub open/closed state contradicts the ledger, `open_blocked`
issues lack `status/blocked`, `open_in_progress` issues lack
`status/in-progress`, `open_fixed_local` issues lack `status/fixed-local`,
`open_pr_raised` issues lack `status/pr-open`, `open_tracker` parent issues
lack `status/tracker`, merged-main-QA-pending issues lack `status/merged-main`,
closed-complete issues do not retain
`status/merged-main`, or a GitHub issue has the `rfc/RFC-0002` label but is
missing from the ledger.

This ledger is issue-lifecycle governance only. It does not promote a feature,
clear blockers, or replace the blocker closure manifest. It prevents GitHub
state drift when a PR lands partial RFC progress, such as consuming owner proof
while keeping Report, Render, Archive, client-publication, and promotion proof
open.

`make rfc0002-github-issue-execution-summary` renders a compact Markdown
summary from the source-controlled execution ledger and issue-learning ledger.
Use it after the live state audit when reporting fixed/open counts, active
implementation issues, blocked issues, trackers, or the learning pattern that
should guide the next implementation slice. The summary is source posture, not
live GitHub proof; it deliberately points back to
`make rfc0002-github-issue-execution-state-audit` for current GitHub label and
open/closed verification.

## GitHub Issue Learning Patterns

`contracts/implementation-proof/rfc0002-issue-learning-patterns.v1.json` is
the durable RFC-0002 issue-learning ledger. It groups every non-complete
RFC-0002 execution issue into a repeated pattern family such as Workbench /
Gateway proof boundaries, downstream owner runtime proof, data-product
promotion, operations certification, AI attestation, demo-commercial claims,
and GitHub execution hygiene.

`make rfc0002-github-issue-learning-pattern-gate` fails closed when a
non-complete execution issue is absent from the pattern ledger, a current issue
reference is not in the execution ledger, a required durable control path is
missing, or a pattern lacks actionable future-agent guidance and explicit
non-claim boundaries. The gate is part of `make lint`, so new RFC-0002 issues
cannot be added to the execution ledger without also deciding which repeated
defect lens future implementation work must apply.

The pattern ledger is learning and routing governance only. It does not close
issues, clear implementation blockers, or certify any capability. It exists so
issue-derived lessons are durable in source control and GitHub-backed PR
evidence, not only in chat memory or long-form prose.

## Blueprint Scope Coverage

`contracts/implementation-proof/rfc0002-blueprint-scope-coverage.v1.json`
is the durable RFC-0002 blueprint-to-issue map. It records every owned
capability, non-owned authority boundary, and target opportunity family from
`docs/LOTUS_IDEA_BLUEPRINT.md` with RFC slice IDs, owning GitHub issues,
sibling-repository dependency issues where applicable, evidence references, and
the current `foundation_only_not_promoted` supported-feature posture.

`make blueprint-scope-coverage-gate` parses the repo-authored blueprint and
fails closed when a capability, boundary, or opportunity family is missing from
the contract, appears in the contract after being removed from the blueprint,
uses a malformed GitHub issue reference, omits evidence, or promotes a
supported-feature claim before certification evidence exists. The gate also
records that the external download copy of the blueprint was reviewed, but the
repo-authored file remains the source of durable truth.

The coverage contract is planning and traceability governance only. It does not
close runtime, deployment, Workbench, downstream, platform mesh, client-ready
publication, or supported-feature blockers.

The 2026-07-19 GitHub audit verified that the current RFC-0002 blueprint and
proof contracts have owner-repo issue coverage in `lotus-advise`, `lotus-ai`,
`lotus-archive`, `lotus-core`, `lotus-gateway`, `lotus-manage`,
`lotus-performance`, `lotus-platform`, `lotus-render`, `lotus-report`,
`lotus-risk`, and `lotus-workbench`. No additional product dependency issue was
required by the audited contract state. `sgajbi/lotus-platform#602` tracks the
reusable cross-repo RFC issue-coverage auditor so future broad RFC closure work
can validate issue existence, RFC/slice labels, state, priority, and blocked
posture without relying on manual chat memory.

## What It Does Not Prove

The diagnostic is deliberately not full live journey proof. It does not:

1. call `lotus-core`,
2. certify source-ingestion as a supported live source product beyond a
   configured bounded proof artifact,
3. live-call `lotus-ai`, execute live provider/RAG workflows, or certify provider rollout,
4. certify data products through platform mesh certification,
5. prove Gateway or Workbench product behavior,
6. create downstream proposals, manage actions, reports, rendered output, or
   archive records,
7. authorize external publication of client-facing material,
8. promote any supported feature.

## Current Blockers

Current posture is `blocked` and `not_certified`.

That is expected. The endpoint exists so operators and implementation agents can
see the real proof gap before demo, data-mesh, Workbench, downstream, or
supported-feature promotion.

The response remains blocked until all of the following are implemented and
validated through the owning repositories and platform gates:

1. source-ingestion certification beyond the bounded live Core proof artifact,
2. observed scheduled-worker deployment evidence and later scheduled-execution
   certification beyond the current source contract,
3. platform mesh certification, active producer products, and Gateway/Workbench discovery,
4. certified downstream delivery evidence beyond the bounded consumer-runtime proof artifact,
5. certified external broker publication and production event-publication evidence beyond the bounded platform-mesh event source-contract artifact,
6. `lotus-ai` live-provider rollout and runtime trust certification,
7. Workbench panel and browser proof,
8. downstream Advise and Manage realization authority,
9. Report/Render/Archive client-publication authority,
10. supported-feature promotion evidence.

Downstream realization blockers are backed by
`contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`.
`make downstream-realization-contract-gate` validates that the planned
contract rows stay source-authority preserving and do not become false
route-existence, downstream-execution, or supported-feature claims.
The downstream realization capability now also cites the internal submission
routes for Advise/Manage conversion intents and Report evidence-pack requests,
plus the report-owned planned intake contract at
`lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`.
Default digest-bound Advise and Manage route source contracts add declaration
provenance when merged sibling evidence is present while preserving every live
route blocker. Report intake and materialization source contracts follow the
same non-clearing rule. Those refs do not clear runtime execution,
render/archive, suitability policy, rebalance/action, client-publication,
certification, or supported-feature blockers.

Source-ingestion runtime evidence is captured by
`scripts/source_ingestion/generate_runtime_execution.py`. The closed-field v2
artifact is `runtime_execution` evidence because its source-safe receipts bind
the actual Core references, domain decisions, and persisted records returned by
the application use case. Hand-authored success flags, summary counts,
in-memory storage, mixed outcomes, missing records, altered source hashes, and
unknown claim fields fail closed. The source-ingestion readiness endpoint may
report the family-level live Core posture as valid from the configured
artifact, but aggregate implementation-proof readiness clears
`live_core_source_proof_missing` only when that valid artifact is also
aggregate-current: it must carry `aggregateProofProvenance`, match the
source-safe consumed proof ref, be no more than 24 hours old, not be
future-dated, be bound to the current Lotus Idea source revision, and declare
`sourceTreeDirty=false`. A current artifact referenced through
`LOTUS_IDEA_SOURCE_INGESTION_RUNTIME_EXECUTION` clears only
`live_core_source_proof_missing`; it does not clear scheduled worker,
data-mesh, Gateway/Workbench, production-certification, downstream, or
supported-feature blockers. Blocked artifacts retain source-safe aggregate
reason counts but carry no persistence receipt and clear no blocker.
When aggregate implementation-proof readiness consumes a family-valid and
aggregate-current live proof path, the `source-ingestion` capability also
records a source-safe artifact reference in `evidenceRefs`, so release
reviewers can trace why that blocker cleared without exposing Core payloads or
portfolio identity. Missing, stale, future-dated, wrong-ref, or
wrong-source-revision provenance, or provenance generated from a dirty source
tree, leaves the source-ingestion and high-cash opportunity-archetype live Core
blockers in place and does not add the artifact ref as evidence.
Canonical Core runtimes should pass explicit `--core-query-base-url` and
`--core-query-control-plane-base-url` values because query-service reads and
query-control-plane snapshots can be served by different Core processes.
`--core-base-url` remains a compatibility fallback for older single-base
stacks.
The repo-native `make implementation-proof-readiness-check` target accepts the
same live-evidence inputs through Make variables, so release reviewers can use
the canonical target instead of a one-off command:

## Aggregate Proof Provenance

Aggregate readiness consumes optional JSON proof artifacts only after both the
family proof contract and the aggregate provenance check pass. The CLI and
runtime artifact loader attach `aggregateProofProvenance` with the source-safe
proof ref, artifact SHA-256, current source revision, source-tree dirty flag,
and proof generation timestamp before any optional proof can clear a blocker.

Blockers remain in place when the provenance envelope is missing, the proof ref
does not match the consumed artifact, `generatedAtUtc` is future-dated or older
than the 24-hour freshness window, the source revision does not match the
current Lotus Idea source revision, or `sourceTreeDirty` is missing or not
`false`. Dirty-tree proof artifacts may be useful as diagnostic evidence, but
they cannot clear release/readiness blockers or add their artifact ref to
capability evidence. Runtimes without a local `.git` checkout must set
`LOTUS_IDEA_SOURCE_REVISION` to the deployed commit or deterministic source
identifier when they expect optional proof artifacts to clear aggregate
readiness blockers. This provenance binding is internal implementation
evidence; it is not data-mesh certification, client-publication approval, or
supported-feature promotion.

## Proof Worktree Import Integrity

Repo-native proof generators and proof gates that import `app` must call
`scripts.proof_worktree_import_guard.ensure_worktree_imports(__file__)` before
the first application import. The guard pins imports to the entrypoint's owning
worktree `src/` directory and repository root, then fails closed with
`proof_import_worktree_mismatch` if an already-loaded or discoverable `app`
module resolves outside that worktree.

This prevents a clean, revision-bound proof artifact from executing application
code from a sibling checkout through a reused editable virtual environment or
ambient `PYTHONPATH`. Operators and agents should use repo-native proof
commands instead of ad hoc cross-worktree invocations. The invariant is covered
by `tests/unit/test_proof_worktree_import_guard.py`, including a sibling
worktree regression and a static scan that requires the guard before every
application import in proof and contract scripts.

## Evidence-Class Boundary

Proof authority is classified as source contract, local test execution, CI
execution, runtime execution, deployment, or production certification. These
classes are exact, not cumulative. A proof can clear only a blocker that
requires the same class.

`app.application.implementation_proof_artifact_registry` records every optional
artifact accepted by the aggregate proof CLI, including its readiness payload
and reference arguments, evidence class, blocker effect, issue owner, and
classification status. `make documentation-contract-gate` compares that
registry with the CLI parser, application snapshot signature, and evidence
classification inventory. Adding a proof input without all four surfaces now
fails deterministically.

Registry effect is executable application policy, not descriptive metadata.
Before validation or mutation, every aggregate consumer must reconcile its
payload or reference argument to exactly one classified registry entry and
assert either `blocker_clearing` or `supporting_evidence`. Unknown, duplicate,
pending, and wrong-effect entries fail closed. This applies to standard
aggregate artifacts, opportunity-archetype artifacts, source-ingestion runtime
evidence, scheduled-worker source/deployment evidence, and downstream
source-contract readiness. Aggregate downstream source contracts are also
subject to the normal 24-hour provenance window; stale or future-dated
contracts do not add aggregate evidence references.

The AI lineage-store v2 proof requires mainline `ci_execution`. It binds the
Main Releasability PostgreSQL workflow/job, run and attempt, exact commit and
main ref, successful conclusion, completion timestamp, GitHub artifact digest,
and the named lineage persistence assertions. Repository files and Make target
presence remain design evidence and cannot clear
`certified_ai_lineage_store_missing` alone. See
`docs/architecture/implementation-proof-evidence-classification.md` for the
taxonomy and the #393 same-pattern campaign.

| Variable | Effect |
| --- | --- |
| `IMPLEMENTATION_PROOF_EVALUATED_AT_UTC` | Overrides the deterministic proof timestamp. |
| `IMPLEMENTATION_PROOF_OUTPUT` | Writes the aggregate readiness JSON to a chosen ignored output path. |
| `LOTUS_CORE_QUERY_BASE_URL` | Passes the live Core query-service URL into readiness generation. |
| `LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL` | Passes the live Core query-control-plane URL into readiness generation. |
| `LOTUS_IDEA_SOURCE_INGESTION_RUNTIME_EXECUTION` | Passes receipt-bound v2 `runtime_execution` evidence into aggregate readiness. The artifact must be valid and aggregate-current before it can affect the source-ingestion or high-cash opportunity-archetype live Core posture. |
| `LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF` | Passes a validated source-safe Lotus Risk concentration live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_live_risk_source_proof_missing`; it does not certify data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF` | Passes validated v2 high-volatility `runtime_execution` evidence into opportunity-archetype readiness. It must bind current Lotus Risk evidence to the authoritative Idea use-case result and accepted or replayed durable persistence. A valid artifact clears only `opportunity_archetype_live_risk_volatility_source_proof_missing`; it does not certify drawdown, data mesh, Workbench, client publication, deployment, production, or supported-feature promotion. |
| `LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF` | Passes validated v2 drawdown `runtime_execution` evidence into opportunity-archetype readiness. It must bind current Lotus Risk evidence to the authoritative Idea use-case result and accepted or replayed durable persistence. A valid artifact clears only `opportunity_archetype_drawdown_source_proof_missing`; it does not certify volatility, data mesh, Workbench, client publication, deployment, production, or supported-feature promotion. The environment name is retained for operator compatibility; it does not imply acceptance of the retired v1 contract. |
| `LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF` | Passes validated v2 Performance underperformance `runtime_execution` evidence into opportunity-archetype readiness. It must bind exact current `ReturnsSeriesBundle:v1` evidence and benchmark context to the authoritative Idea use-case result and accepted or replayed durable persistence. A valid artifact clears only `opportunity_archetype_live_performance_source_proof_missing`; benchmark assignment, data mesh, Workbench, client publication, deployment, production, and supported-feature promotion remain blocked. The environment name is retained for operator compatibility and does not accept the retired v1 contract. |
| `LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF` | Passes validated v2 Performance benchmark-readiness `runtime_execution` evidence into missing-benchmark opportunity-archetype readiness. It must bind one source-preserving application invocation and one exact `ReturnsSeriesBundle:v1` fetch to pseudonymous request scope, source product/route/time, calculation and input hashes, response portfolio, benchmark context, coverage, freshness, quality, producer correlation/trace, and deterministic review-required or no-opportunity receipts. A valid current artifact clears only `opportunity_archetype_performance_benchmark_readiness_source_ref_missing`; Core assignment, methodology, data mesh, Workbench, publication, deployment, production, and support promotion remain blocked. The stable environment name does not accept v1. |
| `LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF` | Passes validated v2 Core benchmark-assignment `runtime_execution` evidence into opportunity-archetype readiness. The compatibility environment name does not accept v1. A valid artifact binds pseudonymous scope and an exact current `BenchmarkAssignment:v1` source receipt, clears only `opportunity_archetype_benchmark_assignment_source_ref_missing`, and preserves Performance, methodology, mesh, Workbench, publication, deployment, production, and promotion blockers. |
| `LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF` | Passes validated v2 Core portfolio-state `runtime_execution` evidence into opportunity-archetype readiness. The compatibility environment name does not accept v1. A valid artifact binds pseudonymous request scope to the complete current `PortfolioStateSnapshot:v1` source receipt and clears only `opportunity_archetype_core_portfolio_state_source_ref_missing`. It preserves Manage, Performance, Risk, mesh, Workbench, publication, deployment, production, and promotion blockers. |
| `LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF` | Passes a validated source-safe Lotus Core maturity-summary live-proof artifact into opportunity-archetype readiness. The live adapter consumes Core-owned `PortfolioMaturitySummary:v1` and fails closed when explicit maturity facts or upstream holdings lineage are missing. A valid artifact clears only `opportunity_archetype_maturity_live_core_source_proof_missing`; it does not recommend reinvestment products, forecast cashflows, certify suitability or risk, certify data mesh, prove Workbench behavior, approve client publication, or promote support. |
| `LOTUS_IDEA_MISSING_BENCHMARK_LIVE_PROOF` | Passes validated closed v2 Core missing-benchmark `runtime_execution` evidence into opportunity-archetype readiness. The compatibility environment name does not accept v1. One Core fetch must reconcile pseudonymous tenant/book/portfolio/client/evaluation/correlation/trace scope, current `BenchmarkAssignment:v1` evidence, assignment identity/effectiveness/status/version posture, and a deterministic candidate or truthful ready-assignment no-opportunity receipt. A valid artifact clears only `opportunity_archetype_missing_benchmark_live_core_source_proof_missing`; Performance readiness, methodology, data mesh, Gateway/Workbench, publication, deployment, production, and promotion remain blocked. |
| `LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF` | Passes validated receipt-bound Core cashflow v2 runtime evidence into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_live_core_cashflow_source_proof_missing`; it does not certify client income needs, funding advice, treasury instruction, suitability, planning objectives, data mesh, Workbench, client publication, deployment, production, or supported-feature promotion. |
| `LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF` | Passes validated closed v2 Lotus Manage mandate runtime evidence into opportunity-archetype readiness. Exact source scope, time, identity, policy, and deterministic outcome must reconcile. A valid artifact clears only `opportunity_archetype_portfolio_scoped_manage_source_proof_missing`, `opportunity_archetype_mandate_performance_health_source_ref_missing`, and `opportunity_archetype_mandate_risk_health_source_ref_missing`; it does not certify Core portfolio state, data mesh, Workbench, client publication, supported-feature promotion, rebalance authority, action authority, order creation, execution, or settlement. |
| `LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF` | Passes validated closed v2 Advise mandate/restriction `runtime_execution` evidence into opportunity-archetype readiness. The compatibility environment name does not accept v1. Exact pseudonymous request scope, producer scope/time, workflow posture, source/policy hashes, deterministic candidate or no-opportunity outcome, and receipt digests must reconcile. A valid artifact clears only `opportunity_archetype_live_restriction_source_proof_missing`; typed source-product, restriction clearance, mandate state, suitability, policy/proposal approval, data mesh, Workbench, client publication, rebalance/order authority, deployment, production, and support promotion remain blocked. |
| `LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF` | Passes a validated source-safe typed Lotus Advise mandate/restriction source-product proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_typed_restriction_source_product_missing`; it does not certify live Advise reachability, clear restrictions, change mandate state, approve suitability, approve policy, approve proposals, certify data mesh, prove Workbench behavior, approve client publication, create rebalance/order authority, or promote support. |
| `LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF` | Passes a validated source-safe Lotus Advise policy-evaluation live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_advise_policy_live_source_proof_missing`; it does not certify suitability, policy approval, proposal approval, data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF` | Passes a validated source-safe typed Lotus Advise risk-profile source-product proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_typed_advise_risk_profile_source_product_missing`; it does not certify live Advise reachability, approve risk profiling, approve suitability or policy, certify data mesh, prove Workbench behavior, approve client publication, or promote support. |
| `LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF` | Passes a validated source-safe Lotus Advise risk-profile diagnostic live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_advise_risk_profile_live_source_proof_missing`; it does not certify a typed risk-profile source product, risk-profile approval, suitability, policy approval, proposal approval, data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_ADVISE_ROOT` | Selects the sibling `lotus-advise` checkout used to generate the default digest-bound Advise route source contract. Defaults to `../lotus-advise`. |
| `LOTUS_IDEA_ADVISE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default Advise route source-contract artifact consumed as supporting evidence. Defaults to `output/downstream/advise-route-source-contract-proof.json`. |
| `LOTUS_IDEA_ADVISE_ROUTE_SOURCE_CONTRACT_PROOF` | Overrides the default Advise route source-contract artifact path. |
| `LOTUS_ADVISE_PYTHON` | Selects the Python interpreter used to execute the sibling `lotus-advise` local ASGI runtime proof. Defaults to `../lotus-advise/.venv-codex/Scripts/python.exe`. |
| `LOTUS_IDEA_ADVISE_INTAKE_RUNTIME_EXECUTION_PROOF` | Overrides the default Advise idea-intake runtime-execution proof path. A valid aggregate-current artifact clears only `advise_live_contract_proof_missing` and preserves suitability, proposal lifecycle, client-publication, production, support, and supported-feature blockers. |
| `LOTUS_MANAGE_ROOT` | Selects the sibling `lotus-manage` checkout used to generate the default digest-bound Manage route source contract. Defaults to `../lotus-manage`. |
| `LOTUS_IDEA_MANAGE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default Manage route source-contract artifact consumed as supporting evidence. Defaults to `output/downstream/manage-route-source-contract-proof.json`. |
| `LOTUS_IDEA_MANAGE_ROUTE_SOURCE_CONTRACT_PROOF` | Overrides the default Manage route source-contract artifact path. |
| `LOTUS_MANAGE_PYTHON` | Selects the Python interpreter used to execute the sibling `lotus-manage` local ASGI runtime proof. Defaults to `python`; override only when a repo-local Manage venv is required. |
| `LOTUS_IDEA_MANAGE_INTAKE_RUNTIME_EXECUTION_PROOF_OUTPUT` | Selects the default Manage action-intake runtime-execution artifact consumed by aggregate readiness. Defaults to `output/downstream/manage-intake-runtime-execution-proof.json`. |
| `LOTUS_IDEA_MANAGE_INTAKE_RUNTIME_EXECUTION_PROOF` | Overrides the default Manage action-intake runtime-execution proof path. A valid aggregate-current artifact clears only `manage_live_contract_proof_missing` and preserves rebalance authority, action-register persistence, OMS/order execution, client-publication, production, support, and supported-feature blockers. |
| `LOTUS_REPORT_ROOT` | Selects the sibling `lotus-report` checkout used to generate the default source-safe report-intake route proof. Defaults to `../lotus-report`. |
| `LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default generated report-intake route proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/report/intake-route-source-contract-proof.json`. |
| `LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF` | Overrides the default generated report-intake route proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default generated report materialization source-contract artifact consumed by aggregate readiness when no override is set. Defaults to `output/report/materialization-source-contract-proof.json`. |
| `LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF` | Overrides the default report materialization source-contract artifact passed into aggregate readiness. |
| `LOTUS_REPORT_PYTHON` | Selects the Python interpreter used to execute the sibling `lotus-report` local ASGI materialization runtime proof. Defaults to `python`; override only when a repo-local Report venv is required. |
| `LOTUS_IDEA_REPORT_MATERIALIZATION_RUNTIME_EXECUTION_PROOF_OUTPUT` | Selects the default generated Report materialization runtime-execution artifact consumed by aggregate readiness. Defaults to `output/report/materialization-runtime-execution-proof.json`. |
| `LOTUS_IDEA_REPORT_MATERIALIZATION_RUNTIME_EXECUTION_PROOF` | Overrides the default Report materialization runtime-execution proof path. A valid aggregate-current artifact must bind receipt-level Report materialization execution to exact Render #65/PR #67 and Archive #72/PR #73 owner-mainline evidence. It clears `report_evidence_pack_live_materialization_proof_missing`, `rendered_output_creation_missing`, and `archive_record_creation_missing`; client-publication, supported-feature promotion, production identity, legal/retention, support, and final certification blockers remain. |
| `LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default generated mesh policy source-contract artifact consumed by aggregate readiness when no override is set. Defaults to `output/data-mesh/mesh-policy-source-contract.json`. |
| `LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF` | Overrides the default generated mesh policy source-contract artifact passed into aggregate readiness. |
| `LOTUS_PLATFORM_ROOT` | Selects the sibling `lotus-platform` checkout used to generate the default source-safe platform catalog source contract. Defaults to `../lotus-platform`. |
| `LOTUS_IDEA_PLATFORM_CATALOG_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default generated platform catalog source contract artifact consumed by aggregate readiness when no override is set. Defaults to `output/data-mesh/platform-catalog-source-contract.json`. |
| `LOTUS_IDEA_PLATFORM_CATALOG_SOURCE_CONTRACT_PROOF` | Overrides the default generated platform catalog source contract artifact passed into aggregate readiness. |
| `LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF_OUTPUT` | Selects the default generated outbox consumer source-contract proof consumed by aggregate readiness when no override is set. Defaults to `output/outbox/outbox-consumer-contract-proof.json`. |
| `LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF` | Overrides the default generated outbox consumer source-contract proof passed into aggregate readiness. |
| `LOTUS_IDEA_OUTBOX_BROKER_RUNTIME_EXECUTION_PROOF_OUTPUT` | Selects the conventional outbox broker runtime-execution proof output path when a configured broker proof is generated. Defaults to `output/outbox/broker/runtime-execution-proof.json`. |
| `LOTUS_IDEA_OUTBOX_BROKER_RUNTIME_EXECUTION_PROOF` | Overrides the outbox broker runtime-execution proof path consumed by aggregate readiness. A valid current artifact clears only `external_broker_runtime_proof_missing`; downstream, platform-mesh, Gateway/Workbench, production-certification, and supported-feature blockers remain. |
| `LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_OUTPUT` | Selects the default generated outbox platform-mesh event source-contract proof consumed by aggregate readiness when no override is set. Defaults to `output/outbox/platform-mesh/event-source-contract-proof.json`. |
| `LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF` | Overrides the default generated outbox platform-mesh event source-contract proof passed into aggregate readiness. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT` | Selects the default generated Gateway/Workbench contract proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/workbench/gateway-workbench-contract-proof.json`. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF` | Overrides the default generated Gateway/Workbench contract proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_OUTPUT` | Selects the default generated Gateway/Workbench discovery contract proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/workbench/gateway-workbench-discovery-contract-proof.json`. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF` | Overrides the default generated Gateway/Workbench discovery contract proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_RUNTIME_EXECUTION_PROOF_OUTPUT` | Selects the recommended local output path for generated Gateway/Workbench runtime-execution proof. Defaults to `output/workbench/gateway-workbench-runtime-execution-proof.json`; aggregate readiness consumes it only when `LOTUS_IDEA_GATEWAY_WORKBENCH_RUNTIME_EXECUTION_PROOF` is set. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_RUNTIME_EXECUTION_PROOF` | Overrides the optional Gateway/Workbench runtime-execution proof artifact passed into aggregate readiness. A valid current artifact clears only `workbench_gateway_bff_consumption_proof_missing`; production identity, browser accessibility, canonical demo runtime, data-product, client-publication, suitability/execution, and supported-feature blockers remain. |
| `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT` | Selects the default generated AI lineage store proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/ai/ai-lineage-store-proof.json`. |
| `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF` | Overrides the default generated AI lineage store proof artifact passed into aggregate readiness. |
| `LOTUS_AI_ROOT` | Selects the sibling `lotus-ai` checkout used to generate the workflow-pack registration source-contract proof. Defaults to `../lotus-ai`. |
| `LOTUS_AI_BASE_URL` | Selects the governed Lotus AI runtime used for actual workflow-pack execution proof. Defaults to `http://127.0.0.1:8140`. |
| `LOTUS_IDEA_AI_RUNTIME_PROOF_TIMEOUT_SECONDS` | Bounds the runtime-proof HTTP call. Defaults to `2`; accepted values are greater than zero and at most `30`. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT` | Selects the default generated AI workflow-pack registration source-contract artifact consumed by aggregate readiness when no override is set. Defaults to `output/ai/ai-workflow-pack-registration-source-contract-proof.json`. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF` | Overrides the default generated AI workflow-pack registration source-contract artifact passed into aggregate readiness. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT` | Selects the default generated AI workflow-pack runtime execution proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/ai/ai-workflow-pack-runtime-execution-proof.json`. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF` | Overrides the default generated AI workflow-pack runtime execution proof artifact passed into aggregate readiness. |

When rerunning live proof against an existing durable PostgreSQL repository,
preserve idempotency history. If the same generated default idempotency key was
accepted before an upstream Core source fingerprint changed, a later run can
correctly return `conflict`. Capture a fresh release-proof run with an ignored
manifest under `output/source-ingestion/` and a source-safe explicit
`idempotencyKey`; do not reset durable state to force an accepted outcome. The
checked-in example manifest remains the canonical source-safe default, while
ignored proof-run manifests are local evidence inputs only.

Valid source-ingestion live Core proof also clears only
`opportunity_archetype_live_core_source_proof_missing` for the governed
high-cash / idle-liquidity scenario inside `opportunity-archetype-scenarios`.
It remains source-safe proof over the internal high-cash ingestion run and does
not certify Workbench behavior, data mesh, client publication, or
supported-feature promotion.

Scheduled source-ingestion worker evidence is intentionally split by class:

1. `scripts/source_ingestion_scheduler/generate_source_contract.py` produces
   closed `source_contract` evidence over digest-bound scheduler source,
   Compose, manifest, and configuration identity. It contributes an evidence
   reference but clears no blocker.
2. `scripts/source_ingestion_scheduler/generate_deployment_evidence.py`
   produces `deployment` evidence only from observed immutable image, Git,
   environment, controller-run, workload-rollout, and scheduler-configuration
   facts.
3. Readiness clears only `scheduled_worker_deploy_proof_missing` when the
   deployment receipt validates and binds the exact configured source contract.
   Unknown fields, evidence-class substitution, digest drift, incomplete
   rollout, and execution or production claim inflation fail closed.

`make implementation-proof-readiness-check` generates only the source contract,
so its default snapshot truthfully retains the deployment blocker. A deployment
receipt may be supplied through
`LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE`; neither
artifact proves that a scheduled iteration executed, live Core certification,
data-mesh certification, Gateway/Workbench behavior, downstream realization,
production certification, or supported-feature promotion.

Lotus Risk concentration runtime execution evidence is captured by
`scripts/risk_concentration_runtime_evidence/generate_runtime_execution.py`. A valid artifact referenced
through `LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF` clears only
`opportunity_archetype_live_risk_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The closed v2
`runtime_execution` contract binds one current
`lotus-risk:ConcentrationRiskReport:v1` source receipt to the authoritative
deterministic use-case result and one durable accepted or replayed Idea
persistence receipt. Request, source, evidence, scope, and persistence digests
must reconcile. Unknown claims, stale or mixed source identity, in-memory
storage, missing persistence, and receipt tampering fail closed. The artifact
stores no portfolio identity, request or response payload, correlation ID,
trace ID, candidate ID, source route, or concentration figure. It retains
data-mesh, Workbench, client-publication, deployment, production, and
supported-feature blockers; official concentration methodology remains owned
by `lotus-risk`.

Lotus Risk high-volatility runtime execution evidence is captured by
`scripts/high_volatility_runtime_evidence/generate_runtime_execution.py`. A
valid artifact referenced through `LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF` clears
only `opportunity_archetype_live_risk_volatility_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The closed v2 contract binds one
current `lotus-risk:RiskMetricsReport:v1` source receipt to the authoritative
deterministic use-case result and one durable accepted or replayed Idea
persistence receipt. Request, source, evidence, scope, timestamp, provenance,
and persistence digests must reconcile. Unknown claims, stale or mixed source
identity, non-candidate outcomes, in-memory storage, missing persistence, and
receipt tampering fail closed. The artifact stores no portfolio identity,
request or response payload, correlation ID, trace ID, candidate ID, source
route, volatility value, or drawdown figure. It retains drawdown, data-mesh,
Workbench, client-publication, deployment, production, and supported-feature
blockers; official risk methodology remains owned by `lotus-risk`.

Lotus Risk drawdown runtime execution evidence is captured by
`scripts/risk_drawdown_runtime_evidence/generate_runtime_execution.py`. A valid
artifact referenced
through `LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF` clears only
`opportunity_archetype_drawdown_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The closed v2 contract binds one
current `lotus-risk:DrawdownAnalyticsReport:v1` source receipt to the
authoritative deterministic use-case result and one accepted or replayed
durable Idea persistence receipt. Request, source, evidence, scope, timestamp,
provenance, and persistence digests must reconcile. Unknown claims, stale or
mixed source identity, non-candidate outcomes, conflicts, in-memory storage,
missing persistence, and receipt tampering fail closed. The artifact stores no
portfolio identity, request or response payload, correlation ID, trace ID,
candidate ID, source route, max-drawdown value, or drawdown episode. It retains
volatility, data-mesh, Workbench, client-publication, deployment, production,
and supported-feature blockers; official drawdown methodology remains owned by
`lotus-risk`.

Lotus Performance underperformance runtime execution is captured by
`scripts/performance_underperformance_runtime_evidence/generate_runtime_execution.py`.
A valid artifact
referenced through `LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF` clears
only `opportunity_archetype_live_performance_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The closed v2 artifact binds a
live `lotus-performance:ReturnsSeriesBundle:v1` source receipt and benchmark
context to deterministic candidate evaluation and one accepted or replayed
durable Idea persistence receipt. Request, source, evidence, scope, timestamp,
and persistence digests must reconcile. It stores no portfolio identity,
request or response payload, correlation or trace ID, candidate ID, source
route, return, or benchmark value. Benchmark-assignment, data-mesh, Workbench,
client-publication, deployment, production, and supported-feature blockers
remain.

Lotus Core benchmark-assignment runtime evidence is captured by
`scripts/core_benchmark_assignment_runtime_evidence/generate_runtime_execution.py`.
A valid artifact
referenced through `LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF` clears only
`opportunity_archetype_benchmark_assignment_source_ref_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-core:BenchmarkAssignment:v1` source call through a named application use
case. Canonical digests bind pseudonymous tenant/portfolio scope, exact as-of
date, reporting currency, evaluation time, and the complete current source
receipt. The closed validator rejects unknown claims, source substitution,
scope or digest mismatch, stale/future evidence, inactive or ineffective
assignments, and missing benchmark identity/version. This read-only operation
does not create an Idea aggregate, so it deliberately has no persistence
receipt. It retains live Performance, data-mesh, Workbench, client-publication,
deployment, production, and supported-feature blockers. Core owns assignment;
Idea does not assign benchmarks, calculate returns, or certify methodology.

Lotus Core portfolio-state runtime evidence is captured by
`scripts/core_portfolio_state_runtime_evidence/generate_runtime_execution.py`.
A valid artifact
referenced through `LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF` clears only
`opportunity_archetype_core_portfolio_state_source_ref_missing` for the
`opportunity-archetype-scenarios` capability. The closed v2 artifact binds a
named read-only use case, pseudonymous request scope, and the complete current
`lotus-core:PortfolioStateSnapshot:v1` receipt. That receipt includes response
scope, product identity, request fingerprint, snapshot identity, source hashes,
restatement, reconciliation, evidence time, policy, correlation, and section
posture without storing raw identifiers, payloads, holdings, positions,
allocation weights, or portfolio totals. Missing or inconsistent producer
trust metadata fails closed. Request `evaluatedAtUtc` remains the request
boundary; top-level `generatedAtUtc` records post-fetch observation, so a Core
receipt generated during the synchronous request can qualify but a receipt
later than artifact finalization cannot. Lotus-core issue `#790` owns producer
acceptance and downstream proof. The artifact deliberately retains portfolio-scoped Manage,
mandate performance-health, mandate risk-health, data-mesh, Workbench,
client-publication, supported-feature, rebalance, action, order-creation,
execution, and settlement blockers unless a separate valid Manage mandate
live-proof artifact supplies the Manage action-register and mandate-health
source refs.

Lotus Core low-income cashflow runtime evidence is captured by
`scripts/low_income_cashflow_runtime_evidence/generate_runtime_execution.py`. A valid artifact
referenced through `LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF` clears only
`opportunity_archetype_live_core_cashflow_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The named application use case
invokes the Core source port and binds a pseudonymous request receipt, exact
`lotus-core:PortfolioCashflowProjection:v1` and
`lotus-core:PortfolioCashMovementSummary:v1` receipts, projection arithmetic,
movement counts, policy threshold, and deterministic candidate or no-opportunity
outcome. Unknown, stale, degraded, scope-inconsistent, arithmetically invalid,
or tampered evidence fails closed. Zero projected cumulative cashflow is valid
numeric evidence and completes without creating an opportunity. The artifact
stores hashes and bounded aggregates rather than raw tenant, portfolio,
correlation, trace, request, response, movement, or client facts. It deliberately retains Workbench,
data-mesh, client-publication, supported-feature, suitability, planning,
funding-advice, and treasury-instruction blockers. Core issue `#796` tracks
producer tenant, reconciliation, snapshot/policy, correlation, and empty-window
evidence semantics required before live qualification can pass.

Lotus Core bond-maturity runtime evidence is captured by
`scripts/bond_maturity_runtime_evidence/generate_runtime_execution.py`. A valid
artifact referenced through `LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF` can satisfy
only `opportunity_archetype_maturity_live_core_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The named read-only application
use case consumes Core-owned `PortfolioMaturitySummary:v1` through the source
port and binds the exact request scope, maturity-summary receipt, and upstream
`HoldingsAsOf:v1` content identity. Qualification requires current complete
evidence, exact horizon and non-projected mode, contractual maturity-date basis,
supported response posture, no missing dates or unsupported product features,
complete reconciliation, snapshot/policy/correlation identity, consistent
hashes, and valid evidence time. A supported zero-count window is a completed
execution with `opportunityDetected=false`; a positive count requires an
in-window next maturity date. The source-safe artifact hashes tenant, portfolio,
and correlation identity and excludes request/response bodies, raw holdings,
security identifiers, quantities, and instrument-level schedules. It retains
the bounded next date and aggregate counts needed to verify the decision.
Request `evaluatedAtUtc` remains the request boundary and top-level
`generatedAtUtc` is the post-fetch observation boundary; a receipt later than
artifact finalization fails closed. Lotus Core issue `#792` owns producer
acceptance and downstream proof.
Data-mesh, Workbench, client-publication, product recommendation, reinvestment
advice, suitability, risk, deployment, production, and supported-feature
blockers remain.

Lotus Manage mandate runtime evidence is captured by
`scripts/manage_mandate_runtime_evidence/generate_runtime_execution.py`. The
closed v2 artifact invokes the named Manage source-evaluation use case and binds
pseudonymous tenant/portfolio scope, source-authored as-of and generation time,
the exact action-register receipt, Performance and Risk mandate-health source
receipts, policy, and deterministic candidate or no-opportunity outcome. A valid
artifact referenced
through `LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF` clears only
`opportunity_archetype_portfolio_scoped_manage_source_proof_missing`,
`opportunity_archetype_mandate_performance_health_source_ref_missing`, and
`opportunity_archetype_mandate_risk_health_source_ref_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-manage:PortfolioActionRegister:v1` source call, current source
evidence, workflow decision count, lineage edge count, portfolio-scope
confirmation, ready Manage action-register posture, Manage-provided
lineage/fingerprint metadata for `SourceRef.content_hash`, and current source
refs for `lotus-performance:MandatePerformanceHealthContext:v1` and
`lotus-risk:MandateRiskHealthContext:v1` without storing
portfolio identity, request or response payloads, correlation IDs, trace IDs,
candidate IDs, source routes, action identifiers, rebalance payloads, or order
details. Unknown fields, source substitution, scope, time, correlation, count,
policy, hash, freshness, or receipt drift fail closed. Lotus Manage issue `#620`
tracks the producer metadata needed for live qualification. The artifact
deliberately retains Core portfolio-state, data-mesh, Workbench,
client-publication, supported-feature, rebalance, action, order-creation,
execution, and settlement blockers.

Lotus Advise mandate/restriction runtime evidence is captured by
`scripts/advise_mandate_restriction_runtime_evidence/generate_runtime_execution.py`.
A valid artifact
referenced through `LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF` clears only
`opportunity_archetype_live_restriction_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact binds hashed
tenant, book, portfolio, client, evaluation, and correlation identity to the
producer workflow's portfolio, as-of, generation time, evaluation/source/policy
hashes, policy identity, requirement and sign-off posture, freshness, quality,
and exact diagnostic. Its closed validator reconciles every receipt and accepts
both a deterministic review candidate and a truthful no-opportunity outcome.
Unknown claims, raw scoped identifiers, source substitution, missing producer
scope/time, future/stale evidence, malformed counts/hashes, or outcome drift
fail closed. Advise issue `#459` tracks the producer metadata needed for a live
artifact to qualify. The artifact retains typed source-product, mandate-state,
restriction-clearance, suitability, policy/proposal, rebalance/order,
client-publication, data-mesh, Workbench, deployment, production, and
supported-feature blockers.

Lotus Advise mandate/restriction source-product proof is captured by
`scripts/advise_source_product_evidence/generate_source_contract.py
--capability mandate-restriction --advise-root <lotus-advise-root>`. A valid
artifact referenced through
`LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF` clears only
`opportunity_archetype_typed_restriction_source_product_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves that
`lotus-idea` consumes the typed
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1` source-product contract and
Advise-owned restriction diagnostic vocabulary for mandate, product
restriction, country restriction, and suitability-policy actionability posture.
It binds the current Advise product declaration and trust-telemetry source by
repository, ref, and SHA-256, rejects unknown claims, and preserves the
producer's blocked telemetry posture.
It deliberately retains live Advise source proof, restriction clearance,
mandate-state authority, suitability, policy, proposal, client-publication,
data-mesh, Workbench, deployment, production, and supported-feature blockers.

Lotus Advise missing-suitability runtime evidence is captured by
`scripts/advise_missing_suitability_runtime_evidence/generate_runtime_execution.py`.
A valid closed v2 artifact
referenced through `LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF` clears only
`opportunity_archetype_advise_policy_live_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1` workflow source call, current
source evidence, blocked client-publication posture, and deterministic
compliance-review candidate generation without storing evaluation identity,
request or response payloads, correlation IDs, trace IDs, candidate IDs,
source routes, requirement details, or sign-off details. It deliberately
retains suitability, policy, proposal, client-publication, data-mesh,
Workbench, and supported-feature blockers.

Lotus Advise missing risk-profile source-product proof is captured by
`scripts/advise_source_product_evidence/generate_source_contract.py
--capability missing-risk-profile --advise-root <lotus-advise-root>`. A valid
artifact referenced through
`LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF` clears only
`opportunity_archetype_typed_advise_risk_profile_source_product_missing` for
the `opportunity-archetype-scenarios` capability. The artifact proves that
`lotus-idea` consumes the typed
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1` source-product contract and
Advise-owned risk-profile diagnostic vocabulary for missing, stale, expired,
and review-due risk-profile posture. It deliberately retains live Advise source
proof, risk-profile approval, suitability, policy, proposal,
client-publication, data-mesh, Workbench, deployment, production, and
supported-feature blockers. Both typed profiles use the same closed
source-authority contract while retaining independent diagnostics and blocker
effects.

Lotus Advise missing-risk-profile runtime evidence is captured by
`scripts/advise_missing_risk_profile_runtime_evidence/generate_runtime_execution.py`.
A valid closed v2 artifact referenced through
`LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF` clears only
`opportunity_archetype_advise_risk_profile_live_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves one live
source fetch and one named application-use-case execution. Canonical request,
producer workflow, and deterministic evaluation receipts must reconcile for a
candidate or truthful no-opportunity result. It binds the
`lotus-advise:AdvisoryPolicyEvaluationRecord:v1` workflow source call, current
source evidence, explicit risk-profile diagnostic posture, and deterministic
advisor-review outcome without storing evaluation identity,
request or response payloads, correlation IDs, trace IDs, candidate IDs,
source routes, requirement details, or sign-off details. It deliberately
retains typed risk-profile source-product, risk-profile authority,
suitability, policy, proposal, sign-off, client-publication, data-mesh,
Workbench, deployment, production, and supported-feature blockers.

Durable repository proof is captured by
`scripts/persistence/generate_durable_repository_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_DURABLE_REPOSITORY_PROOF` or passed with
`--durable-repository-proof` clears only these aggregate blockers inside
generated implementation-proof readiness evidence and the operator API
readiness snapshot:

1. `durable_repository_not_configured`,
2. `repository_side_queue_pagination_not_certified`.

Both blockers require CI-execution evidence, not a source-file inventory or CI
job name. Main Releasability derives a receipt from the governed PostgreSQL
JUnit report and binds it to the exact repository, workflow/job, run id and
attempt, commit SHA and main ref, successful conclusion, and uploaded artifact
digest. The receipt must include observed migration rollback/reapply,
candidate persistence/reload and replay, concurrent identity/audit/outbox, and
repository-side queue-pagination assertions. The proof does not configure the
running service, certify production storage or deployment migrations, certify
live Core ingestion or runtime trust telemetry, prove Gateway/Workbench
behavior, or promote a supported feature. Runtime readiness endpoints continue
to report missing durable repository posture when `LOTUS_IDEA_DATABASE_URL` is
absent.

Runtime trust telemetry test execution is captured by
`scripts/runtime_trust_telemetry/generate_test_execution_contract.py`. A valid v2
artifact referenced through `LOTUS_IDEA_RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION`
or passed with `--runtime-trust-telemetry-test-execution` declares
`evidenceClass=test_execution` and `repositoryAdapter=in_memory`. It exercises
a deterministic, source-safe candidate fixture, but satisfies no aggregate
blocker. Aggregate readiness may record the artifact as supporting evidence
only.

The closed-field validator requires `runtime_candidate_snapshot_missing`,
`durable_repository_not_configured`, product-coverage, mesh-certification, and
promotion blockers to remain. It rejects claims of runtime repository use,
durable storage, API or tenant execution, deployment, production operation,
certification, and promotion. Runtime trust telemetry certification therefore
requires separate evidence from an authorized durable runtime; deterministic
test execution cannot substitute for it.

Workbench read-path source-contract proof is captured by
`scripts/workbench/generate_read_path_source_contract.py`. A valid v2 artifact
referenced through `LOTUS_IDEA_WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF` or
passed with `--workbench-read-path-source-contract-proof` records bounded
queue/detail route declarations as `source_contract` evidence. It clears no
blocker, so `workbench_gateway_bff_consumption_proof_missing` remains in
generated and operator API readiness until machine-verifiable evidence proves
Gateway serving, Workbench consumption, and entitlement enforcement. It also
does not certify a panel, browser accessibility, canonical demo runtime,
data-product publication, client-ready publication, or supported-feature
promotion.

Gateway/Workbench contract proof is captured by
`scripts/workbench/generate_contract_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT` from the
validated Workbench read-path source contract and passes it into aggregate readiness when
`LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF` is not set. A valid artifact is
classified as `source_contract`: aggregate readiness may record its evidence
reference, but it clears no blocker. In particular,
`gateway_workbench_proof_missing` remains on the source-ingestion and
outbox-delivery proof families until machine-verifiable runtime execution
evidence exists. The artifact does not clear full Workbench product proof,
Workbench panel proof, browser accessibility proof, canonical demo runtime
proof, Gateway/Workbench data-product discovery proof, client-ready
publication, or supported-feature promotion.

Gateway/Workbench discovery contract proof is captured by
`scripts/workbench/generate_discovery_contract_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_OUTPUT` from
platform catalog/onboarding evidence, the Workbench read-path source contract, and the
Gateway/Workbench contract proof. A valid v2 artifact is classified as
`source_contract`: aggregate readiness may add its evidence reference to the
data-mesh and runtime-trust telemetry capabilities, but it clears no blocker.
`gateway_workbench_discovery_proof_missing` remains until machine-verifiable
runtime evidence proves active catalog publication, Gateway serving,
Workbench consumption, and entitlement enforcement. The artifact does not
certify data-mesh products, activate producer products, publish product routes,
certify canonical Workbench behavior, or promote supported features.

Gateway/Workbench owner-mainline evidence is recorded in
`contracts/implementation-proof/rfc0002-slice11-owner-mainline-evidence.v1.json`
and guarded by `make gateway-workbench-owner-mainline-evidence-gate`. The
contract records only exact merged-main and Main Releasability evidence for the
owning `lotus-gateway` and `lotus-workbench` RFC-0002 Slice 11 dependencies.
It is not passed as blocker-clearing runtime evidence: production identity
provider proof, entitlement-denied browser proof, canonical all-main runtime
validation, data-product certification, and supported-feature promotion remain
open dependencies.

Gateway/Workbench runtime-execution proof is captured by
`scripts/workbench/generate_runtime_execution_proof.py` and guarded by
`make gateway-workbench-runtime-execution-proof-gate`. It consumes the
Workbench-owned `live-validation-summary.json`, `SHOT-INDEX.md`, and the
Idea-owned owner-mainline evidence contract. A valid artifact is classified as
`runtime_execution` and may clear only
`workbench_gateway_bff_consumption_proof_missing` when passed through
`LOTUS_IDEA_GATEWAY_WORKBENCH_RUNTIME_EXECUTION_PROOF` or
`--gateway-workbench-runtime-execution-proof` and when aggregate provenance is
current. It requires canonical portfolio `PB_SG_GLOBAL_BAL_001`, canonical
benchmark `BMK_PB_GLOBAL_BALANCED_60_40`, the RFC-0076 canonical contract,
the Workbench opportunities journey with
`sourcePosture=idea-review-queue-through-gateway`, at least one Idea candidate
queue row, and the advisory opportunities screenshot bound by the shot index.
It does not certify production identity, browser accessibility, full canonical
demo runtime, data-product publication, client-ready publication,
suitability/execution authority, or supported-feature promotion.

Outbox broker source-contract proof is captured by
`scripts/outbox/broker/generate_source_contract_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_OUTBOX_BROKER_SOURCE_CONTRACT_PROOF` or passed
with `--outbox-broker-source-contract-proof` adds a traceable evidence reference
to outbox-delivery and operator-workflow readiness. It clears no blocker.
`outbox_broker_not_configured` and `external_broker_runtime_proof_missing`
remain until separately governed runtime evidence proves external broker
configuration and publication. The artifact validates the publisher port, HTTP
adapter source contract, operator API surface, event contracts, and
`make outbox-broker-source-contract-proof-gate`; it does not certify runtime
execution, deployment, external publication, downstream consumption, platform
mesh publication, Gateway/Workbench behavior, or supported-feature promotion.

Outbox broker runtime-execution proof is captured by
`scripts/outbox/broker/generate_runtime_execution.py`. It uses the configured
`LOTUS_IDEA_OUTBOX_BROKER_URL`, publishes a source-safe certification canary
through the real `HttpOutboxEventPublisher`, and writes a bounded proof artifact
that contains only outcome posture, not event identifiers, aggregate
identifiers, raw payload, broker URL, or transport body. A valid artifact
referenced through `LOTUS_IDEA_OUTBOX_BROKER_RUNTIME_EXECUTION_PROOF` or passed
with `--outbox-broker-runtime-execution-proof` is classified as
`runtime_execution` and clears only `external_broker_runtime_proof_missing` for
the outbox/operator readiness capabilities. It does not certify downstream
consumers, platform-mesh publication, Gateway/Workbench behavior, production
identity, production certification, or supported-feature promotion. Validate the
artifact with `make outbox-broker-runtime-execution-proof-gate`.

Downstream outbox consumer contract posture is enforced by
`contracts/outbox-events/lotus-idea-outbox-consumers.v1.json` and
`make outbox-consumer-contract-gate`. The contract declares Gateway, Advise,
Manage, and Report consumers with source-authority boundaries and keeps each
consumer `contract_declared_not_runtime_certified`; it changes the outbox
blocker from `downstream_consumer_contracts_missing` to
`downstream_consumer_runtime_proof_missing` without promoting support.

Outbox consumer source-contract proof is captured by
`scripts/outbox/generate_consumer_contract_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF_OUTPUT` and passes it
into aggregate readiness when `LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF` is not
set. A valid v2 artifact is `source_contract` evidence. It proves declared
Gateway, Advise, Manage, and Report consumer coverage, consumed event types,
and authority boundaries, while explicitly retaining
`downstream_consumer_runtime_proof_missing`. It does not certify external
broker publication, consumer execution, platform mesh event publication,
Gateway/Workbench behavior, downstream delivery, client-ready publication, or
supported-feature promotion.

Outbox platform-mesh event source-contract proof is captured by
`scripts/outbox/platform_mesh/generate_source_contract_proof.py`. The
repo-native `make implementation-proof-readiness-check` target now generates
the default artifact from repo-owned outbox event/consumer contracts and
sibling `lotus-platform` source-manifest/catalog evidence under
`LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_OUTPUT`, then passes
it into aggregate readiness when
`LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF` is not set. A valid
artifact is `source_contract` evidence. It records the source-safe event
contract, declared consumer coverage, platform source-manifest inclusion, and
generated catalog mapping for proposed `lotus-idea` products. It adds a
provenance reference but clears no aggregate blocker;
`platform_mesh_event_publication_proof_missing` remains until runtime
publication evidence exists. The artifact does not establish runtime execution, a publication receipt, external broker publication, downstream delivery, deployment, production certification, Gateway/Workbench behavior, client-ready publication, or supported-feature promotion. Missing sibling evidence writes an invalid non-proof artifact; drift in present sibling evidence still exits non-zero.

Advise and Manage route source contracts are captured by
`scripts/downstream_realization/generate_advise_route_source_contract.py` and
`scripts/downstream_realization/generate_manage_route_source_contract.py`. The repo-native
`make implementation-proof-readiness-check` target now generates default
artifacts from `LOTUS_ADVISE_ROOT` and `LOTUS_MANAGE_ROOT` under
`LOTUS_IDEA_ADVISE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT` and
`LOTUS_IDEA_MANAGE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT`, then passes them into aggregate
readiness when the corresponding override variables are not set. Valid
artifacts declare `evidenceClass=source_contract`, bind the sibling contract and
route/service declarations by repository, ref, and SHA-256, and add provenance
only. They clear no blocker: `advise_live_contract_proof_missing` and
`manage_live_contract_proof_missing` remain until bounded runtime receipts
exist. Missing sibling evidence writes invalid non-proof artifacts, and drift
in present sibling evidence exits non-zero. The validators reject unknown
fields and forged runtime, authorization, tenant, downstream-acceptance,
authority, production, publication, or promotion claims.

Advise idea-intake runtime-execution evidence is captured by
`scripts/downstream_realization/generate_advise_intake_runtime_execution.py`.
The repo-native `make implementation-proof-readiness-check` target generates
the default artifact from `LOTUS_ADVISE_ROOT` using `LOTUS_ADVISE_PYTHON` and
passes it into aggregate readiness unless
`LOTUS_IDEA_ADVISE_INTAKE_RUNTIME_EXECUTION_PROOF` is set. A valid artifact is
`runtime_execution` evidence: it observes the Advise owner route serving
accepted, replayed, rejected, idempotency-conflict, authorization-denied, and
tenant-scoped idempotency calls while storing only source-safe receipt posture
and canonical receipt digests. It clears only
`advise_live_contract_proof_missing`. It does not create proposals, grant
suitability or policy authority, certify production identity, authorize client
publication, prove Gateway/Workbench behavior, or promote support.

Manage action-intake runtime-execution evidence is captured by
`scripts/downstream_realization/generate_manage_intake_runtime_execution.py`.
The repo-native `make implementation-proof-readiness-check` target generates
the default artifact from `LOTUS_MANAGE_ROOT` using `LOTUS_MANAGE_PYTHON` and
passes it into aggregate readiness unless
`LOTUS_IDEA_MANAGE_INTAKE_RUNTIME_EXECUTION_PROOF` is set. A valid artifact is
`runtime_execution` evidence: it observes the Manage owner route serving
accepted, replayed, rejected, idempotency-conflict, authorization-denied, and
tenant-scoped idempotency calls while storing only source-safe receipt posture
and canonical receipt digests. It clears only
`manage_live_contract_proof_missing`. It does not create action-register
records, grant rebalance or execution authority, create orders, certify
production identity, authorize client publication, prove Gateway/Workbench
behavior, or promote support.

Report intake route source-contract evidence is captured by
`scripts/report/generate_intake_route_source_contract.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_REPORT_ROOT` under
`LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT` and passes it into aggregate
readiness when `LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF` is not set. A valid
artifact is `source_contract` evidence: it adds the sibling declaration's
provenance but clears no blocker. In particular,
`lotus_report_live_intake_route_proof_missing` remains until governed runtime
evidence observes the owning Report route serving and accepting the handoff.
Missing sibling evidence writes an invalid non-proof artifact. It cites the merged
`lotus-report` route contract for `POST /reports/idea-evidence-packs`, the
report-owned intake route modules and tests, the `lotus-idea` downstream
contract, and the readiness endpoints. It does not create a report job, render
output, archive record, client publication, suitability decision, mandate
action, execution instruction, or supported feature.

Report materialization source-contract evidence is captured by
`scripts/report/generate_materialization_source_contract.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_REPORT_ROOT` under
`LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT` and passes it
into aggregate readiness when
`LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF` is not set. A valid
v3 artifact clears no blocker. It records
`reportOwnerMaterializationContractConsumed=true` and
`reportOwnerProofRef=sgajbi/lotus-report#152`, then adds a source-safe evidence reference while
preserving runtime materialization, rendered-output, archive-record,
client-publication, certification, and supported-feature blockers. Missing
sibling evidence writes an invalid source-contract artifact and keeps those
blockers. It cites the
merged `lotus-report` materialization contract for
`POST /reports/idea-evidence-packs/materializations`, report-owned
materialization/render/archive modules and tests, the `lotus-idea` downstream
contract, and the readiness endpoints. Sibling declarations do not prove that
a job ran, output was rendered, an archive record was created, or a retention
or legal-hold policy was applied. The artifact also does not grant
client-publication authority, suitability authority, mandate action, execution
instruction, production certification, or a supported feature.

The platform catalog source contract is generated by
`scripts/data_mesh/generate_platform_catalog_source_contract.py`. The
repo-native `make implementation-proof-readiness-check` target reads the
sibling checkout selected by `LOTUS_PLATFORM_ROOT`, writes the default artifact
to `LOTUS_IDEA_PLATFORM_CATALOG_SOURCE_CONTRACT_PROOF_OUTPUT`, and consumes it
unless `LOTUS_IDEA_PLATFORM_CATALOG_SOURCE_CONTRACT_PROOF` provides an explicit
artifact.

The v3 artifact declares `evidenceClass=source_contract` and binds the exact
platform source manifest, generated catalog, dependency graph, and maturity
matrix with repository, ref, and SHA-256 metadata. Its closed-field validator
accepts only an unpromoted maturity posture: `IdeaCandidate:v1` may be a
non-blocking `certification_candidate`, all Idea producer products must remain
`proposed`, no first-wave product can be claimed, and runtime publication, mesh
certification, producer activation, discovery certification, production
certification, supported-feature promotion, and closure fields must remain
false. A valid, current aggregate artifact can therefore satisfy only:

1. `platform_source_manifest_inclusion_missing`,
2. `platform_catalog_inclusion_missing`.

It does not certify SLO/access/evidence policy, platform runtime publication,
Gateway/Workbench discovery, deployment, production readiness, or product
support. Missing sibling evidence writes an invalid non-proof artifact and
keeps both blockers; drift in present sibling evidence remains a failing
contract condition.

Mesh policy source-contract evidence is captured by
`scripts/data_mesh/generate_mesh_policy_source_contract.py`. The repo-native
`make implementation-proof-readiness-check` target generates the default
artifact under `LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF_OUTPUT` and passes
it into aggregate readiness when
`LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF` is not set. A valid current
artifact adds a supporting evidence reference and clears no blocker. The
following policy-certification blockers remain:

1. `mesh_slo_policy_certification_missing`,
2. `mesh_access_policy_certification_missing`,
3. `mesh_evidence_policy_certification_missing`.

It digest-binds the mesh readiness, SLO, access, and evidence-pack policy
sources and cites the repo-native gates. It does not certify policy execution,
the platform mesh, producer activation, platform source-manifest/catalog
inclusion, Gateway/Workbench discovery, deployment, production readiness,
client publication, or supported-feature promotion.
`make mesh-policy-source-contract-proof-gate` validates the closed artifact
shape, authority digests, source-safe evidence refs, and zero-blocker-clearance
boundary before consumption.

AI lineage store proof is captured by
`scripts/generate_ai_lineage_store_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT` and passes it into
aggregate readiness when `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF` is not set. A
valid artifact clears only `certified_ai_lineage_store_missing` from the
AI explanation capability. It cites the AI explanation lineage migration,
rollback, governance code, persistence port, PostgreSQL adapter, PostgreSQL
runtime proof tests, and the required GitHub PostgreSQL runtime proof lane.
It does not execute `lotus-ai`, call an AI provider, expose prompts or provider
responses, prove Workbench behavior, authorize client-ready publication, or
promote a supported feature.
`make ai-lineage-store-proof-contract-gate` validates the artifact shape and
blocks source-sensitive content before the proof is consumed by aggregate
readiness.

### AI Workflow-Pack Registration Source Contract

The source-contract artifact is generated by
`scripts/ai_workflow_pack_registration/generate_source_contract_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_AI_ROOT` under
`LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT` and passes it into
aggregate readiness when `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF` is
not set.

| Evidence property | Current truth |
| --- | --- |
| Evidence class | `source_contract` |
| Source authority | `lotus-ai` |
| Blockers cleared | None |
| Runtime blocker retained | `workflow_pack_runtime_contract_not_certified` |
| Runtime/deployment observed | No |
| Product promotion | No |

The artifact cites the sibling `lotus-ai` workflow-pack phase-one spec,
registry seed, execution binding, queue policy catalog, supportability surface,
and registry/API/runtime tests for `idea_explanation.pack@v1`.
It adds a source-safe evidence reference without changing aggregate blockers.
It does not execute `lotus-ai`, observe a running registry, call an AI provider, certify runtime trust
telemetry, prove Workbench behavior, authorize client-ready publication, or
promote a supported feature.
Missing sibling evidence writes an invalid non-proof artifact and keeps the
blocker so CI remains stable without treating absence as proof; drift in
present sibling evidence still exits non-zero.
`make ai-workflow-pack-registration-proof-contract-gate` validates the artifact
shape, `source_contract` classification, empty blocker-clearance set,
source-safe evidence refs, and explicit non-execution/non-deployment posture
before aggregate readiness consumes it.

AI workflow-pack runtime execution proof is captured by
`scripts/generate_ai_workflow_pack_runtime_execution_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact by invoking `LOTUS_AI_BASE_URL` under
`LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT` and passes it into
aggregate readiness when `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF`
is not set. A valid artifact clears only
`lotus_ai_runtime_execution_missing` from the AI explanation capability and
adds `lotus_ai_live_provider_execution_missing`. The application use case sends
a synthetic redacted evidence packet through the governed
`idea_explanation.pack@v1` route. It accepts only a completed, eligible,
`lotus-idea`-scoped run whose task audit and run identity agree, whose evidence
hash matches the request, and whose review, client-publication, and downstream
authority posture remains fail-closed.

The artifact retains a bounded receipt and its digest, not the request body,
prompt, generated narrative, provider payload, candidate identity, portfolio
identity, client identity, tenant identity, or correlation identity. A
deterministic stub run proves the runtime seam and guardrails only. It does not
prove live-provider execution, signed production output acceptance, provider
rollout, runtime-trust certification, Workbench behavior, client-ready
publication, or supported-feature promotion. An unavailable or invalid runtime
writes an explicit invalid non-proof and clears no blocker.
`make ai-workflow-pack-runtime-execution-proof-contract-gate` validates the v2
receipt schema, source-safety boundary, digest binding, and one-blocker
clearance before aggregate readiness can consume it.

## Response Shape

The success response is intentionally aggregate and source-safe:

| Field | Meaning |
| --- | --- |
| `readinessStatus` | Aggregate RFC-0002 proof state, currently `blocked` |
| `supportabilityStatus` | Aggregate certification posture, currently `not_certified` |
| `capabilityCount` | Number of proof families represented in `capabilities` |
| `blockedCapabilityCount` | Number of proof families still blocked by evidence gaps |
| `overallBlockers` | Source-safe blocker codes across all proof families |
| `sourceOfTruth` | Implementation, RFC, supported-feature, demo-claim, and endpoint-ledger paths |
| `capabilities[]` | Capability-level readiness records for each proof family |
| `capabilities[].capabilityId` | Stable proof-family identifier such as `source-ingestion`, `outbox-delivery`, or `downstream-realization` |
| `capabilities[].readinessStatus` | Capability readiness derived from remaining blockers after proof artifact consumption; blocker-free capabilities report `ready` |
| `capabilities[].supportabilityStatus` | Capability supportability derived from remaining blockers after proof artifact consumption; blocker-free capabilities report `supported` |
| `capabilities[].evidenceRefs` | Source-safe implementation, endpoint, and validated proof artifact references |
| `capabilities[].blockers` | Source-safe blocker codes for that capability family |

The `opportunity-archetype-scenarios` capability reads
`contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`
and prefixes its scenario blockers with `opportunity_archetype_` so they do not
collide with source-ingestion, Workbench, data-mesh, or supported-feature
blockers from other proof families. It is a taxonomy and scenario-readiness
view only. The same contract owns a `blocker_issue_refs` map that links every
unprefixed archetype blocker to durable GitHub execution issues; the contract
gate rejects missing, stale, invalid, or non-Slice-16-anchored refs before the
blockers can be consumed as operator truth. A family-valid and
aggregate-current source-ingestion live Core proof can clear only the high-cash
live Core scenario blocker, a valid Risk
concentration proof can clear only the concentration live Risk scenario blocker,
and a valid high-volatility proof can clear only the live Risk volatility
scenario blocker,
and a valid Risk drawdown proof can clear only the drawdown source blocker.
Valid Performance, Core benchmark assignment, low-income Core cashflow, Manage
mandate, Core portfolio-state, Advise mandate/restriction source-product,
Advise mandate/restriction live, Advise missing-suitability, and Advise missing
risk-profile artifacts can clear only their own namespaced source blockers when
supplied.
High-volatility / drawdown review remains blocked on data-mesh, Workbench,
publication, and supported-feature evidence unless those separate proofs are supplied. Client-demo,
data-mesh, Workbench, publication, and supported-feature blockers remain.
Drawdown-review candidate results intentionally retain the API/persistence
family value `high_volatility` for compatibility, but implementation-proof
readiness treats the high-volatility and drawdown-review Risk evidence lanes as
separate blockers, source products, and proof variables. Do not infer that a
valid drawdown proof certifies volatility, or that a valid volatility proof
certifies drawdown.

Live canonical proof evidence from 2026-07-05 shows the aggregate consumer can
clear Risk concentration, Performance underperformance, and missing-benchmark
Performance readiness source blockers for `PB_SG_GLOBAL_BAL_001` when the
artifacts are generated from current source services and the aggregate
`IMPLEMENTATION_PROOF_EVALUATED_AT_UTC` matches the proof window. The run
cleared only:

| Proof artifact | Cleared blocker | Remaining boundary |
| --- | --- | --- |
| `output/opportunity/risk-concentration-live-proof.json` | `opportunity_archetype_live_risk_source_proof_missing` | Data-mesh certification, Workbench product proof, client publication, supported-feature promotion |
| `output/opportunity/performance-underperformance-live-proof.json` | `opportunity_archetype_live_performance_source_proof_missing` | Benchmark assignment, data-mesh certification, Workbench product proof, client publication, supported-feature promotion |
| `output/opportunity/missing-benchmark-performance-readiness-proof.json` | `opportunity_archetype_performance_benchmark_readiness_source_ref_missing` | Core missing-benchmark live proof, benchmark assignment, benchmark methodology, data-mesh certification, Workbench product proof, client publication, supported-feature promotion |

The 2026-07-05 Performance benchmark-readiness artifact used the retired flat
v1 contract. It is historical diagnostic evidence only and cannot clear the
current blocker. Generate a fresh v2 artifact before relying on this row.

## Example

```powershell
curl -H "X-Caller-Roles: operator" `
  -H "X-Caller-Capabilities: idea.implementation-proof.readiness.read" `
  "http://localhost:8330/api/v1/implementation-proof/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z"
```

## Source Safety

The endpoint returns aggregate capability posture only. It does not expose:

1. candidate identifiers,
2. portfolio identifiers,
3. client identifiers,
4. source routes,
5. source payloads,
6. outbox event identifiers,
7. aggregate identifiers,
8. raw idempotency keys,
9. broker payloads,
10. request or response bodies,
11. raw entitlement failures,
12. trace or correlation identifiers.

## Evidence

Implementation-backed evidence:

1. application builder: `src/app/application/implementation_proof_readiness.py`,
1. API route: `src/app/api/implementation_proof_readiness.py`,
1. runtime artifact loader: `src/app/runtime/proof_artifacts.py`,
1. artifact generator: `scripts/generate_implementation_proof_readiness.py`,
1. repo-native check that generates and consumes the scheduled-worker source
   contract while preserving the deployment blocker, durable repository proof,
   runtime telemetry test-execution evidence, Workbench
   read-path proof, Advise and Manage route source contracts,
   Report intake route source contract, Report materialization source contract, outbox broker
   proof, outbox consumer contract proof, and outbox platform mesh event
   publication proof artifacts, generates default AI model-risk and non-AI
   operator workflow operations proof artifacts unless explicit artifacts are
   supplied, and records validated proof refs in capability evidence:
   `make implementation-proof-readiness-check`,
1. opportunity archetype scenario contract:
   `contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`,
1. opportunity archetype contract gate:
   `make opportunity-archetype-contract-gate`,
   including allocation-drift API module, endpoint, and integration-test
   evidence refs so the scenario readiness contract cannot understate the
   bounded caller-supplied API foundation,
1. AI model-risk operations contract:
   `contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`,
1. AI model-risk operations contract gate:
   `make ai-model-risk-ops-contract-gate`,
1. AI model-risk operations proof gate:
   `make ai-model-risk-operations-proof-contract-gate`,
1. non-AI operator workflow operations contract:
    `contracts/observability/lotus-idea-operator-workflows-operations.v1.json`,
1. non-AI operator workflow operations contract gate:
    `make operator-workflows-ops-contract-gate`,
1. non-AI operator workflow operations proof gate:
    `make operator-workflows-operations-proof-contract-gate`,
1. downstream contract check: `make downstream-realization-contract-gate`,
1. report-owned planned intake contract:
   `lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`,
1. runtime trust telemetry snapshot check:
   `make runtime-trust-telemetry-snapshot-check`,
1. runtime trust telemetry snapshot endpoint:
   `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot`,
1. generated runtime telemetry evidence:
   `output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json`,
1. source-ingestion run-once endpoint:
   `POST /api/v1/source-ingestion/run-once`,
1. source-ingestion run-once runbook:
    `docs/operations/source-ingestion-run-once.md`,
1. source-ingestion runtime-execution receipt generator:
    `scripts/source_ingestion/generate_runtime_execution.py`,
1. source-ingestion block-reason diagnostics tests:
    `tests/unit/test_source_ingestion_worker.py`,
1. scheduled source-ingestion worker evidence generators:
    `scripts/source_ingestion_scheduler/`,
1. scheduled source-ingestion worker contract gate:
    `make source-ingestion-scheduled-worker-check`,
1. source-ingestion runtime-execution receipt contract gate:
    `make source-ingestion-runtime-execution-contract-gate`,
1. Risk concentration runtime-execution generator:
    `scripts/risk_concentration_runtime_evidence/generate_runtime_execution.py`,
1. Risk concentration runtime-execution contract gate:
    `make risk-concentration-live-proof-contract-gate`,
1. High-volatility runtime-execution generator:
    `scripts/high_volatility_runtime_evidence/generate_runtime_execution.py`,
1. High-volatility runtime-execution contract gate:
    `make high-volatility-live-proof-contract-gate`,
1. Risk drawdown runtime-execution generator:
    `scripts/risk_drawdown_runtime_evidence/generate_runtime_execution.py`,
1. Risk drawdown runtime-execution contract gate (compatibility target name):
    `make risk-drawdown-live-proof-contract-gate`,
1. Missing-suitability runtime-evidence generator:
    `scripts/advise_missing_suitability_runtime_evidence/generate_runtime_execution.py`,
1. Missing-suitability runtime-evidence contract gate:
    `make missing-suitability-live-proof-contract-gate`,
1. Missing risk-profile source-product proof generator:
    `scripts/advise_source_product_evidence/generate_source_contract.py
    --capability missing-risk-profile`,
1. Missing risk-profile source-product proof contract gate:
    `make missing-risk-profile-source-product-proof-contract-gate`,
1. Mandate/restriction source-product proof generator:
    `scripts/advise_source_product_evidence/generate_source_contract.py
    --capability mandate-restriction`,
1. Mandate/restriction source-product proof contract gate:
    `make mandate-restriction-source-product-proof-contract-gate`,
1. Missing risk-profile runtime-evidence generator:
    `scripts/advise_missing_risk_profile_runtime_evidence/generate_runtime_execution.py`,
1. Missing risk-profile runtime-evidence contract gate:
    `make missing-risk-profile-live-proof-contract-gate`,
1. Manage mandate runtime-evidence generator:
    `scripts/manage_mandate_runtime_evidence/generate_runtime_execution.py`,
1. Manage mandate runtime-evidence contract gate:
    `make manage-mandate-live-proof-contract-gate`,
1. Advise mandate/restriction runtime-evidence generator:
    `scripts/advise_mandate_restriction_runtime_evidence/generate_runtime_execution.py`,
1. Advise mandate/restriction runtime-evidence contract gate (compatibility target):
    `make mandate-restriction-live-proof-contract-gate`,
1. Performance underperformance runtime-execution generator:
    `scripts/performance_underperformance_runtime_evidence/generate_runtime_execution.py`,
1. Performance underperformance runtime-execution contract gate (compatibility target):
    `make performance-underperformance-live-proof-contract-gate`,
1. Missing-benchmark Performance readiness runtime-evidence generator:
    `scripts/performance_benchmark_readiness_runtime_evidence/generate_runtime_execution.py`,
1. Missing-benchmark Performance readiness runtime-evidence contract gate:
    `make missing-benchmark-performance-readiness-proof-contract-gate`,
1. Core benchmark-assignment runtime-evidence generator:
    `scripts/core_benchmark_assignment_runtime_evidence/generate_runtime_execution.py`,
1. Core benchmark assignment live-proof contract gate:
    `make core-benchmark-assignment-live-proof-contract-gate`,
1. Core portfolio-state runtime-evidence generator:
    `scripts/core_portfolio_state_runtime_evidence/generate_runtime_execution.py`,
1. Core portfolio-state runtime-evidence contract gate:
    `make core-portfolio-state-live-proof-contract-gate`,
1. Core portfolio-state runtime-evidence tests:
    `tests/unit/core_portfolio_state_runtime_evidence/`,
1. Bond maturity runtime-evidence generator:
    `scripts/bond_maturity_runtime_evidence/generate_runtime_execution.py`,
1. Bond maturity runtime-evidence contract gate:
    `make bond-maturity-live-proof-contract-gate`,
1. Bond maturity runtime-evidence tests:
    `tests/unit/bond_maturity_runtime_evidence/`,
1. Low-income Core cashflow runtime-evidence generator:
    `scripts/low_income_cashflow_runtime_evidence/generate_runtime_execution.py`,
1. Low-income Core cashflow runtime-evidence contract gate:
    `make low-income-core-cashflow-live-proof-contract-gate`,
1. Low-income Core cashflow runtime-evidence tests:
    `tests/unit/low_income_cashflow_runtime_evidence/`,
1. durable repository proof generator:
    `scripts/persistence/generate_durable_repository_proof.py`,
1. durable repository proof contract gate:
    `make durable-repository-proof-contract-gate`,
1. runtime trust telemetry test-execution evidence generator:
    `scripts/runtime_trust_telemetry/generate_test_execution_contract.py`,
1. runtime trust telemetry test-execution evidence contract gate:
    `make runtime-trust-telemetry-test-execution-contract-gate`,
1. Workbench read-path source-contract proof generator:
    `scripts/workbench/generate_read_path_source_contract.py`,
1. Workbench read-path source-contract proof gate:
    `make workbench-read-path-source-contract-proof-gate`,
1. Gateway/Workbench contract proof generator:
    `scripts/workbench/generate_contract_proof.py`,
1. Gateway/Workbench contract proof contract gate:
    `make gateway-workbench-contract-proof-contract-gate`,
1. Gateway/Workbench discovery contract proof generator:
    `scripts/workbench/generate_discovery_contract_proof.py`,
1. Gateway/Workbench discovery contract proof contract gate:
    `make gateway-workbench-discovery-contract-proof-contract-gate`,
1. Gateway/Workbench owner-mainline evidence contract:
    `contracts/implementation-proof/rfc0002-slice11-owner-mainline-evidence.v1.json`,
1. Gateway/Workbench owner-mainline evidence contract gate:
    `make gateway-workbench-owner-mainline-evidence-gate`,
1. Gateway/Workbench runtime-execution proof generator:
    `scripts/workbench/generate_runtime_execution_proof.py`,
1. Gateway/Workbench runtime-execution proof gate:
    `make gateway-workbench-runtime-execution-proof-gate`,
1. outbox broker source-contract proof generator:
    `scripts/outbox/broker/generate_source_contract_proof.py`,
1. outbox consumer contract gate:
    `make outbox-consumer-contract-gate`,
1. outbox consumer contract proof generator:
    `scripts/outbox/generate_consumer_contract_proof.py`,
1. outbox consumer contract proof contract gate:
    `make outbox-consumer-contract-proof-contract-gate`,
1. outbox consumer contract proof tests:
    `tests/unit/outbox/test_outbox_consumer_contract_proof.py`,
1. outbox broker source-contract proof gate:
    `make outbox-broker-source-contract-proof-gate`,
1. outbox broker runtime-execution proof generator:
    `scripts/outbox/broker/generate_runtime_execution.py`,
1. outbox broker runtime-execution proof gate:
    `make outbox-broker-runtime-execution-proof-gate`,
1. outbox broker runtime-execution proof tests:
    `tests/unit/outbox/broker/test_runtime_execution.py` and
    `tests/unit/outbox/broker/test_readiness_consumption.py`,
1. outbox platform-mesh event source-contract proof generator:
    `scripts/outbox/platform_mesh/generate_source_contract_proof.py`,
1. outbox platform-mesh event source-contract proof gate:
    `make outbox-platform-mesh-event-source-contract-proof-gate`,
1. outbox platform-mesh event source-contract proof tests:
    `tests/unit/outbox/platform_mesh/test_source_contract_proof.py` and
    `tests/unit/outbox/platform_mesh/test_readiness_consumption.py`,
1. Advise route source-contract generator:
    `scripts/downstream_realization/generate_advise_route_source_contract.py`,
1. Manage route source-contract generator:
    `scripts/downstream_realization/generate_manage_route_source_contract.py`,
1. downstream route source-contract gate:
    `make downstream-route-source-contract-proof-gate`,
1. downstream route source-contract tests:
    `tests/unit/downstream_realization/test_route_source_contract.py`,
1. Advise idea-intake runtime-execution proof generator:
    `scripts/downstream_realization/generate_advise_intake_runtime_execution.py`,
1. Advise idea-intake runtime-execution proof gate:
    `make advise-intake-runtime-execution-proof-gate`,
1. Advise idea-intake runtime-execution proof tests:
    `tests/unit/downstream_realization/test_advise_intake_runtime_execution.py`,
1. Manage action-intake runtime-execution proof generator:
    `scripts/downstream_realization/generate_manage_intake_runtime_execution.py`,
1. Manage action-intake runtime-execution proof gate:
    `make manage-intake-runtime-execution-proof-gate`,
1. Manage action-intake runtime-execution proof tests:
    `tests/unit/downstream_realization/test_manage_intake_runtime_execution.py`,
1. report intake route source-contract generator:
    `scripts/report/generate_intake_route_source_contract.py`,
1. report intake route source-contract gate:
    `make report-intake-route-source-contract-proof-gate`,
1. report intake route source-contract tests:
    `tests/unit/report/test_intake_route_source_contract.py`,
1. report materialization source-contract generator:
    `scripts/report/generate_materialization_source_contract.py`,
1. report materialization source-contract gate:
    `make report-materialization-source-contract-proof-gate`,
1. report materialization source-contract tests:
    `tests/unit/report/test_materialization_source_contract.py`,
1. outbox broker source-contract proof tests:
    `tests/unit/outbox/broker/test_source_contract_proof.py`,
    `tests/unit/outbox/broker/test_readiness_consumption.py`,
1. platform catalog source contract generator:
    `scripts/data_mesh/generate_platform_catalog_source_contract.py`,
1. platform catalog source contract contract gate:
    `make platform-catalog-source-contract-proof-gate`,
1. platform catalog source contract tests:
    `tests/unit/data_mesh/test_platform_catalog_source_contract.py`,
1. Workbench read-path source-contract proof tests:
    `tests/unit/workbench/test_read_path_source_contract.py`,
1. runtime trust telemetry test-execution evidence tests:
    `tests/unit/runtime_trust_telemetry/test_test_execution_contract.py`,
1. outbox delivery run-once endpoint:
    `POST /api/v1/outbox-delivery/run-once`,
1. operation event: `implementation_proof_readiness_read`,
1. endpoint ledger:
    `docs/operations/endpoint-certification-ledger.json`,
1. runtime artifact loader tests:
    `tests/unit/test_proof_artifacts.py`,
1. unit tests:
    `tests/unit/test_implementation_proof_readiness.py`,
1. durable repository proof tests:
    `tests/unit/durable_repository_proof/test_builder.py` and
    `tests/unit/durable_repository_proof/test_ci_receipt.py`,
1. generator tests:
    `tests/unit/test_generate_implementation_proof_readiness.py`,
1. AI workflow-pack registration source-contract generator:
    `scripts/ai_workflow_pack_registration/generate_source_contract_proof.py`,
1. AI workflow-pack registration proof contract gate:
    `make ai-workflow-pack-registration-proof-contract-gate`,
1. AI workflow-pack registration source-contract tests:
    `tests/unit/ai_workflow_pack_registration/test_source_contract_proof.py`,
1. AI workflow-pack runtime execution proof generator:
    `scripts/generate_ai_workflow_pack_runtime_execution_proof.py`,
1. AI workflow-pack runtime execution proof contract gate:
    `make ai-workflow-pack-runtime-execution-proof-contract-gate`,
1. AI workflow-pack runtime execution proof tests:
    `tests/unit/test_ai_workflow_pack_runtime_execution_proof.py`,
1. integration tests:
    `tests/integration/test_implementation_proof_readiness_api.py`.

The `ai-explanation` capability evidence includes the AI model-risk operations
contract, source-valid dashboard, source-valid Prometheus alert rules, runbook,
and proof gate. The v2 source-contract proof adds its evidence reference but
clears no aggregate blocker. It preserves dashboard runtime, alert-rule
runtime, `lotus-ai` execution, runtime trust telemetry, Workbench product,
client-ready publication, and supported-feature promotion blockers.

The non-AI operator workflow operations evidence includes the source-safe
dashboard, Prometheus alert rules, runbook, and proof gates for implemented
source-ingestion, outbox delivery, downstream realization, runtime trust
telemetry, and implementation-proof readiness operation events. Those refs
certify operator visibility only; live source ingestion, external broker
publication, downstream execution outcomes, Gateway/Workbench proof,
data-mesh certification, and supported-feature promotion remain separate
blockers.

Run:

```powershell
python -m pytest tests/unit/test_implementation_proof_readiness.py tests/integration/test_implementation_proof_readiness_api.py -q
make implementation-proof-readiness-check

$env:LOTUS_CORE_QUERY_BASE_URL = "http://localhost:8201"
$env:LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL = "http://localhost:8202"
$env:LOTUS_IDEA_SOURCE_INGESTION_RUNTIME_EXECUTION = "output/source-ingestion/source-ingestion-runtime-execution.json"
$env:LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF = "output/opportunity/high-volatility-live-proof.json"
$env:LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF = "output/opportunity/core-portfolio-state-live-proof.json"
$env:LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF = "output/opportunity/low-income-core-cashflow-live-proof.json"
$env:LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF = "output/opportunity/manage-mandate-live-proof.json"
$env:LOTUS_ADVISE_ROOT = "..\lotus-advise"
$env:LOTUS_ADVISE_PYTHON = "..\lotus-advise\.venv-codex\Scripts\python.exe"
$env:LOTUS_IDEA_ADVISE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT = "output/downstream/advise-route-source-contract-proof.json"
$env:LOTUS_MANAGE_ROOT = "..\lotus-manage"
$env:LOTUS_IDEA_MANAGE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT = "output/downstream/manage-route-source-contract-proof.json"
$env:LOTUS_MANAGE_PYTHON = "python"
$env:LOTUS_IDEA_MANAGE_INTAKE_RUNTIME_EXECUTION_PROOF_OUTPUT = "output/downstream/manage-intake-runtime-execution-proof.json"
$env:LOTUS_REPORT_ROOT = "..\lotus-report"
$env:LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT = "output/report/intake-route-source-contract-proof.json"
$env:LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT = "output/report/materialization-source-contract-proof.json"
$env:LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF_OUTPUT = "output/outbox/outbox-consumer-contract-proof.json"
$env:LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_OUTPUT = "output/outbox/platform-mesh/event-source-contract-proof.json"
$env:LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT = "output/workbench/gateway-workbench-contract-proof.json"
$env:LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_OUTPUT = "output/workbench/gateway-workbench-discovery-contract-proof.json"
$env:IMPLEMENTATION_PROOF_OUTPUT = "output/implementation-proof/implementation-proof-readiness.json"
make implementation-proof-readiness-check

make durable-repository-proof-contract-gate
make runtime-trust-telemetry-test-execution-contract-gate
make ai-workflow-pack-registration-proof-contract-gate
make outbox-broker-source-contract-proof-gate
make outbox-consumer-contract-proof-contract-gate
make outbox-platform-mesh-event-source-contract-proof-gate
make downstream-route-source-contract-proof-gate
make advise-intake-runtime-execution-proof-gate
make manage-intake-runtime-execution-proof-gate
make report-intake-route-source-contract-proof-gate
make report-materialization-source-contract-proof-gate
make workbench-read-path-source-contract-proof-gate
make gateway-workbench-contract-proof-contract-gate
make gateway-workbench-discovery-contract-proof-contract-gate
make source-ingestion-scheduled-worker-check
make source-ingestion-runtime-execution-contract-gate
make risk-concentration-live-proof-contract-gate
make high-volatility-live-proof-contract-gate
make risk-drawdown-live-proof-contract-gate
make manage-mandate-live-proof-contract-gate
make missing-suitability-live-proof-contract-gate
make missing-risk-profile-source-product-proof-contract-gate
make missing-risk-profile-live-proof-contract-gate
make performance-underperformance-live-proof-contract-gate
make core-benchmark-assignment-live-proof-contract-gate
make core-portfolio-state-live-proof-contract-gate
make bond-maturity-live-proof-contract-gate
make low-income-core-cashflow-live-proof-contract-gate
make downstream-realization-contract-gate
make runtime-trust-telemetry-snapshot-check
make endpoint-certification-gate
make openapi-gate
```

Use this endpoint to decide whether RFC-0002 is ready for live validation.
Use the live canonical stack only after the readiness blockers have been
cleared by implementation-backed slices.

# Implementation Proof Evidence Classification

## Purpose

Lotus Idea readiness blockers describe different kinds of claims. A source
contract can prove design presence; it cannot prove that code ran. A successful
test can prove bounded behavior; it cannot prove deployment or production
approval. This classification keeps aggregate readiness aligned with the
authority of the evidence it consumes.

## Evidence Classes

| Class | Proves | Does not prove |
| --- | --- | --- |
| `source_contract` | Governed code, schema, configuration, or contract exists. | Execution, deployment, or operational readiness. |
| `test_execution` | A bounded local test exercised named behavior. | Trusted CI identity, mainline status, or production equivalence. |
| `ci_execution` | A trusted CI lane executed named behavior for an exact commit and artifact. | Runtime deployment or production approval. |
| `runtime_execution` | A named runtime accepted and completed a bounded operation. | Deployment eligibility, live-provider use, or production certification. |
| `deployment` | A governed artifact was deployed by digest to a named environment. | Business correctness or production approval outside the deployment scope. |
| `production_certification` | The owning authority approved bounded production evidence. | Any unrelated product, compliance, suitability, or client-publication authority. |

Evidence classes do not form an inheritance hierarchy. A blocker clears only
when its contract names the same required class and all class-specific controls
pass. Stronger-sounding evidence cannot be substituted for a differently
scoped claim.

## AI Lineage Store Certification

`certified_ai_lineage_store_missing` now requires `ci_execution` evidence.
The v2 proof binds:

1. repository, workflow, and PostgreSQL job identity,
2. GitHub run id and attempt,
3. exact 40-character mainline commit and `refs/heads/main`,
4. successful conclusion and timezone-aware completion time,
5. the GitHub artifact SHA-256,
6. the governed PostgreSQL test assertions for schema, accepted write,
   reload/replay, conflict rejection, and source-safe storage.

The Main Releasability PostgreSQL job uploads its JUnit artifact before
building the receipt. `app.application.ai_lineage_store_proof` validates the
closed receipt and its enclosing digest. Source files and the Make target remain
useful `source_contract` evidence, but without the receipt the proof is invalid,
`durableAiLineageStoreBacked` is false, and the aggregate blocker remains.

This is internal design modularity inside the existing Lotus Idea deployable.
It does not justify a new service or move PostgreSQL ownership outside Lotus
Idea.

## Same-Pattern Campaign

Issue [#393](https://github.com/sgajbi/lotus-idea/issues/393) owns the wider
inventory. Corrections remain bounded so one proof family reaches `main` before
the next starts.

| Proof family | Current classification finding | Tracking |
| --- | --- | --- |
| AI workflow execution | Actual `runtime_execution` receipt implemented. | #392, merged |
| AI lineage store | Mainline digest-bound `ci_execution` receipt implemented and exact-main validated. | #396, PRs #397/#398 |
| Outbox consumer runtime | Consumer declarations are `source_contract` evidence, add evidence references only, and preserve `downstream_consumer_runtime_proof_missing`. | #404, PR #405 merged and exact-main validated at `794d8616` |
| Durable repository | Exact-main, digest-bound PostgreSQL `ci_execution` receipts are required; source evidence cannot clear durable-runtime blockers. | #401, PR #403 merged and exact-main validated at `3daa14a6` |
| Gateway/Workbench contract | Local declarations are `source_contract` evidence, add evidence references only, and preserve `gateway_workbench_proof_missing`. | #406, PR #407 merged and exact-main validated at `e09b4ffc` |
| Gateway/Workbench discovery contract | Proposed catalog entries and consumer declarations are `source_contract` evidence; they cannot prove active publication, Gateway serving, Workbench consumption, or runtime discovery. | #408, PR #409 merged and exact-main validated at `5a12dea7` |
| AI model-risk dashboard and alert source | Grafana JSON, Prometheus rule YAML, the runbook, and their static validators are `source_contract` evidence. They add a traceable evidence reference but cannot prove provisioning, rule loading/evaluation, alert delivery, deployment, or production certification and clear no aggregate blocker. | #411 merged through PR #413; exact-main validation passed at `971b3c33` after fix-forward PR #415 |
| Operator-workflows dashboard and alert source | Grafana JSON, Prometheus rule YAML, `promtool` fixtures, the runbook, and static validators are `source_contract` evidence. They add provenance but cannot prove dashboard provisioning/query execution, live rule loading/evaluation/delivery, deployment, or production certification and clear no aggregate blocker. | #412 merged through PR #417; Main Releasability `29329446874` and CodeQL `29329442570` passed on exact main SHA `a65a7f91` |
| Outbox broker source contract | The publisher port, HTTP adapter, operator API, contracts, and static tests are `source_contract` evidence. They add provenance but cannot prove that an external broker is configured or that a runtime publication occurred, and clear no aggregate blocker. | #419 merged through PR #420; Main Releasability `29333295553` and CodeQL `29333289244` passed on exact main SHA `53d714fc` |
| Platform-mesh event source contract | Repo-owned event/consumer declarations and sibling platform source-manifest/catalog entries are `source_contract` evidence. They add provenance but cannot prove runtime execution, event publication, a publication receipt, deployment, or production certification; `platform_mesh_event_publication_proof_missing` remains. | #422 merged through PR #423; Main Releasability `29337248995` and CodeQL `29337239463` passed on exact main SHA `d6f9ad69` |
| AI workflow-pack registration source contract | Sibling Lotus AI workflow-pack files, tests, seed declarations, bindings, queue policy, and supportability source are `source_contract` evidence. They add provenance but cannot prove registry execution, deployment, production approval, provider execution, Workbench realization, publication, or supported-feature promotion; `workflow_pack_runtime_contract_not_certified` remains. | #428 merged through PR #429; Main Releasability `29343992344` and CodeQL `29343983463` passed on exact main SHA `97c77006`; closure PR #430 passed exact-main validation at `c6547283` |
| Workbench read-path source contract | Local files, Make targets, and route declarations are `source_contract` evidence. They add provenance but cannot prove Gateway serving, Workbench consumption, entitlement enforcement, browser behavior, canonical runtime, publication, or support; `workbench_gateway_bff_consumption_proof_missing` remains. | #434 / PR #435 / exact-main `9b7b3eba`; Main Releasability `29351807566` and CodeQL `29351801033` passed |
| Report intake route source contract | The sibling Report contract and static route declarations are `source_contract` evidence. They add provenance but cannot prove serving, authorization, tenant isolation, request execution, materialization, render, archive, publication, or support; `lotus_report_live_intake_route_proof_missing` remains. | #437 merged through PR #439; Main Releasability `29356075075` and CodeQL `29356064752` passed on exact main SHA `1a64ef69`; wiki publication `4a43d9d` has zero drift |
| Report materialization source contract | The sibling Report materialization contract is `source_contract` evidence. It adds declaration provenance but cannot prove report-job execution, rendered output, archive creation, retention/legal-hold posture, publication, deployment, production certification, or support; all materialization/runtime blockers remain. | #438 hardened on exact main by PR #441; Main Releasability 29360465408 and CodeQL 29360459620 passed; wiki publication 5a1ca40 has zero drift |
| Platform catalog source contract | The sibling platform source manifest, generated catalog, dependency graph, and maturity matrix are digest-bound `source_contract` evidence. A valid current artifact may satisfy only source-manifest and catalog-inclusion blockers; it cannot prove runtime publication, mesh or policy certification, product activation, Gateway/Workbench discovery, deployment, production certification, or support. | #443 hardened on exact main by PR #445; Main Releasability 29365118262 and CodeQL 29365112353 passed; wiki publication 43da2ba has zero drift. Issue #444 tracks the next static-policy occurrence. |
| Mesh policy source contract | Repo-owned readiness, SLO, access, and evidence-policy declarations are digest-bound `source_contract` evidence. A valid current artifact adds supporting provenance only and cannot clear SLO, access, or evidence-policy certification blockers or prove policy operation, platform certification, product activation, Gateway/Workbench discovery, deployment, production approval, or support. | #444 hardened on exact main by PR #447; Main Releasability 29368885180 and CodeQL 29368878920 passed; wiki publication d428a88 has zero drift. |
| Advise and Manage route source contracts | Sibling contract, route, and service declarations are digest-bound `source_contract` evidence. Valid current artifacts add supporting provenance only and preserve `advise_live_contract_proof_missing` and `manage_live_contract_proof_missing`; they cannot prove route serving, authorization, tenant isolation, request acceptance, a downstream record, deployment, production certification, publication, or support. | #449 hardened on exact main by PR #450; Main Releasability 29374109211 and CodeQL 29374104007 passed; wiki publication 430491a has zero drift. |
| Runtime trust telemetry test execution | A deterministic candidate fixture executed against `InMemoryIdeaRepository` is `test_execution` evidence. Valid current evidence adds provenance only and preserves candidate-snapshot, durable-repository, product-coverage, runtime-certification, deployment, production, and promotion blockers. It cannot certify an authorized durable runtime. | #452 hardened on exact main by PR #453 at `687ae5bf`; Main Releasability `29377188016` and CodeQL `29377183417` passed; wiki publication `184ee77` has zero drift. |
| Source-ingestion runtime execution | v2 `runtime_execution` evidence must bind the actual high-cash use-case result to exact current Core source refs and durable accepted/replayed persistence receipts. In-memory runs, mixed decisions, missing records, count/hash drift, unknown claims, and self-asserted success booleans clear no blocker. A valid current artifact affects only the family live-Core posture and `opportunity_archetype_live_core_source_proof_missing`; scheduler, mesh, Gateway/Workbench, production, and promotion blockers remain. | #456 hardened on exact main by PR #457 at `3275fa92`; Main Releasability `29381069664` and CodeQL `29381066524` passed; wiki publication `41d3acd` has zero drift. |
| Signed AI attestation source contract | Lotus AI producer and Idea consumer declarations are closed v2 `source_contract` evidence. Separate authority collections bind exact repository/ref/SHA-256 records and canonical collection digests. Full cross-repository and explicit Idea-consumer-only scopes clear no blocker and cannot prove runtime/provider execution, model-risk approval, deployment, production certification, Workbench behavior, publication, or support. | #459 hardened on exact main by PR #460 at `0a9c69c7`; Main Releasability `29384199409` and CodeQL `29384195334` passed; wiki publication `cdd3095` has zero drift. |
| Risk concentration runtime execution | Closed v2 `runtime_execution` evidence invokes the authoritative concentration evaluation-and-persistence use case and binds one exact current `lotus-risk:ConcentrationRiskReport:v1` receipt to one accepted or replayed durable Idea persistence receipt. Provenance, request, source, evidence, scope, timestamp, and persistence digests must reconcile. Unknown fields, source substitution, in-memory execution, missing persistence, and receipt tampering clear no blocker. A valid current artifact affects only `opportunity_archetype_live_risk_source_proof_missing`; mesh, Gateway/Workbench, publication, deployment, production, and promotion blockers remain. | #462 hardened on exact main by PR #463 at `6f8b0acb`; Main Releasability `29388585101` and CodeQL `29388582153` passed; wiki publication `bb2b238` has zero drift. |
| High-volatility runtime execution | Closed v2 `runtime_execution` evidence invokes the authoritative high-volatility evaluation-and-persistence use case and binds one exact current `lotus-risk:RiskMetricsReport:v1` receipt to one accepted or replayed durable Idea persistence receipt. Request, source, evidence, scope, timestamp, provenance, and persistence digests must reconcile. Unknown fields, source substitution, stale or mismatched evidence, non-candidate outcomes, in-memory execution, missing persistence, and receipt tampering clear no blocker. A valid current artifact affects only `opportunity_archetype_live_risk_volatility_source_proof_missing`; drawdown, mesh, Gateway/Workbench, publication, deployment, production, and promotion blockers remain. | #465 hardened on exact main by PR #467 at `81f490ba`; Main Releasability `29391350559` and CodeQL `29391347328` passed; wiki publication `78cfcfc` has zero drift. |
| Risk drawdown runtime execution | Closed v2 `runtime_execution` evidence invokes the authoritative drawdown evaluation-and-persistence use case and binds one exact current `lotus-risk:DrawdownAnalyticsReport:v1` receipt to one accepted or replayed durable Idea persistence receipt. Request, source, evidence, scope, timestamp, provenance, and persistence digests must reconcile. Unknown fields, source substitution, stale or mismatched evidence, non-candidate outcomes, in-memory execution, missing persistence, conflicts, and receipt tampering clear no blocker. A valid current artifact affects only `opportunity_archetype_drawdown_source_proof_missing`; volatility, mesh, Gateway/Workbench, publication, deployment, production, and promotion blockers remain. | #466 hardened on exact main by PR #470 at `6d58f620`; Main Releasability `29394530188` and CodeQL `29394525914` passed; wiki publication `2c3e3c5` has zero drift. |
| Performance underperformance runtime execution | Closed v2 `runtime_execution` evidence invokes the authoritative underperformance evaluation-and-persistence use case and binds one exact current `lotus-performance:ReturnsSeriesBundle:v1` receipt to one deterministic candidate and one accepted or replayed durable Idea persistence receipt. Request, source, evidence, scope, timestamp, provenance, candidate, and persistence identities must reconcile. Unknown claims, source substitution, stale or mismatched evidence, missing benchmark context, non-candidate outcomes, in-memory execution, missing persistence, conflicts, and receipt tampering clear no blocker. A valid current artifact affects only `opportunity_archetype_live_performance_source_proof_missing`; benchmark assignment, mesh, Gateway/Workbench, publication, deployment, production, and promotion blockers remain. Official returns, benchmark-relative performance, and methodology authority remain in Lotus Performance. | #469 hardened on exact main by PR #472 at `447de580`; Main Releasability `29397869069` and CodeQL `29397864679` passed; wiki publication `784d959` has zero drift. |
| Core benchmark-assignment runtime execution | Closed v2 `runtime_execution` evidence invokes a named application use case through the Core source port and binds pseudonymous tenant/portfolio scope, exact as-of date, reporting currency, evaluation time, and one current `lotus-core:BenchmarkAssignment:v1` `SourceRef` through canonical request and receipt digests. Unknown fields, source substitution, scope or digest mismatch, stale/future evidence, inactive or ineffective assignments, and missing benchmark identity/version clear no blocker. The operation is read-only and therefore has no fabricated Idea persistence receipt. A valid current artifact affects only `opportunity_archetype_benchmark_assignment_source_ref_missing`; Performance, mesh, Gateway/Workbench, publication, deployment, production, and promotion blockers remain. Core retains benchmark-assignment authority; Performance retains return and methodology authority. | #476 hardened on exact main by PR #477 at `a0e02338`; Main Releasability `29403118436` and CodeQL `29403112996` passed; wiki publication `e90f0a2` has zero drift. |
| Core portfolio-state runtime execution | Closed v2 `runtime_execution` evidence invokes a named read-only application use case through the Core source port. Canonical receipts bind pseudonymous tenant/portfolio scope, exact as-of and evaluation time, requested baseline sections, the complete current `lotus-core:PortfolioStateSnapshot:v1` `SourceRef`, response scope/product identity, request fingerprint, snapshot identity, source hashes, restatement, reconciliation, policy, correlation, and applied/dropped sections. Unknown fields, source substitution, scope/time/digest mismatch, stale/future evidence, missing trust metadata, incomplete reconciliation, dropped sections, and receipt tampering clear no blocker. No Idea persistence receipt is fabricated. A valid current artifact affects only `opportunity_archetype_core_portfolio_state_source_ref_missing`; Manage, Performance, Risk, mesh, Gateway/Workbench, publication, deployment, production, and promotion blockers remain. | #479 hardened on exact main by PR #480 at `6bc59f56`; Main Releasability `29407946868` and CodeQL `29407941204` passed; wiki publication `c860b77` has zero drift. lotus-core #790 keeps live qualification fail-closed pending producer trust metadata. |
| Core bond-maturity runtime execution | Closed v2 `runtime_execution` evidence invokes a named read-only application use case through the Core source port. Canonical receipts bind pseudonymous tenant/portfolio scope, exact as-of/evaluation time, horizon and non-projected mode, the complete current `lotus-core:PortfolioMaturitySummary:v1` receipt, upstream `HoldingsAsOf:v1` content identity, response scope, contractual-date basis, counts, supportability, snapshot, hashes, restatement, reconciliation, policy, evidence time, and correlation. A supported empty window is a completed execution with no opportunity; partial, stale, unsupported-feature, scope-mismatched, inconsistent, or tampered evidence clears no blocker. No Idea persistence receipt is fabricated. A valid current artifact affects only `opportunity_archetype_maturity_live_core_source_proof_missing`; mesh, Gateway/Workbench, publication, deployment, production, and promotion blockers remain. | #482 implemented locally in capability-owned packages; `make check` passes all contract/static gates, MyPy over 883 source files, and 4,282 unit tests. lotus-core #792 tracks missing producer reconciliation, tenant, and correlation trust metadata, so real qualification remains fail closed pending that producer fix. |
| Other aggregate proof builders | Classification audit remains open; no unreviewed family is promoted by this capability. | #393 |

## Operating Commands

| Purpose | Command |
| --- | --- |
| Contract and tamper checks | `make ai-lineage-store-proof-contract-gate` |
| PostgreSQL behavior and JUnit evidence | `make postgres-integration-gate` |
| Mainline receipt and proof generation | `make ai-lineage-store-ci-proof` inside Main Releasability |
| Aggregate consumption | `make implementation-proof-readiness-check` with `LOTUS_IDEA_AI_LINEAGE_STORE_CI_RECEIPT` when a governed receipt is available |

The proof does not clear live Lotus AI provider, runtime-trust, Workbench,
client-publication, or supported-feature blockers. No README or
supported-features promotion follows from this correction.

## Reference Basis

The design follows GitHub's artifact-provenance model: bind an artifact to its
repository, workflow, commit, and digest, and keep verification scope explicit.
See [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
and [workflow artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts).

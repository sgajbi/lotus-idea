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
| Outbox consumer runtime | Source contract currently implies runtime execution. | #393, remediation pending |
| Durable repository | Source/Make/CI narrative currently implies durable runtime certification. | #393, remediation pending |
| Gateway/Workbench operational | Local and fixed cross-repo references currently imply operational proof. | #393, remediation pending |
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

# lotus-idea Wiki

`lotus-idea` is the Lotus wealth opportunity intelligence and idea lifecycle
service.

Current posture: RFC-0002 foundation implementation is in progress. The repo
has certified internal API foundations, proof-readiness diagnostics,
source-safe contracts, and CI guardrails, but no external business feature is
supported yet.

## Audience Paths

| Audience | Start with | Use it for |
| --- | --- | --- |
| Business and product | [Overview](Overview), [Architecture](Architecture), [Opportunity Quality Evaluation](Opportunity-Quality-Evaluation), and [Supported Features](Supported-Features) | Product blueprint, current capability truth, deterministic product-quality evidence, ownership boundaries, and promotion requirements. |
| Sales and demo | [Demo Readiness](Demo-Readiness) and [Roadmap](Roadmap) | Implementation-backed talk tracks, do-not-claim rules, and planned capability framing. |
| Operations and support | [Operations Runbook](Operations-Runbook), [Service SLO and Capacity](Service-SLO-And-Capacity), [Data Lifecycle Operations](Data-Lifecycle-Operations), [PostgreSQL Disaster Recovery](PostgreSQL-Disaster-Recovery), [Canonical Opportunity Source Proofs](Canonical-Opportunity-Source-Proofs), [Troubleshooting](Troubleshooting), [Validation and CI](Validation-and-CI), and [Security and Governance](Security-and-Governance) | Reliability budgets, supportability posture, governed privacy lifecycle, recovery, source-proof execution, diagnostics, gates, and incident first checks. |
| Engineering and agents | [Architecture](Architecture), [API Surface](API-Surface), [Integrations](Integrations), [Development Workflow](Development-Workflow), [RFC Index](RFC-Index), and [RFC-0002 Execution Status](RFC-0002-Execution-Status) | Source authority, API foundations, repo-native commands, RFC slice truth, and current GitHub execution posture. |

## Start Here

| Goal | Page |
| --- | --- |
| Understand what `lotus-idea` does | [Overview](Overview) |
| See current support truth | [Supported Features](Supported-Features) |
| Understand architecture, blueprint, and boundaries | [Architecture](Architecture) |
| Start locally | [Getting Started](Getting-Started) |
| Work on the repo | [Development Workflow](Development-Workflow) |
| Understand APIs and integrations | [API Surface](API-Surface), [Integrations](Integrations) |
| Validate changes | [Validation and CI](Validation-and-CI), [Opportunity Quality Evaluation](Opportunity-Quality-Evaluation) |
| Run live source proof | [Canonical Opportunity Source Proofs](Canonical-Opportunity-Source-Proofs) |
| Operate or troubleshoot | [Operations Runbook](Operations-Runbook), [Data Lifecycle Operations](Data-Lifecycle-Operations), [PostgreSQL Disaster Recovery](PostgreSQL-Disaster-Recovery), [Troubleshooting](Troubleshooting) |
| Prepare a safe demo | [Demo Readiness](Demo-Readiness) |
| Review governance and roadmap | [Security and Governance](Security-and-Governance), [RFC Index](RFC-Index), [RFC-0002 Execution Status](RFC-0002-Execution-Status), [Roadmap](Roadmap) |

## Current RFC-0002 Execution Posture

| Signal | Current state |
| --- | --- |
| GitHub issue posture | The dated 2026-08-31 UTC baseline is 252 label-backed RFC-0002 issues across 13 repositories: 209 closed and 43 open. |
| Open execution posture | The dated baseline split is 23 `status/blocked`, 4 `status/in-progress`, 6 `status/merged-main`, 1 `status/ready`, 9 `status/tracker`, with 0 app-actionable blocked issues. Idea #681/#685/#686/#1142 are active; Gateway #694 is ready; AI #126, Gateway #692, Idea #1155/#1156, and Workbench #953/#954 are merged-main pending issue-specific QA or closure. Normal issue resolution and lifecycle movement may advance beyond this baseline inside the seven-day freshness window; new/reopened issues or blocker growth fail the live gate. |
| Active slice work | `sgajbi/lotus-idea#681` remains the Slice 18 synchronization tracker. `#685` and `#686` are active writable Gateway/Workbench proof work, not external blockers. `#1142` owns the single-image Compose build correction. `#1155` and `#1156` have their Idea-owned implementations on exact main and await canonical consumer QA. `#1168`, `#1169`, and `#1170` are closed after exact persisted adviser-action, lifecycle-transition, and downstream-action evidence reached main with release, wiki-parity, and branch-hygiene proof. The dated Idea source ledger baseline tracks 156 RFC-0002 issues: 128 closed and 28 open. |
| Latest Idea closure truth | PR #1175 rebase-merged exact persisted downstream-action evidence to Idea main `df26f7f18c1dafb0009f8294cf08b999d1681ca0`; Main Releasability run `33360310207` and CodeQL run `33360303951` passed, wiki publication reached `44c0940` with strict parity, and branch hygiene passed. `#1170` is closed. The API returns the exact persisted Idea-owned action and fails closed for missing or ambiguous evidence without claiming Report/Render/Archive materialization or downstream authority. |
| Latest canonical QA | The canonical 13-repository journey passed Idea startup after PR #1174; the current source-owned blocker is valuation-date propagation in `sgajbi/lotus-core#1035`. This is not an Idea Compose, authentication, or Workbench workaround defect. |
| Next proof path | Complete active Idea #685/#686 and ready Gateway #694, then run fresh governed `PB_SG_GLOBAL_BAL_001` consumer QA for merged-main #1155/#1156 and their Gateway/Workbench owner issues. Keep Core #1035, production identity, protected runtime, provider/legal, client-publication, and supported-feature evidence in their own issue-backed lanes. |

See [RFC-0002 Execution Status](RFC-0002-Execution-Status) for the durable
issue-backed status map and closure boundaries.

## Evidence Standard

Treat a `lotus-idea` claim as current only when code, tests, OpenAPI or
contract evidence, documentation, supported-feature posture, CI proof, and
mainline validation agree. Route planned or partially proved capabilities to
[Roadmap](Roadmap), not to supported-feature language.

## Boundary

`lotus-idea` owns idea lifecycle, evidence, scoring, review, feedback, and
conversion intent. It does not own source calculations, suitability approval,
portfolio accounting, trade execution, rendering, archiving, or AI provider
infrastructure.

## Wiki Source And Publication

The authored wiki source lives in this repository under `wiki/`. The GitHub
wiki is the published target; it should match this source after
`Sync-RepoWikis.ps1 -Publish -Repository lotus-idea`. If GitHub does not show a
page-level edit control, update the repo-local `wiki/` file, merge it to
`main`, and publish the wiki rather than editing the publication target by
hand.

## Common Commands

```powershell
make documentation-contract-gate
make implementation-truth-gate
make supported-features-gate
make endpoint-certification-gate
```

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
| GitHub issue posture | The dated 2026-08-31 baseline is 247 label-backed RFC-0002 issues across 13 repositories: 205 closed and 42 open. |
| Open execution posture | The dated baseline split is 25 `status/blocked`, 7 `status/in-progress`, 1 `status/merged-main`, 9 `status/tracker`, with 0 app-actionable blocked issues. Gateway #691/#692 and Workbench #953/#954 are active consumer work, not blockers. Normal issue resolution and lifecycle movement may advance beyond this baseline inside the seven-day freshness window; new/reopened issues or blocker growth fail the live gate. |
| Active slice work | `sgajbi/lotus-idea#681` remains the Slice 18 synchronization tracker. `#1155` has its Idea-owned feedback taxonomy and offline-evaluation foundation on exact main while Gateway/Workbench consumer proof remains open. `#1156` has its Idea-owned effectiveness projection and visible-render receipts on exact main while Gateway/Workbench consumer proof remains open. `#1162` is closed after exact-main golden-evaluation, release, wiki-parity, and branch-hygiene proof. The dated Idea source ledger baseline tracks 152 RFC-0002 issues: 125 closed and 27 open. |
| Latest Idea closure truth | PR #1163 rebase-merged the independently authored opportunity-quality golden evaluation to exact main `f3aa9f1ddc76181d8e642cbba3712114be09254c`; Main Releasability run `33322378418` and CodeQL run `33322371179` passed. PR #1164 synchronized and published that truth on exact main `738a23daf946772e200ed36d2108fd5bbb4a934d`; Main Releasability run `33323617114`, CodeQL run `33323616468`, wiki publication `384c618`, strict parity, and branch hygiene passed. `#1162` is closed. No supported feature, live downstream, or production-runtime claim is promoted. |
| Latest canonical QA | Failed before AI/Advise proof on Workbench browser feedback-action confirmation. Workbench PR #698 is now merged and exact-main validated, but fresh canonical QA remains required. |
| Next proof path | Gateway #691/#692 and Workbench #953/#954 must consume the already merged feedback/effectiveness contracts before #1155/#1156 can close. Fresh closure-grade product proof still requires the governed `PB_SG_GLOBAL_BAL_001` canonical run from exact-main repositories. Close only issues with issue-specific queue, detail, action, feedback, conversion-intent, downstream, AI, or Advise proof. |

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

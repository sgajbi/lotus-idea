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
| Business and product | [Overview](Overview), [Architecture](Architecture), and [Supported Features](Supported-Features) | Product blueprint, current capability truth, ownership boundaries, and promotion requirements. |
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
| Validate changes | [Validation and CI](Validation-and-CI) |
| Run live source proof | [Canonical Opportunity Source Proofs](Canonical-Opportunity-Source-Proofs) |
| Operate or troubleshoot | [Operations Runbook](Operations-Runbook), [Data Lifecycle Operations](Data-Lifecycle-Operations), [PostgreSQL Disaster Recovery](PostgreSQL-Disaster-Recovery), [Troubleshooting](Troubleshooting) |
| Prepare a safe demo | [Demo Readiness](Demo-Readiness) |
| Review governance and roadmap | [Security and Governance](Security-and-Governance), [RFC Index](RFC-Index), [RFC-0002 Execution Status](RFC-0002-Execution-Status), [Roadmap](Roadmap) |

## Current RFC-0002 Execution Posture

| Signal | Current state |
| --- | --- |
| GitHub issue posture | Current posture is 205 label-backed RFC-0002 issues across 13 repositories: 168 closed and 37 open. |
| Open blocked work | 25 `status/blocked`, 0 `status/fixed-local`, 1 `status/in-progress`, 1 `status/merged-main`, 2 `status/merged-to-main`, 0 `status/pr-open`, 8 `status/tracker`, and 0 app-actionable blocked issues. |
| Active slice work | `sgajbi/lotus-idea#681` remains open as the Slice 18 synchronization tracker; `sgajbi/lotus-idea#1104` is closed after PR #1105 for Slice 19 supported-feature gate fixture refactor; `sgajbi/lotus-idea#1101` is closed after PR #1102 for Slice 09/17/19 AI workflow evaluator hardening; `sgajbi/lotus-idea#1098` is closed after main releasability GHCR-authentication retry hardening. The current Idea source ledger tracks 136 RFC-0002 issues: 111 closed and 25 open. |
| Latest Idea closure truth | `lotus-idea#1104` is closed after PR #1105 refactored the supported-feature gate implemented-feature fixture boundary to main `a5bc341501c7fb3790f329850bbf950d7ec8d3a0`; Main Releasability `31825052693`, wiki publication `897fb10`, strict wiki parity, and branch hygiene passed. PR #1106 then synchronized closure source truth to main `f257c21e0af6c2958794a860aaa518d35b8e3627` with Main Releasability `31826903476` and wiki publication `86cff66`. PR #1107 synchronized current RFC-0002 issue posture and wiki/context source truth to main `ea0b5951de8245e97e436e7e2e5cd46a1e1c2639` with Main Releasability `31828341891` and wiki publication `6f435b4`. No supported feature or production/runtime claim is promoted. |
| Latest canonical QA | Failed before AI/Advise proof on Workbench browser feedback-action confirmation. Workbench PR #698 is now merged and exact-main validated, but fresh canonical QA remains required. |
| Next proof path | Core PR #948, Gateway PR #550, Workbench PR #701, Workbench PR #708, and the latest Idea source-truth PRs are merged. Fresh closure-grade proof now requires the governed `PB_SG_GLOBAL_BAL_001` canonical run from exact-main repositories or an isolated non-conflicting QA workspace because the shared local Core and Workbench checkouts are active non-main agent branches. Close only issues with issue-specific queue, detail, action, feedback, conversion-intent, downstream, AI, or Advise proof. |

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

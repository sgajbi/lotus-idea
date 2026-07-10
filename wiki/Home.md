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
| Business and product | [Overview](Overview) and [Supported Features](Supported-Features) | Current capability truth, ownership boundaries, and promotion requirements. |
| Sales and demo | [Demo Readiness](Demo-Readiness) and [Roadmap](Roadmap) | Implementation-backed talk tracks, do-not-claim rules, and planned capability framing. |
| Operations and support | [Operations Runbook](Operations-Runbook), [Canonical Opportunity Source Proofs](Canonical-Opportunity-Source-Proofs), [Troubleshooting](Troubleshooting), [Validation and CI](Validation-and-CI), and [Security and Governance](Security-and-Governance) | Supportability posture, source-proof execution, diagnostics, gates, and incident first checks. |
| Engineering and agents | [Architecture](Architecture), [API Surface](API-Surface), [Integrations](Integrations), [Development Workflow](Development-Workflow), and [RFC Index](RFC-Index) | Source authority, API foundations, repo-native commands, and RFC slice truth. |

## Start Here

| Goal | Page |
| --- | --- |
| Understand what `lotus-idea` does | [Overview](Overview) |
| See current support truth | [Supported Features](Supported-Features) |
| Understand architecture and boundaries | [Architecture](Architecture) |
| Start locally | [Getting Started](Getting-Started) |
| Work on the repo | [Development Workflow](Development-Workflow) |
| Understand APIs and integrations | [API Surface](API-Surface), [Integrations](Integrations) |
| Validate changes | [Validation and CI](Validation-and-CI) |
| Run live source proof | [Canonical Opportunity Source Proofs](Canonical-Opportunity-Source-Proofs) |
| Operate or troubleshoot | [Operations Runbook](Operations-Runbook), [Troubleshooting](Troubleshooting) |
| Prepare a safe demo | [Demo Readiness](Demo-Readiness) |
| Review governance and roadmap | [Security and Governance](Security-and-Governance), [RFC Index](RFC-Index), [Roadmap](Roadmap) |

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

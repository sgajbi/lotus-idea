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
| Operations and support | [Operations Runbook](Operations-Runbook), [Validation and CI](Validation-And-CI), and [Security and Governance](Security-And-Governance) | Supportability posture, diagnostics, gates, and incident first checks. |
| Engineering and agents | [Architecture](Architecture), [Integrations](Integrations), [Development Workflow](Development-Workflow), and [RFC Index](RFC-Index) | Source authority, API foundations, repo-native commands, and RFC slice truth. |

## Start Here

1. [Overview](Overview)
2. [Architecture](Architecture)
3. [Getting Started](Getting-Started)
4. [Development Workflow](Development-Workflow)
5. [Validation and CI](Validation-And-CI)
6. [RFC Index](RFC-Index)
7. [Integrations](Integrations)
8. [Supported Features](Supported-Features)
9. [Operations Runbook](Operations-Runbook)
10. [Security and Governance](Security-And-Governance)
11. [Demo Readiness](Demo-Readiness)
12. [Roadmap](Roadmap)

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

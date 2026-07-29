# Incident Response

This page summarizes the authored source runbook at
`docs/runbooks/incident-response.md` for wiki readers.

Current posture: implemented internal foundation, `not_certified` for
production incident drill evidence, and no supported-feature promotion. This
is not production on-call staffing certification.

## Severity Model

| Severity | Use when | Initial response | Update cadence |
| --- | --- | ---: | ---: |
| Sev1 | Client/advisor-impacting outage, data-safety risk, unauthorized exposure risk, or unsafe opportunity workflow behavior. | 15 minutes | 30 minutes |
| Sev2 | Material workflow degradation with bounded mitigation. | 30 minutes | 60 minutes |
| Sev3 | Internal operator, proof, telemetry, or non-critical workflow issue. | 120 minutes | 240 minutes |
| Sev4 | Low-risk defect or documentation correction. | 1 business day | 1 business day |

Start at the higher severity when impact is uncertain.

## Response Flow

Detect, acknowledge, triage, assess impact, contain, communicate, recover,
verify, document, run problem review, and improve controls.

## Escalation

- Incident commander owns severity, timeline, containment, and closure.
- Lotus Idea service owner owns app behavior diagnosis, source-safe evidence,
  fix-forward plan, tests, and GitHub tracking.
- Platform runtime on-call owns ingress, deployment, runner, release image,
  environment, shared observability, and platform automation diagnosis.
- Database on-call owns PostgreSQL backup, restore, PITR, credentials, and
  cutover support.
- Security/privacy review owns exposure assessment, redaction, credential
  rotation, and privacy/legal escalation.
- Downstream owners retain source authority for Core, Performance, Risk,
  Advise, Manage, Report, Render, Archive, Gateway, Workbench, and AI.

## Source-Safe Evidence

Use GitHub issues/PRs, commit SHAs, run ids, contract ids, artifact digests,
route templates, status classes, blocker codes, and opaque support references.

Do not put tenant, client, portfolio, account, holding, payload, request body,
response body, authorization header, cookie, token, secret, DSN, hostname, raw
database query, raw exception, AI prompt, AI completion, embedding, or provider
payload values into wiki, issues, PRs, logs, or artifacts.

## Post-Incident Problem Management

Every Sev1, Sev2, and repeated Sev3 incident must create GitHub-tracked
corrective actions with owner, due date, acceptance criteria, and evaluation
condition. The review must ask what happened, why prevention/detection failed,
whether the runbook worked, what evidence was missing, and what test, gate,
alert, dashboard, runbook, wiki, context, skill, or automation should change.

## Validation

Run:

```powershell
make incident-response-contract-gate
```

The gate validates
`contracts/operations/lotus-idea-incident-response.v1.json`,
`docs/runbooks/incident-response.md`, this wiki source, and links from the
operations runbook.

## Boundaries

This page is not customer-communication approval, legal/privacy/suitability
authority, report/archive authority, authentication or authorization
implementation, production deployment certification, Gateway or Workbench
proof, data-mesh certification, protected incident-drill evidence, or
supported-feature promotion.

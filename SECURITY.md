# Security Policy

## Supported Versions

lotus-idea does not publish externally supported product releases yet. The active `main` branch is
the only supported security review target for repository code, CI, Docker runtime posture,
dependency governance, and source-safe evidence contracts.

Older branches, experimental feature branches, local generated artifacts, and unpublished RFC target
states are not supported security baselines.

## Reporting a Vulnerability

Use GitHub private vulnerability reporting or the repository security advisory workflow when it is
available to you. Do not open public GitHub issues, pull requests, or discussions for suspected
vulnerabilities.

Do not include client-identifying data, production secrets, access tokens, private portfolio data,
or proprietary bank data in reports or reproduction material. Use synthetic examples and source-safe
evidence references.

For each report, include:

- affected file, endpoint, workflow, Docker/runtime path, dependency, or GitHub setting;
- expected and observed behavior;
- source-safe reproduction steps;
- likely impact to confidentiality, integrity, availability, entitlement posture, auditability,
  evidence truth, or CI/release governance;
- any known workaround that does not weaken entitlement, audit, or source-authority controls.

## Security Scope

lotus-idea owns opportunity detection, idea lifecycle, evidence packs, scoring, review workflow,
feedback, conversion intent, and readiness posture. It does not own portfolio accounting, official
performance, risk, suitability, compliance decisions, rebalance execution, report
render/archive authority, or AI infrastructure.

Security review must preserve this product boundary. Findings that affect upstream or downstream
systems should identify the impacted Lotus repository without promoting lotus-idea into that
system's authority.

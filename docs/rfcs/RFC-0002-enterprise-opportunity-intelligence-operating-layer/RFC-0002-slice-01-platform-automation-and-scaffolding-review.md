# RFC-0002 Slice 01: Platform Automation And Scaffolding Review

Status: Implemented - platform scaffold wiki baseline verified

## Outcome

Review whether the Lotus scaffold and platform automation already support an
enterprise opportunity-intelligence service. Fix reusable gaps in
`lotus-platform` instead of patching only `lotus-idea`.

## Current Implementation Evidence

This slice is complete as a scaffold review and evidence slice. No new
`lotus-core` or `lotus-platform` code change is required from this repository
slice.

The reusable scaffold gap discovered during `lotus-idea` creation has already
been addressed in `lotus-platform`:

1. `lotus-platform` commit `549d290` (`Improve scaffold wiki baseline`) adds
   the standard repo-local wiki baseline to `automation/New-Lotus-Service.ps1`.
2. The generated wiki baseline includes `_Sidebar.md`, `Home.md`,
   `Overview.md`, `Architecture.md`, `Getting-Started.md`,
   `Development-Workflow.md`, `Validation-And-CI.md`,
   `Operations-Runbook.md`, `Security-And-Governance.md`, `Integrations.md`,
   `Roadmap.md`, and `Supported-Features.md`.
3. `lotus-platform/tests/unit/test_repository_hygiene_scaffold_contract.py`
   asserts that generated services contain the standard wiki page set,
   branch-hygiene guidance, validation/CI guidance, quality-scorecard posture,
   and supported-feature anti-claim wording.
4. `lotus-platform/docs/onboarding/LOTUS-BACKEND-SERVICE-SCAFFOLD-GUIDE.md`
   documents the generated wiki shape as part of the standard backend-service
   scaffold.
5. The current `lotus-idea/wiki/` source contains the standard page set plus
   service-specific RFC, roadmap, operations, security, integration, and
   supported-feature truth.

Explicit no-change decisions for this slice:

1. No `lotus-core` change is needed. Slice 01 is scaffold/platform evidence,
   not source-data contract implementation.
2. No new `lotus-platform` PR is needed from this slice because the previously
   identified wiki-baseline scaffold gap is already implemented and covered by
   platform tests.
3. No supported-feature promotion is allowed from this slice. It only verifies
   that future Lotus apps start with stronger repo organization, wiki source,
   CI/validation guidance, and supported-feature discipline.
4. The remaining platform follow-up from later API work, Prometheus-compatible
   FastAPI business-route registration, stays tracked separately in
   `sgajbi/lotus-platform#420` and does not block Slice 01 closure.

## Required Work

1. Review scaffolded CI lanes, OpenAPI gate, endpoint certification, supported
   features, mesh placeholders, wiki source, quality scorecard, security guard,
   and Docker baseline.
2. Compare scaffold support against RFC-0002 requirements for domain products,
   evidence packets, workflow-pack AI, review queues, conversion intents,
   trust telemetry, and live proof.
3. Add platform improvements where repeated future apps would benefit.
4. Record explicit no-change decisions when the platform scaffold is already
   sufficient.

## Current Scaffold Finding

Initial `lotus-idea` review found that the generated backend scaffold created a
strong CI/API/quality baseline but did not seed the full Lotus wiki page set.
The missing authored pages were:

1. `Getting-Started.md`,
2. `Development-Workflow.md`,
3. `Validation-And-CI.md`,
4. `Roadmap.md`.

This is a platform-scaffold issue, not just a `lotus-idea` local documentation
issue. Future Lotus apps should start with onboarding, workflow, validation,
branch-hygiene, roadmap, and supported-feature wiki structure already present.

## Slice Closure Posture

Slice 01 is closed as implemented because the required reusable scaffold
improvement exists in `lotus-platform`, the platform scaffold contract tests
cover it, and `lotus-idea` now records the evidence rather than carrying a
stale Planned status. This closure does not claim product functionality,
Gateway/Workbench proof, data-product certification, or source-adapter runtime
readiness.

## Acceptance Gate

1. A scaffold gap ledger exists in this slice evidence.
2. Required platform fixes are implemented or explicitly deferred with a claim
   narrowing decision.
3. `lotus-idea` remains generated from standard patterns and avoids local-only
   governance shortcuts.
4. Platform scaffold automation and tests include the standard wiki page set,
   or this slice records a deliberate no-change decision with evidence.
5. Architecture-boundary enforcement is blocking in repo-native local commands
   and GitHub lanes before feature implementation starts, while broad quality
   baseline metrics remain report-only until stable thresholds are justified.

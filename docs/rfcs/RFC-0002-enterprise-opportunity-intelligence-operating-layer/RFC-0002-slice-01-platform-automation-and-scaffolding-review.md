# RFC-0002 Slice 01: Platform Automation And Scaffolding Review

Status: Planned

## Outcome

Review whether the Lotus scaffold and platform automation already support an
enterprise opportunity-intelligence service. Fix reusable gaps in
`lotus-platform` instead of patching only `lotus-idea`.

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

## Acceptance Gate

1. A scaffold gap ledger exists in this slice evidence.
2. Required platform fixes are implemented or explicitly deferred with a claim
   narrowing decision.
3. `lotus-idea` remains generated from standard patterns and avoids local-only
   governance shortcuts.
4. Platform scaffold automation and tests include the standard wiki page set,
   or this slice records a deliberate no-change decision with evidence.

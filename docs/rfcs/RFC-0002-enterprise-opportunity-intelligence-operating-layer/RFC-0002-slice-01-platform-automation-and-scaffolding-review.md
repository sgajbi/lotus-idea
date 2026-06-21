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

## Acceptance Gate

1. A scaffold gap ledger exists in this slice evidence.
2. Required platform fixes are implemented or explicitly deferred with a claim
   narrowing decision.
3. `lotus-idea` remains generated from standard patterns and avoids local-only
   governance shortcuts.

# RFC-0002 Slice 00: Critical Review, Source Map, And Product Gap Allocation

Status: Planned

## Outcome

Produce the execution baseline for `lotus-idea` before implementation starts.
This slice must prove that the team understands source ownership, overlap with
existing apps, product gaps, and the first supported opportunity journey.

## Required Work

1. Inspect current `lotus-core`, `lotus-performance`, `lotus-risk`,
   `lotus-advise`, `lotus-manage`, `lotus-ai`, `lotus-report`,
   `lotus-render`, `lotus-archive`, `lotus-gateway`, and `lotus-workbench`
   source contracts, data products, RFCs, supported features, and repo contexts.
2. Create a source-authority map for every planned opportunity family.
3. Classify overlaps with Risk Watchtower, Advise copilot/proposals, Manage DPM
   action workflows, Report evidence packs, and Gateway/Workbench composition.
4. Decide the first supported end-to-end journey and the first canonical demo
   portfolio.
5. Resolve open questions from RFC-0002 Section 18 or record blockers that
   narrow the supported claim.

## Acceptance Gate

1. Every source dependency has an owner and source contract path.
2. Every downstream consumer has a realization gate.
3. No capability required for the first supported claim exists only in WTBD,
   notes, or another side ledger.
4. Branch names, local status, unmerged durable-truth branches, and initial CI
   posture are recorded.

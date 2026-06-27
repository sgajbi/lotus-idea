# RFC-0002 Slice 16: Demo Readiness, Archetype Scenarios, And Commercial Proof

Status: Partially implemented - proof-readiness diagnostic consumes the governed archetype/scenario contract as blocked scenario readiness; concentration risk review is a non-promoted bounded foundation; demo claims remain blocked

## Outcome

Prepare client-demo and commercial proof only after implementation-backed
capabilities exist.

## Current Implementation Evidence

1. `docs/demo/demo-claims.md` now records current implementation-backed
   foundation posture and keeps demo claims blocked until live proof,
   Workbench proof, data-product certification, downstream realization, and
   supported-feature evidence exist.
2. `docs/demo/README.md`, `docs/demo/client-facing-lotus-idea-brief.md`,
   `docs/demo/client-demo-operating-process.md`,
   `docs/demo/client-demo-pack.template.md`, and `wiki/Demo-Readiness.md`
   define the client-demo entry point, client-understandable Lotus Idea story,
   evidence-pack process,
   claim states, client-pack versus internal-evidence separation, acceptance
   checklist, rehearsal/follow-up discipline, and do-not-claim boundaries
   without promoting supported external product readiness.
3. `GET /api/v1/implementation-proof/readiness` gives operators and demo leads
   a source-safe blocker view across source ingestion, advisor queue, AI
   explanation, data mesh, runtime trust telemetry preview/snapshot evidence,
   outbox delivery, Workbench, downstream realization, and supported-feature
   promotion.
4. `docs/operations/implementation-proof-readiness.md` documents how to call
   and interpret the diagnostic as a readiness aid, not as demo evidence.
5. `contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`
   now records the governed opportunity archetype and scenario taxonomy for the
   first high-cash / idle-liquidity journey, a non-promoted bounded
   concentration-risk review foundation, and planned underperformance,
   allocation-drift, bond-maturity, and missing-suitability journeys.
   `make opportunity-archetype-contract-gate` protects the contract from
   unsupported demo, client-publication, data-mesh certification, or
   supported-feature promotion claims.
6. The aggregate implementation-proof readiness diagnostic now exposes an
   `opportunity-archetype-scenarios` proof family sourced from that contract.
   Its blockers are namespaced with `opportunity_archetype_` so scenario replay
   gaps do not collide with source-ingestion, Workbench, data-mesh, downstream,
   or supported-feature proof families.

This slice does not create demo-ready material. It deliberately prevents
commercial proof from getting ahead of implementation-backed runtime evidence.

## Required Work

1. Add live source-backed replay evidence for canonical and archetype scenarios
   before promoting any scenario beyond contract foundation.
2. Add deterministic seed/replay commands and expected evidence.
3. Update `docs/demo/demo-claims.md` only for supported claims.
4. Create RFP-safe and demo-safe material that explains supported, gated,
   prohibited, and degraded behavior.

## Remaining Gap

1. Canonical archetype scenarios still require live source-backed candidate
   generation and replay evidence.
2. Demo materials still require Workbench panel proof and canonical runtime
   evidence.
3. RFP-safe language must remain blocked until supported-feature promotion
   evidence exists.
4. Concentration risk review still requires live Risk source proof, upstream
   Risk consumer approval, data-mesh certification, Workbench proof, and
   supported-feature evidence before demo use.
5. Remaining planned archetypes still require source adapters, deterministic
   signal policies, and cross-repo authority proof.

## Acceptance Gate

1. Demo claims map to endpoint, UI, data-product, archetype-contract, and live
   evidence.
2. No fake calculations, fake source refs, or ungrounded AI narratives exist.
3. Canonical proof uses governed data and validation.
4. Commercial language does not imply bank adoption or unsupported production
   readiness.

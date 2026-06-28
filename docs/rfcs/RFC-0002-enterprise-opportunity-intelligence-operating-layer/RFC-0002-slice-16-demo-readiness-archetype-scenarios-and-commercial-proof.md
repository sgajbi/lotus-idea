# RFC-0002 Slice 16: Demo Readiness, Archetype Scenarios, And Commercial Proof

Status: Partially implemented - proof-readiness diagnostic consumes the governed archetype/scenario contract as blocked scenario readiness; concentration risk review, underperformance review, allocation-drift mandate review, bond maturity / reinvestment, high-volatility / drawdown review, missing suitability context, missing risk-profile review, mandate/restriction review, low-income / liquidity shortfall, and missing-benchmark review are non-promoted bounded foundations with source-specific proof contracts where implemented; typed Advise mandate/restriction source-product proof and Advise mandate/restriction live proof clear only their named blockers; demo claims remain blocked

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
   first high-cash / idle-liquidity journey, non-promoted bounded
   concentration-risk, underperformance, allocation-drift, high-volatility /
   drawdown, missing-suitability, missing risk-profile, mandate/restriction,
   low-income / liquidity-shortfall, missing-benchmark review, and bounded
   Core source-backed bond-maturity review foundations. Concentration-risk also
   has a bounded caller-supplied Risk evidence API foundation at
   `POST /api/v1/idea-signals/concentration-risk/evaluate`; it is not Workbench
   proof, client-demo proof, data-mesh certification, trade advice, rebalance
   action, or supported-feature promotion.
   `make opportunity-archetype-contract-gate` protects the contract from
   unsupported demo, client-publication, data-mesh certification, or
   supported-feature promotion claims.
6. The aggregate implementation-proof readiness diagnostic now exposes an
   `opportunity-archetype-scenarios` proof family sourced from that contract.
   Its blockers are namespaced with `opportunity_archetype_` so scenario replay
   gaps do not collide with source-ingestion, Workbench, data-mesh, downstream,
   or supported-feature proof families.
7. Source-safe live proof artifacts can clear only their source-specific
   archetype blockers: Risk concentration proof clears the live Risk blocker,
   high-volatility proof clears the live Risk volatility blocker, drawdown
   proof clears the Risk drawdown blocker, Performance underperformance proof
   clears the live Performance blocker, missing-benchmark Performance readiness
   proof clears only the Performance benchmark-readiness blocker, Core benchmark
   assignment proof clears the benchmark-assignment source-ref blocker,
   missing-benchmark Core proof clears only the missing-benchmark live Core
   source blocker, low-income Core
   cashflow proof clears the live Core cashflow source blocker, Manage mandate
   proof clears the portfolio-scoped Manage action-register blocker, Core
   portfolio-state proof clears only the Core portfolio-state source-ref
   blocker, Advise missing-suitability proof clears the live Advise policy
   blocker, typed mandate/restriction source-product proof clears only the
   typed restriction source-product blocker, mandate/restriction live proof
   clears only the Advise restriction live-source blocker, typed missing
   risk-profile source-product proof clears only the typed Advise risk-profile
   source-product blocker, and missing risk-profile live proof clears only the
   live Advise risk-profile source blocker.
   Mandate performance/risk health, data-mesh certification, Workbench proof,
   client-publication, and supported-feature blockers remain intact after
   source-specific proof.

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
4. Concentration risk review still requires live Risk source proof,
   data-mesh certification, Workbench proof, and supported-feature evidence
   before demo use. Risk consumer approval for
   `lotus-risk:ConcentrationRiskReport:v1` is source-approved and is no longer
   a concentration-review blocker.
   The source-safe Risk concentration live-proof artifact contract now exists
   and can clear only the live Risk source blocker when valid evidence is
   supplied to aggregate readiness; it is not demo, Workbench, mesh, client
   publication, or supported-feature proof.
5. Underperformance review still requires live Performance returns-series
   source proof, benchmark-assignment source-ref proof, data-mesh
   certification, Workbench proof, and supported-feature evidence before demo
   use. The current foundation consumes source-reported active return and
   benchmark context from `lotus-performance:ReturnsSeriesBundle:v1`, blocks
   missing benchmark context, and does not calculate performance methodology
   inside `lotus-idea`.
6. High-volatility review now has a bounded deterministic policy, Lotus Risk
   `RiskMetricsReport:v1` and `DrawdownAnalyticsReport:v1`
   source-port/adapter foundations, and source-safe live Risk volatility and
   drawdown proof contracts. Valid artifacts can clear only
   `opportunity_archetype_live_risk_volatility_source_proof_missing` and
   `opportunity_archetype_drawdown_source_proof_missing`; data-mesh
   certification, Workbench proof, client-publication approval, and
   supported-feature evidence remain required before demo use.
7. Missing suitability context now has a bounded deterministic policy and
   Lotus Advise `AdvisoryPolicyEvaluationRecord:v1` workflow
   source-port/adapter/live-proof foundation. It can create only a
   compliance-review candidate from Advise-owned open approval, disclosure,
   consent, or sign-off posture while preserving blocked client-publication
   posture. A valid source-safe live Advise proof clears only the missing
   suitability live-source blocker; data-mesh certification, Workbench proof,
   client-publication approval, and supported-feature evidence remain required
   before demo use.
8. Missing risk-profile review now has a bounded deterministic policy and
   Lotus Advise `AdvisoryPolicyEvaluationRecord:v1` explicit risk-profile
   diagnostic source-port/adapter/live-proof foundation plus a separate
   source-safe typed Advise risk-profile source-product proof. It can create
   only an advisor-review evidence-gap candidate from Advise-owned missing,
   stale, expired, or review-due risk-profile diagnostic posture. A valid
   source-product proof clears only
   `opportunity_archetype_typed_advise_risk_profile_source_product_missing`;
   a valid source-safe live Advise proof clears only
   `opportunity_archetype_advise_risk_profile_live_source_proof_missing`;
   data-mesh certification, Workbench proof, client-publication approval, and
   supported-feature evidence remain required before demo use.
9. Allocation drift / mandate review now has a bounded deterministic policy,
   Lotus Manage `PortfolioActionRegister:v1` source-port/adapter foundation,
   source-safe Manage mandate live-proof contract, and source-safe Core
   portfolio-state live-proof contract. Valid artifacts clear only
   `opportunity_archetype_portfolio_scoped_manage_source_proof_missing` and
   `opportunity_archetype_core_portfolio_state_source_ref_missing`;
   mandate performance-health, mandate risk-health, data-mesh certification,
   Workbench proof, client-publication approval, supported-feature evidence,
   rebalance authority, action authority, order creation, execution, and
   settlement remain required before demo use.
10. Low-income / liquidity shortfall now has a bounded deterministic policy,
   Lotus Core cashflow source-port/adapter foundation, source-safe Core
   cashflow live-proof contract, and contract-backed archetype entry. It can
   create only advisor-review candidates from Core
   `PortfolioCashflowProjection:v1` and `PortfolioCashMovementSummary:v1`
   evidence, and a valid proof artifact can clear only
   `opportunity_archetype_live_core_cashflow_source_proof_missing`. It must
   not be presented as client income-needs planning, funding advice,
   suitability, treasury instruction, Workbench proof, data-mesh certification,
   client publication, or supported-feature promotion.
11. Bond maturity / reinvestment now has a bounded deterministic policy and
   Core `HoldingsAsOf:v1` maturity-date source-port/adapter/live-proof plus
   caller-supplied API foundation. The API can create only advisor-review
   candidates from Core-owned maturity facts and cannot recommend products,
   calculate reinvestment advice, approve suitability, create orders, publish
   client communication, or promote support. A valid source-safe artifact
   clears only the live Core maturity-source blocker; no replacement product
   recommendation, reinvestment advice, maturity schedule authority,
   suitability, order execution, Workbench proof, data-mesh certification,
   client publication, or supported-feature promotion is implied.
12. Missing-benchmark review now has a bounded deterministic policy and Core
   benchmark-assignment source-port wrapper. It can create only advisor-review
   evidence-gap candidates from Core-owned missing, inactive, ineffective, or
   unversioned benchmark assignment posture. Live Core source proof,
   Performance benchmark-readiness source refs, Workbench proof, data-mesh
   certification, client publication, supported-feature promotion, benchmark
   assignment, benchmark methodology, and benchmark-return calculation remain
   blocked.
13. Mandate/restriction review now has a bounded deterministic policy,
   source-safe caller-supplied API foundation, typed Advise
   `AdvisoryPolicyEvaluationRecord:v1` source-product proof, and separate
   source-safe Advise live-proof contract. It can create only compliance-review
   candidates from explicit source-owned restriction posture. A valid
   source-product proof clears only
   `opportunity_archetype_typed_restriction_source_product_missing`, and a
   valid live proof clears only
   `opportunity_archetype_live_restriction_source_proof_missing`; mandate
   change authority, product/country restriction clearance, suitability
   approval, order creation, Workbench proof, data-mesh certification, client
   publication, and supported-feature promotion remain blocked.
14. Remaining planned archetypes still require source adapters, deterministic
   signal policies, and cross-repo authority proof.

## Acceptance Gate

1. Demo claims map to endpoint, UI, data-product, archetype-contract, and live
   evidence.
2. No fake calculations, fake source refs, or ungrounded AI narratives exist.
3. Canonical proof uses governed data and validation.
4. Commercial language does not imply bank adoption or unsupported production
   readiness.

# RFC-0002 Slice 04: Source Authority, Signal Contracts, And Data Mesh Baseline

Status: Partially implemented

## Outcome

Turn the source map into machine-readable consumer and producer contracts.

## Current Baseline

The repository now carries proposed source-truth mesh contracts:

1. `contracts/domain-data-products/lotus-idea-products.v1.json`
2. `contracts/domain-data-products/lotus-idea-consumers.v1.json`
3. `contracts/domain-data-products/mesh-readiness.v1.json`
4. `contracts/trust-telemetry/idea-candidate.telemetry.v1.json`
5. `contracts/mesh-slo/lotus-idea-idea-candidate.slo.v1.json`
6. `contracts/mesh-access/lotus-idea-idea-candidate.access.v1.json`
7. `contracts/mesh-evidence/lotus-idea-idea-candidate.evidence-pack-policy.v1.json`

The baseline is deliberately not certified. Products remain `proposed`, the
static telemetry snapshot is blocked, and platform mesh promotion waits for
implementation-backed runtime evidence.

The consumer declaration is aligned to the Slice 00 source map. Current
declared upstream source products are:

1. `lotus-core:PortfolioStateSnapshot:v1`,
2. `lotus-core:HoldingsAsOf:v1`,
3. `lotus-core:PortfolioCashMovementSummary:v1`,
4. `lotus-core:PortfolioCashflowProjection:v1`,
5. `lotus-core:BenchmarkAssignment:v1`,
6. `lotus-performance:ReturnsSeriesBundle:v1`,
7. `lotus-performance:BenchmarkExposureContext:v1`,
8. `lotus-performance:MandatePerformanceHealthContext:v1`,
9. `lotus-risk:RiskMetricsReport:v1`,
10. `lotus-risk:MandateRiskHealthContext:v1`,
11. `lotus-risk:RegimeScenarioPackEvaluation:v1`,
12. `lotus-advise:AdvisoryProposalLifecycleRecord:v1`,
13. `lotus-advise:AdvisoryPolicyEvaluationRecord:v1`,
14. `lotus-advise:AdvisoryCopilotInteractionRecord:v1`,
15. `lotus-manage:PortfolioActionRegister:v1`,
16. `lotus-report:ClientReportEvidencePack:v1`.

The first high-cash / idle-liquidity journey depends on the Core portfolio
state, holdings/cash balance, cash movement, and cashflow projection products.
Performance, risk, Advise, Manage, Report, and AI-facing dependencies are
declared now to keep the first-wave RFC source map coherent, but they must not
be consumed in runtime behavior until the corresponding implementation slice
adds source adapters, tests, OpenAPI/API proof where applicable, and
supportability handling.

## Required Work

1. Keep `contracts/domain-data-products/` declarations current for
   `lotus-idea` consumer dependencies and proposed producer products.
2. Maintain freshness, source-owner, compatibility, quality, access, SLO, and
   evidence-policy fields for the first promoted product family.
3. Add validation tests or repo-native commands for every declaration expansion.
4. Reconcile exact upstream product names with platform-generated catalogs.

## Acceptance Gate

1. Consumer declarations name real source owners.
2. Producer declarations remain proposed until implementation-backed.
3. Placeholder mesh files do not exist in `contracts/` or operations docs.
4. Platform mesh validation passes before any certification claim.
5. No source fact is accepted without provenance and freshness posture.

## Validation Evidence

Current local validation:

1. `tests/unit/test_data_mesh_foundation_contract.py` asserts the declared
   consumer dependencies include the current source-authority products from
   Slice 00.
2. `make check` validates JSON contract readability through the unit suite and
   keeps producer products proposed and blocked from certification.

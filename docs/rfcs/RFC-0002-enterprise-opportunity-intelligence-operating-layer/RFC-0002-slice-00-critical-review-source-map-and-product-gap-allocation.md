# RFC-0002 Slice 00: Critical Review, Source Map, And Product Gap Allocation

Status: Completed - implementation baseline recorded

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

## Execution Baseline

This slice is the required implementation-start baseline for RFC-0002. It
does not promote any supported feature. `lotus-idea` remains foundation-only
until later slices implement runtime behavior, endpoint certification,
data-product certification, docs/wiki truth, and supported-feature evidence.

Review inputs:

1. `C:\Users\Sandeep\Downloads\LOTUS_IDEA_BLUEPRINT.md`.
2. `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`.
3. `lotus-platform/context/playbooks/ENTERPRISE-BACKEND-REFACTORING-INSTRUCTIONS.md`.
4. `lotus-platform/generated/domain-product-catalog.json`.
5. Repository engineering contexts for `lotus-core`, `lotus-performance`,
   `lotus-risk`, `lotus-advise`, `lotus-manage`, `lotus-ai`, `lotus-report`,
   `lotus-render`, `lotus-archive`, `lotus-gateway`, and `lotus-workbench`.
6. Public market-pattern references already listed in RFC-0002 Section 1.

Market research conclusion: the external market pattern validates governed
advisor opportunity intelligence, portfolio-grounded insight, AI-assisted
commentary, human review, evidence lineage, and model-risk governance. It does
not change Lotus source ownership. Lotus implementation truth remains the code,
contracts, tests, RFCs, platform standards, data-product evidence, and live
validation.

## Source-Authority Map

| Opportunity family | Required source products | Owner decision | `lotus-idea` responsibility |
| --- | --- | --- | --- |
| High cash / idle liquidity | `lotus-core:PortfolioStateSnapshot:v1`, `lotus-core:HoldingsAsOf:v1`, `lotus-core:PortfolioCashMovementSummary:v1`, `lotus-core:PortfolioCashflowProjection:v1` | `lotus-core` owns cash, holdings, portfolio state, cash movement, projected cashflow, and related data-quality/freshness posture. | Detect source-backed idle-liquidity candidates, preserve source refs, apply deterministic eligibility policy, and route for advisor review. |
| Concentration | `lotus-risk:RiskMetricsReport:v1`; later `ConcentrationRiskReport` if added to the consumer contract | `lotus-risk` owns concentration methodology, risk metrics, issuer/position calculations, and risk supportability. | Use risk-owned concentration evidence as an opportunity input without recomputing concentration. |
| Underperformance | `lotus-performance:ReturnsSeriesBundle:v1`, `lotus-performance:MandatePerformanceHealthContext:v1`, `lotus-core:BenchmarkAssignment:v1` | `lotus-performance` owns returns, benchmark-aware performance, active-return posture, and methodology evidence; `lotus-core` owns benchmark assignment. | Convert source-owned performance concern into an idea candidate with explicit degraded/stale benchmark handling. |
| Allocation drift / mandate drift | `lotus-manage:PortfolioActionRegister:v1`, `lotus-performance:MandatePerformanceHealthContext:v1`, `lotus-risk:MandateRiskHealthContext:v1`, `lotus-core:PortfolioStateSnapshot:v1` | `lotus-manage` owns DPM model/rebalance/action workflow truth; `lotus-performance` and `lotus-risk` own mandate health analytics; `lotus-core` owns source state. | Detect cross-domain opportunity posture and create review-gated conversion intent, not DPM workflow state. |
| Bond maturity / reinvestment | `lotus-core:PortfolioStateSnapshot:v1`, `lotus-core:HoldingsAsOf:v1`, future maturity-specific source product if required | `lotus-core` owns instrument/holding maturity facts. | Keep as planned until maturity fields/source contract are explicitly proven for the supported journey. |
| Low income / liquidity shortfall | `lotus-core:PortfolioCashflowProjection:v1`, `lotus-core:PortfolioCashMovementSummary:v1`, future client-income-needs products if required | `lotus-core` owns cashflow/liquidity evidence; financial-planning advice remains out of scope unless a source owner supplies a governed product. | Keep as evidence-gated; do not infer income-needs planning or funding advice. |
| High volatility / drawdown | `lotus-risk:RiskMetricsReport:v1`, `lotus-risk:MandateRiskHealthContext:v1` | `lotus-risk` owns volatility, drawdown, tracking-error, scenario, and risk methodology. | Queue source-backed risk attention candidates without recalculating risk or becoming risk watchtower. |
| Missing benchmark | `lotus-core:BenchmarkAssignment:v1`, `lotus-performance:ReturnsSeriesBundle:v1` | `lotus-core` owns benchmark identity; `lotus-performance` owns benchmark-aware return readiness. | Create evidence-gap candidate only; do not assign benchmark. |
| Missing risk profile / suitability context | `lotus-advise:AdvisoryProposalLifecycleRecord:v1`, `lotus-advise:AdvisoryPolicyEvaluationRecord:v1` where applicable | `lotus-advise` owns suitability, policy evaluation, advisory approvals, consent, and proposal lifecycle. | Block advisory conversion or mark missing-evidence posture; do not approve suitability or policy. |

The first implementation family is **high cash / idle liquidity** because it
has the clearest source authority, the fewest cross-repo behavior dependencies,
strong demo explainability, and direct alignment with the blueprint's
deterministic-first opportunity engine. It also avoids beginning with risk,
performance, or DPM calculation ownership leakage.

## Active Source Product Contracts

| Product | Source contract path | Current route family |
| --- | --- | --- |
| `lotus-core:PortfolioStateSnapshot:v1` | `lotus-core/contracts/domain-data-products/lotus-core-products.v1.json` | `/integration/portfolios/{portfolio_id}/core-snapshot` |
| `lotus-core:HoldingsAsOf:v1` | `lotus-core/contracts/domain-data-products/lotus-core-products.v1.json` | `/portfolios/{portfolio_id}/positions`, `/portfolios/{portfolio_id}/cash-balances` |
| `lotus-core:PortfolioCashMovementSummary:v1` | `lotus-core/contracts/domain-data-products/lotus-core-products.v1.json` | `/portfolios/{portfolio_id}/cash-movement-summary` |
| `lotus-core:PortfolioCashflowProjection:v1` | `lotus-core/contracts/domain-data-products/lotus-core-products.v1.json` | `/portfolios/{portfolio_id}/cashflow-projection` |
| `lotus-core:BenchmarkAssignment:v1` | `lotus-core/contracts/domain-data-products/lotus-core-products.v1.json` | `/integration/portfolios/{portfolio_id}/benchmark-assignment` |
| `lotus-performance:ReturnsSeriesBundle:v1` | `lotus-performance/contracts/domain-data-products/lotus-performance-products.v1.json` | `/integration/returns/series`, `/integration/returns/series/results/{calculation_id}` |
| `lotus-performance:BenchmarkExposureContext:v1` | `lotus-performance/contracts/domain-data-products/lotus-performance-products.v1.json` | `/integration/benchmarks/exposure-context` |
| `lotus-performance:MandatePerformanceHealthContext:v1` | `lotus-performance/contracts/domain-data-products/lotus-performance-products.v1.json` | `/performance/mandate-health-context` |
| `lotus-risk:RiskMetricsReport:v1` | `lotus-risk/contracts/domain-data-products/lotus-risk-products.v1.json` | `/analytics/risk/calculate` |
| `lotus-risk:MandateRiskHealthContext:v1` | `lotus-risk/contracts/domain-data-products/lotus-risk-products.v1.json` | `/analytics/risk/mandate-health-context` |
| `lotus-risk:RegimeScenarioPackEvaluation:v1` | `lotus-risk/contracts/domain-data-products/lotus-risk-products.v1.json` | `/analytics/risk/regime-scenario-pack/evaluate` |
| `lotus-advise:AdvisoryProposalLifecycleRecord:v1` | `lotus-advise/contracts/domain-data-products/lotus-advise-products.v1.json` | `/advisory/proposals/{proposal_id}`, `/advisory/proposals/{proposal_id}/versions/{version_no}`, `/advisory/proposals/{proposal_id}/timeline`, `/advisory/proposals/{proposal_id}/approvals` |
| `lotus-advise:AdvisoryPolicyEvaluationRecord:v1` | `lotus-advise/contracts/domain-data-products/lotus-advise-products.v1.json` | `/advisory/policy-evaluations/*`, `/advisory/proposals/*/policy-evaluations` |
| `lotus-advise:AdvisoryCopilotInteractionRecord:v1` | `lotus-advise/contracts/domain-data-products/lotus-advise-products.v1.json` | `/advisory/copilot/*`, `/advisory/proposals/*/copilot-runs` |
| `lotus-manage:PortfolioActionRegister:v1` | `lotus-manage/contracts/domain-data-products/lotus-manage-products.v1.json` | `/api/v1/rebalance/supportability/summary`, `/api/v1/rebalance/runs/{rebalance_run_id}/artifact`, `/api/v1/rebalance/runs/{rebalance_run_id}/workflow`, `/api/v1/rebalance/workflow/decisions` |
| `lotus-report:ClientReportEvidencePack:v1` | `lotus-report/contracts/domain-data-products/lotus-report-products.v1.json` | `/reports/client-evidence-packs/{portfolio_id}`, `/reports/portfolios/{portfolio_id}/review` |

## Overlap And Movement Decisions

| Area | Stays in owning app | Belongs in `lotus-idea` |
| --- | --- | --- |
| `lotus-risk` risk watchtower / risk analytics | Risk methodology, concentration, drawdown, volatility, scenario, affected-cohort evaluation, and risk supportability. | Cross-domain opportunity lifecycle, ranking, review queue, and conversion intent that cites risk evidence. |
| `lotus-performance` performance analytics | Returns, attribution, benchmark-relative metrics, active-return posture, and methodology truth. | Underperformance candidate lifecycle and stale/partial evidence handling. |
| `lotus-core` portfolio state | Portfolio, holdings, cash, benchmark identity, instrument/client/product facts, cashflow, and source readiness. | Source-reference validation and idea candidate creation from source-owned facts. |
| `lotus-advise` proposals and copilot | Proposal lifecycle, suitability, policy evaluation, approvals, consent, client-advice posture, and advisory copilot execution/review. | Pre-proposal opportunity candidate, advisor review posture, and advisory conversion intent only. |
| `lotus-manage` DPM operating system | Rebalance, model portfolio, mandate health, construction, proof packs, action register, campaign/wave/action workflow, and PM execution supportability. | PM-relevant opportunity candidate and manage conversion intent without creating DPM actions locally. |
| `lotus-ai` shared AI service | Workflow-pack registry/execution, provider policy, prompt/version governance, evaluation, safety, async runtime, run ledger, and model-risk supportability. | Evidence-bounded AI request orchestration and consumption of returned run posture; no direct provider calls. |
| `lotus-report` / `lotus-render` / `lotus-archive` | Report package assembly, deterministic rendering, archive lifecycle, retention, retrieval, legal hold, and access audit. | Reviewed idea evidence handoff contracts and reportability posture. |
| `lotus-gateway` / `lotus-workbench` | Product-facing composition and rendered review UX. | Backend idea truth only; Gateway/Workbench must not infer or rank ideas locally. |

No existing app should move implemented source calculations or workflow authority
into `lotus-idea`. The only movement is conceptual: opportunity discovery and
idea lifecycle should start in `lotus-idea` rather than being embedded inside
Advise copilot, Manage DPM action queues, or Workbench UI logic.

## First Supported Journey Decision

Initial journey:

1. canonical portfolio: `PB_SG_GLOBAL_BAL_001`;
2. opportunity family: high cash / idle liquidity;
3. first audience: advisor review only;
4. first source dependencies: `PortfolioStateSnapshot:v1`, `HoldingsAsOf:v1`,
   `PortfolioCashMovementSummary:v1`, and `PortfolioCashflowProjection:v1`;
5. first output: source-backed idea candidate and evidence packet ready for
   advisor review;
6. first downstream path: report-only evidence handoff after review, followed
   by Advise/Manage conversion only when their acceptance contracts are
   implemented in later slices;
7. first AI posture: missing-evidence checker and unsupported-claim verifier
   before rationale drafting.

This sequence gives a useful demo path without claiming suitability,
performance/risk methodology, DPM action creation, client communication, or
client-ready publication.

## RFC-0002 Section 18 Answers

1. Exact product names are listed in the source-contract table above and remain
   governed by `lotus-platform/generated/domain-product-catalog.json`.
2. First opportunity family: high cash / idle liquidity.
3. First persistence posture: pure domain model first, then synchronous
   database-backed records in Slice 6; event publication remains after durable
   replay/idempotency is proven.
4. First review audience: advisor only.
5. Initial rank policy: deterministic scorecard by source supportability,
   materiality, freshness, review urgency, duplication/suppression posture, and
   evidence completeness under an explicit policy version.
6. Automatic expiry: stale source evidence, expired as-of date, superseded
   source hash, unsupported source dependency, duplicate supersession, and
   time-sensitive maturity/cashflow windows. Manual closure: advisor rejection,
   no-action, suppression, and downstream conversion abandonment.
7. First conversion path: report-only evidence after advisor review. Advise and
   Manage conversion remain planned until their consumer acceptance contracts
   are implemented.
8. Canonical demo portfolio: `PB_SG_GLOBAL_BAL_001`.
9. First AI workflow: missing-evidence checker and unsupported-claim verifier;
   rationale draft follows only after deterministic evidence packets and review
   posture exist.
10. Platform scaffold gaps: no blocking scaffold gap for Slice 3. Reusable
    lessons are already captured in the current scaffold/CI/docs baseline;
    later slices must update `lotus-platform` automation if implementation
    exposes a repeatable gap.

## Branch, Stranded-Truth, And CI Baseline

Baseline state at implementation start:

1. start branch: `feature/rfc0002-slice00-implementation-baseline`;
2. base branch: `origin/main`;
3. `git fetch origin --prune`: completed before this baseline update;
4. `git branch -r --no-merged origin/main`: no unmerged remote durable-truth
   branches reported for `lotus-idea`;
5. supported-feature posture: remains `foundation_only`;
6. data-mesh posture: repo-local declarations remain proposed/not certified
   until runtime telemetry and platform certification are implemented;
7. next low-risk implementation slice: Slice 3 pure domain model, vocabulary,
   and lifecycle.

## PR-Sized Implementation Sequence

Use small linear commits and one small PR per coherent implementation surface
unless a slice is explicitly documentation-only:

1. **Foundation PR**: Slice 00 baseline, Slice 03 pure domain model, Slice 04
   source-contract alignment, and first Slice 05 high-cash domain policy. No
   API, persistence, or supported-feature promotion.
2. **Source-adapter PR**: ports and application orchestration for Core high-cash
   evidence, including source readiness, entitlement-denied, stale-source, and
   missing-source paths. No public support claim until endpoint certification.
3. **Persistence PR**: Slice 06 durable candidate/evidence records,
   idempotency, replay hashes, and audit events.
4. **Queue/scoring PR**: Slice 07 scoring/ranking/suppression queue projection
   over persisted candidates, with policy-versioned deterministic behavior.
5. **Review PR**: Slice 08 advisor review, feedback, suppression/no-action, and
   audit APIs.
6. **API certification PR**: Slice 10 certified idea/candidate/evidence/review
   APIs, OpenAPI examples, endpoint-certification ledger, and no-alias
   vocabulary proof.
7. **Gateway/Workbench PRs**: Slice 11 product-surface realization through
   Gateway-only Workbench consumption and browser/accessibility proof.
8. **AI PR**: Slice 09 missing-evidence and unsupported-claim verifier workflow
   through `lotus-ai`, with deterministic fallback and no rationale drafting
   until evidence/review posture is proven.
9. **Downstream conversion PRs**: Slice 12 Advise/Manage acceptance contracts
   and Slice 13 report/render/archive materialization, each in owner repos when
   authority belongs there.
10. **Promotion/hardening PRs**: Slices 14-20 data-product promotion, trust
    telemetry, observability/security, demo proof, documentation/wiki/context,
    live validation, final hardening, and branch hygiene. Supported features
    can be promoted only in these proof-backed PRs.

## Documentation And Wiki Decision

This slice updates RFC truth and repository/wiki navigation only. It does not
change public supported features, API behavior, endpoint certification, or
data-product certification. Wiki source is updated because operator-facing
roadmap/RFC navigation now needs to reflect that Slice 00 is complete and the
first implementation journey is high cash / idle liquidity.

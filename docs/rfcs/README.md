# RFC Index

`lotus-idea` is implemented only through governed RFC slices. The repository is
currently in foundation state; business features remain planned until their RFCs
carry implementation evidence, endpoint certification, data-product posture,
tests, docs, wiki, and supported-feature promotion.

## Active RFC Suite

1. [RFC-0001: Repository Foundation And Service Boundary](RFC-0001-repository-foundation-and-service-boundary.md)
2. [RFC-0002: Enterprise Opportunity Intelligence Operating Layer](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-enterprise-opportunity-intelligence-operating-layer.md)

## RFC-0002 Slice Evidence Files

| Slice | Evidence file | Status |
| --- | --- | --- |
| 0 | [Critical Review, Source Map, And Product Gap Allocation](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-00-critical-review-source-map-and-product-gap-allocation.md) | Completed - implementation baseline recorded |
| 1 | [Platform Automation And Scaffolding Review](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-01-platform-automation-and-scaffolding-review.md) | Planned |
| 2 | [Cleanup, Structure, And Current Surface Normalization](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-02-cleanup-structure-and-current-surface-normalization.md) | Planned |
| 3 | [Opportunity Domain Model, Vocabulary, And Lifecycle](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-03-opportunity-domain-model-vocabulary-and-lifecycle.md) | Implemented - pure domain foundation only |
| 4 | [Source Authority, Signal Contracts, And Data Mesh Baseline](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-04-source-authority-signal-contracts-and-data-mesh-baseline.md) | Partially implemented - repo-native mesh contract gate enforced |
| 5 | [Deterministic Signal Evaluation And Candidate Generation](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-05-deterministic-signal-evaluation-and-candidate-generation.md) | Partially implemented - high-cash domain policy plus Core source-port foundation |
| 6 | [Persistence, Replay, Idempotency, And Audit](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-06-persistence-replay-idempotency-and-audit.md) | Partially implemented - internal persistence plus high-cash orchestration foundation only |
| 7 | [Scoring, Ranking, Suppression, And Queue Policy](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-07-scoring-ranking-suppression-and-queue-policy.md) | Partially implemented - internal scoring and queue projection foundation only |
| 8 | [Review Queues, Feedback, And Human Governance](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-08-review-queues-feedback-and-human-governance.md) | Partially implemented - internal advisor review and feedback governance foundation only |
| 9 | [Governed AI Explanation And Model-Risk Controls](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-09-governed-ai-explanation-and-model-risk-controls.md) | Partially implemented - internal AI governance foundation only |
| 10 | [Certified APIs, OpenAPI, And Gateway Contract](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-10-certified-apis-openapi-and-gateway-contract.md) | Partially implemented - certified high-cash API foundation only |
| 11 | [Workbench Product Realization](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-11-workbench-product-realization.md) | Planned |
| 12 | [Advise And Manage Conversion Realization](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md) | Partially implemented - internal conversion governance foundation only |
| 13 | [Report, Render, Archive, And Evidence-Pack Materialization](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-13-report-render-archive-and-evidence-pack-materialization.md) | Planned |
| 14 | [Data Product Promotion, Trust Telemetry, And Platform Hardening](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-14-data-product-promotion-trust-telemetry-and-platform-hardening.md) | Planned |
| 15 | [Observability, Security, Entitlements, And Operations](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-15-observability-security-entitlements-and-operations.md) | Planned |
| 16 | [Demo Readiness, Archetype Scenarios, And Commercial Proof](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-16-demo-readiness-archetype-scenarios-and-commercial-proof.md) | Planned |
| 17 | [Implementation Proof And Live Validation](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-17-implementation-proof-and-live-validation.md) | Planned |
| 18 | [Documentation, Wiki, Support, And Agent Context](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-18-documentation-wiki-support-and-agent-context.md) | Planned |
| 19 | [Second-Last Hardening And Review](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-19-second-last-hardening-and-review.md) | Planned |
| 20 | [Final Closure And Branch Hygiene](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-20-final-closure-and-branch-hygiene.md) | Planned |
| 21 | [Post-Completion Communication And LinkedIn Draft](RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-21-post-completion-communication-and-linkedin-draft.md) | Planned |

## RFC Rules

Every implementation RFC must include:

1. source authority and dependency map,
2. business outcome and non-goals,
3. data contracts and OpenAPI impact,
4. security, privacy, entitlement, and model-risk impact,
5. observability, audit, support, and operations evidence,
6. test pyramid and certification plan,
7. documentation, wiki, and supported-feature updates,
8. platform/scaffold improvement slice where reusable gaps are found,
9. cleanup/refactor slice,
10. implementation proof slice,
11. second-last hardening and review slice,
12. final closure slice,
13. post-completion communication decision when public or thought-leadership
    material may be created from implementation outcomes.

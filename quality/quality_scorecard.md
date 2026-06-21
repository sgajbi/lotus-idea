# Bank-Buyable Quality Scorecard

Repository: lotus-idea
Service profile: domain-service

Use this scorecard to track movement toward the Lotus Bank-Buyable Engineering Contract.

| Control Area | Current Status | Evidence | Gap | Next Slice |
| --- | --- | --- | --- | --- |
| Architecture | `Partially implemented` | Layered package skeleton plus blocking architecture-boundary gate and report-only architecture evidence. | Service-specific boundaries not yet implemented. | Replace scaffold placeholders with real module map and ownership truth. |
| API and contracts | `Partially implemented` | Health, readiness, metadata, OpenAPI gate, endpoint certification ledger. | Business endpoints not yet implemented. | Add certification evidence with each endpoint. |
| Data and methodology | `Planned` | No business data scope promoted. | Domain methodology not yet applicable. | Add source-owner and methodology docs when data behavior exists. |
| Security and privacy | `Partially implemented` | No-sensitive-content guard and product-safe errors. | AuthN/AuthZ posture is service-specific. | Add explicit security model before protected APIs. |
| Observability and supportability | `Partially implemented` | Correlation/trace headers, structured logs, health/readiness, metrics. | Business supportability states not yet implemented. | Add operation metrics and runbook updates with real workflows. |
| Resilience and performance | `Partially implemented` | Readiness drain baseline and Docker healthcheck. | Timeout/retry/back-pressure posture is service-specific. | Add resilience policy with downstream clients. |
| Testing | `Partially implemented` | Unit, integration, e2e scaffold tests. | Business behavior tests not yet implemented. | Add high-value tests with each feature slice. |
| CI and release evidence | `Partially implemented` | Feature, PR merge, main releasability workflows enforce lint, typecheck, architecture boundaries, OpenAPI, supported features, endpoint certification, security, tests, coverage, and Docker. | Broad quality metrics remain report-only until stable thresholds are justified. | Promote additional deterministic gates after measured baseline. |
| Documentation and operations | `Partially implemented` | README, repo context, wiki, runbooks, standards placeholders. | Operator docs are scaffold-level. | Replace placeholders with implementation-backed truth. |

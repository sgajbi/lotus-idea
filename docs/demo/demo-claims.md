# Demo Claims

This file is the starting demo-readiness ledger for `lotus-idea`.

Do not promote demo claims from `Planned` until code, tests, endpoint certification, supported
feature evidence, and validation artifacts exist.

Allowed status vocabulary:

1. `Implemented`
2. `Partially implemented`
3. `Planned`
4. `Not applicable`
5. `Unknown - requires owner review`

## Functional Capability Matrix

| Capability | Status | Evidence | Gap | Next step |
| --- | --- | --- | --- | --- |
| Service-specific business workflow | `Planned` | None. | No business workflow is implemented by the scaffold. | Add implementation, tests, endpoint certification, supported-feature evidence, and demo proof. |
| Health and readiness diagnostics | `Implemented` | `/health`, `/health/live`, `/health/ready`, integration tests. | Dependency-aware readiness is service-specific. | Add real dependency checks when integrations exist. |
| Metadata diagnostics | `Implemented` | `/metadata`, e2e smoke test. | Domain metadata is service-specific. | Add service-owned metadata only when implementation needs it. |

## Non-Functional Capability Matrix

| Capability | Status | Evidence | Gap | Next step |
| --- | --- | --- | --- | --- |
| Product-safe errors | `Implemented` | `app.errors.ProblemDetails`, generated tests. | Domain-specific denied/degraded errors are not implemented. | Add endpoint-specific errors with tests. |
| Correlation and trace propagation | `Implemented` | `CorrelationIdMiddleware`, integration tests. | Cross-service propagation depends on real downstream clients. | Certify per integration. |
| Architecture boundary reporting | `Partially implemented` | `make architecture-boundary-report`. | Report-only until governance promotes it. | Keep report-only until low-noise policy is proven. |
| Security authorization model | `Partially implemented` | Caller-context and capability-policy placeholders. | No production authentication or service-specific authorization model. | Implement caller extraction and policy decisions for real endpoints. |
| Mesh certification | `Planned` | None unless mesh placeholders are explicitly requested. | Not certified. | Add repo-owned mesh declarations, telemetry, SLO/access/evidence policies, and pass certification. |

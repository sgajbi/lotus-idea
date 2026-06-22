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
| High-cash opportunity evaluation and internal candidate persistence | `Partially implemented` | `POST /api/v1/idea-signals/high-cash/evaluate`, `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`, `POST /api/v1/idea-candidates/{candidateId}/evidence-replay`, `GET /api/v1/source-ingestion/readiness`, endpoint certification ledger, unit/integration tests, manifest-backed run-once ingestion worker CLI and `make source-ingestion-worker-check`, repository persistence tests, and PostgreSQL source-ingestion replay/conflict recovery proof. | Internal foundation only; evidence replay is an operator posture check over existing repository state, and the readiness diagnostic reports blockers but no deployed/live Core source-ingestion worker proof, Gateway route, Workbench panel, mesh certification, or supported-feature promotion exists. | Implement deployed/live source-ingestion worker proof, downstream proof, Gateway/Workbench contracts, live validation evidence, and supported-feature registration before demo promotion. |
| Review, feedback, conversion, and report evidence-pack intent workflow | `Partially implemented` | Internal review queue, review action, feedback, conversion intent/outcome, and report evidence-pack request APIs with endpoint certification and tests. | Intent and internal tracking only; no downstream proposal, manage-review, report/render/archive materialization, suitability, execution, client communication, or supported-feature promotion. | Add downstream realization proof and governed consumer contracts before demo promotion. |
| Health and readiness diagnostics | `Implemented` | `/health`, `/health/live`, `/health/ready`, integration tests. | Dependency-aware readiness is service-specific. | Add real dependency checks when integrations exist. |
| Metadata diagnostics | `Implemented` | `/metadata`, e2e smoke test. | Domain metadata is service-specific. | Add service-owned metadata only when implementation needs it. |

## Non-Functional Capability Matrix

| Capability | Status | Evidence | Gap | Next step |
| --- | --- | --- | --- | --- |
| Product-safe errors | `Implemented` | `app.errors.ProblemDetails`, generated tests. | Domain-specific denied/degraded errors are not implemented. | Add endpoint-specific errors with tests. |
| Correlation and trace propagation | `Implemented` | `CorrelationIdMiddleware`, integration tests. | Cross-service propagation depends on real downstream clients. | Certify per integration. |
| Architecture boundary enforcement | `Implemented` | `make architecture-boundary-gate` is blocking in `make check`, `make ci`, and GitHub lanes; `make architecture-boundary-report` remains available for evidence refresh. | Current architecture-boundary scope is enforced; new modules must remain inside declared boundaries. | Expand boundary rules only when new package ownership creates a real enforcement need. |
| Security authorization model | `Partially implemented` | Caller-context extraction, role/capability policy checks, route-level authorization tests, and product-safe denial responses. | No production identity-provider integration or Gateway-authenticated product surface proof. | Certify caller propagation and authorization through Gateway/Workbench before demo promotion. |
| Mesh certification | `Planned` | Repo-owned proposed producer and consumer declarations, blocked static trust telemetry, and planned SLO/access/evidence policies. | Not certified and not implementation-backed. | Implement runtime products, emit live telemetry, include `lotus-idea` in the platform source manifest, and pass mesh certification. |

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
| High-cash opportunity evaluation and internal candidate persistence | `Partially implemented` | `POST /api/v1/idea-signals/high-cash/evaluate`, `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`, `POST /api/v1/idea-candidates/{candidateId}/evidence-replay`, `GET /api/v1/source-ingestion/readiness`, endpoint certification ledger, unit/integration tests, manifest-backed run-once ingestion worker CLI, `make source-ingestion-worker-check` manifest/output-contract proof, repository persistence tests, PostgreSQL source-ingestion replay/conflict recovery proof, and bounded read-only Gateway publication for advisor queue and candidate detail. | Internal foundation only; evidence replay is an operator posture check over existing repository state, and the readiness diagnostic reports blockers but no deployed/live Core source-ingestion worker proof, Workbench panel, mesh certification, or supported-feature promotion exists. | Implement deployed/live source-ingestion worker proof, downstream proof, Workbench contracts, live validation evidence, and supported-feature registration before demo promotion. |
| Review, feedback, conversion, and report evidence-pack intent workflow | `Partially implemented` | Internal review queue, review action, feedback, conversion intent/outcome, report evidence-pack request APIs, source-safe downstream adapter foundations, endpoint certification, and tests. | Intent and internal tracking only; no certified live downstream proposal, manage-review, report/render/archive materialization, suitability, execution, client communication, or supported-feature promotion. | Add downstream realization proof and governed consumer contracts before demo promotion. |
| Internal outbox delivery readiness | `Partially implemented` | `GET /api/v1/outbox-delivery/readiness`, source-safe HTTP publisher adapter foundation, endpoint certification ledger, unit/integration tests, and `outbox_delivery_readiness_read` operation event. | Operator diagnostic and adapter foundation only; it reports aggregate outbox backlog/status posture, durable repository posture, broker configuration posture, adapter presence, and blockers without certifying live broker runtime, exposing event identifiers, calling downstream services, proving Gateway/Workbench behavior, or promoting a supported feature. | Prove live broker runtime, downstream consumer contracts, platform mesh event certification, Gateway/Workbench proof, and supported-feature evidence before demo promotion. |
| Downstream realization readiness | `Partially implemented` | `GET /api/v1/downstream-realization/readiness`, source-safe downstream adapter foundations, endpoint certification ledger, unit/integration tests, planned Advise/Manage/Report contract-readiness records, and `downstream_realization_readiness_read` operation event. | Operator diagnostic and adapter foundation only; it reports workflow counts, adapter-foundation presence, planned contract posture, and Advise/Manage/Report/Render/Archive blockers but does not prove downstream route existence, create downstream records, prove Gateway/Workbench behavior, or promote a supported feature. | Use it to drive downstream realization slices; do not use it as demo evidence until blockers are cleared by live cross-repo proof. |
| Health and readiness diagnostics | `Implemented` | `/health`, `/health/live`, `/health/ready`, integration tests. | Dependency-aware readiness is service-specific. | Add real dependency checks when integrations exist. |
| Metadata diagnostics | `Implemented` | `/metadata`, e2e smoke test. | Domain metadata is service-specific. | Add service-owned metadata only when implementation needs it. |
| RFC-0002 implementation proof readiness diagnostic | `Partially implemented` | `GET /api/v1/implementation-proof/readiness`, endpoint certification ledger, unit/integration tests, generated readiness artifact proof, and `implementation_proof_readiness_read` operation event. | Operator diagnostic only; it aggregates blockers and source-of-truth refs across source ingestion, advisor queue, AI explanation, data mesh, runtime telemetry, outbox delivery, Workbench, downstream realization, and supported-feature promotion; it does not provide live implementation proof, certified live broker runtime, Workbench proof, downstream realization, data-product certification, or supported-feature promotion. | Use it to drive the next proof slices; do not use it as demo evidence until every reported blocker is cleared by implementation-backed proof. |

## Non-Functional Capability Matrix

| Capability | Status | Evidence | Gap | Next step |
| --- | --- | --- | --- | --- |
| Product-safe errors | `Implemented` | `app.errors.ProblemDetails`, generated tests. | Domain-specific denied/degraded errors are not implemented. | Add endpoint-specific errors with tests. |
| Correlation and trace propagation | `Implemented` | `CorrelationIdMiddleware`, integration tests. | Cross-service propagation depends on real downstream clients. | Certify per integration. |
| Architecture boundary enforcement | `Implemented` | `make architecture-boundary-gate` is blocking in `make check`, `make ci`, and GitHub lanes; `make architecture-boundary-report` remains available for evidence refresh. | Current architecture-boundary scope is enforced; new modules must remain inside declared boundaries. | Expand boundary rules only when new package ownership creates a real enforcement need. |
| Security authorization model | `Partially implemented` | Caller-context extraction, role/capability policy checks, route-level authorization tests, product-safe denial responses, and bounded read-only Gateway caller-context forwarding for advisor queue and candidate detail. | No production identity-provider integration, Workbench entitlement-denied panel proof, or supported product-surface proof. | Certify caller propagation and authorization through Workbench before demo promotion. |
| Mesh certification | `Planned` | Repo-owned proposed producer and consumer declarations, blocked static trust telemetry, and planned SLO/access/evidence policies. | Not certified and not implementation-backed. | Implement runtime products, emit live telemetry, include `lotus-idea` in the platform source manifest, and pass mesh certification. |

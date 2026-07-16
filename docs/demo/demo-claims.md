# Demo Claims

This file is the starting demo-readiness ledger for `lotus-idea`.

Do not promote demo claims from `Planned` until code, tests, endpoint certification, supported
feature evidence, and validation artifacts exist.

Use [Lotus Idea Client Demo Operating Process](client-demo-operating-process.md) before preparing
external material. It defines the client-facing story, evidence pack, validation commands,
acceptance checklist, and do-not-claim boundaries that keep this ledger safe for client demos.

Allowed status vocabulary:

1. `Implemented`
2. `Partially implemented`
3. `Planned`
4. `Not applicable`
5. `Unknown - requires owner review`

Risk concentration evidence is valid only when the closed v2
`runtime_execution` contract binds the authoritative Lotus Risk source receipt
to an accepted or replayed durable Idea persistence receipt. It can affect only
the live-Risk source blocker and does not promote demo, client-publication,
production, or supported-feature posture.

## Functional Capability Matrix

| Capability | Status | Evidence | Gap | Next step |
| --- | --- | --- | --- | --- |
| High-cash opportunity evaluation and internal candidate persistence | `Partially implemented` | `POST /api/v1/idea-signals/high-cash/evaluate`, `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`, `POST /api/v1/idea-candidates/{candidateId}/evidence-replay`, `GET /api/v1/source-ingestion/readiness`, `POST /api/v1/source-ingestion/run-once`, endpoint certification ledger, unit/integration tests, manifest-backed run-once ingestion worker CLI, deployable scheduled-worker entrypoint, `make source-ingestion-worker-check`, `make source-ingestion-scheduled-worker-check`, `make source-ingestion-runtime-execution-contract-gate`, repository persistence tests, PostgreSQL source-ingestion replay/conflict recovery proof, bounded read-only Gateway publication for advisor queue and candidate detail, and bounded read-only Workbench queue/detail rendering merged in `lotus-workbench` PR #391. | Internal and read-only product-surface foundation only; evidence replay is an operator posture check, run-once returns aggregate decision counts, and valid current v2 runtime evidence must bind exact Core refs to durable accepted/replayed receipts. It affects only the source-ingestion and high-cash live-Core posture. Scheduler observation, Workbench actions, feedback, conversion affordances, entitlement-denied proof, mesh certification, production certification, live downstream proof, and supported-feature promotion remain absent. | Implement live validation evidence, downstream proof, remaining Workbench contracts, mesh certification, and supported-feature registration before demo promotion. |
| Opportunity archetype and scenario contract | `Partially implemented` | Governed archetype JSON, typed loader, deterministic policy/source tests, bounded signal APIs, and capability-owned proof gates. Advise missing-suitability, mandate/restriction, and missing-risk-profile now use closed v2 runtime-execution contracts over exact request, producer-workflow, and candidate/no-opportunity receipts; source-product proof remains separate. See [implementation proof readiness](../operations/implementation-proof-readiness.md) for the evidence inventory. | Each artifact clears only its namespaced source blocker. Official source calculations and decisions, data-mesh certification, Workbench proof, client publication, deployment, production, and supported-feature promotion remain blocked. | Complete the remaining authority-specific proof issues, full journey replay, Workbench/downstream proof, mesh certification, and promotion evidence. |
| Review, feedback, conversion, and report evidence-pack intent workflow | `Partially implemented` | Internal review queue, review action, feedback, conversion intent/outcome, report evidence-pack request APIs, certified internal downstream submission APIs, source-safe downstream application orchestration and adapter foundations, digest-bound Advise, Manage, and Report route source-contract consumption, bounded Report materialization source-contract consumption, endpoint certification, integration tests, and deterministic critical workflow e2e proof. | Intent, submission posture, non-clearing route declarations, and internal tracking only; source contracts clear no blocker and do not prove route serving or acceptance, a materialization job, rendered output, archive record, client communication, client publication, or supported-feature promotion. | Add governed downstream authority proof, product-surface proof, and supported-feature evidence before demo promotion. |
| Internal outbox delivery readiness and run-once | `Partially implemented` | `GET /api/v1/outbox-delivery/readiness`, `POST /api/v1/outbox-delivery/run-once`, repo-owned outbox event and downstream consumer contracts, source-safe HTTP publisher adapter foundation, PostgreSQL repository-side readiness projection, durable retry scheduling with first/last failure timing, due retry eligibility, and retry-deferred aggregate counts, bounded broker, downstream consumer, and platform-mesh event source-contract proof artifacts, plus Gateway/Workbench contract evidence, endpoint certification ledger, unit/integration tests, and `outbox_delivery_readiness_read` / `outbox_delivery_run_once` operation events. | Operator diagnostic, bounded operator action, event/consumer contracts, adapter foundation, and source-contract evidence only; it reports aggregate outbox backlog/status posture, due retry posture, retry-deferred failed-row count, durable repository posture, broker configuration posture, adapter presence, run summary counts, and blockers without certifying external broker or platform-mesh event publication, exposing event identifiers, calling downstream services beyond a configured publisher adapter, proving full Gateway/Workbench product behavior, proving downstream delivery, authorizing client-ready publication, or promoting a supported feature. | Prove external broker and platform-mesh event publication, full Gateway/Workbench product proof, downstream delivery evidence, and supported-feature evidence before demo promotion. |
| Downstream realization readiness | `Partially implemented` | `GET /api/v1/downstream-realization/readiness`, `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions`, `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions`, source-safe downstream application orchestration and adapter foundations, endpoint certification ledger, unit/integration tests, planned Advise/Manage/Report contract-readiness records, digest-bound Advise, Manage, and Report route source-contract consumption, Report materialization source-contract consumption, and `downstream_realization_readiness_read` / `downstream_realization_submission` operation events. | Operator diagnostic, submission posture, adapter foundation, and bounded route-declaration provenance only; source-contract evidence clears no blocker and does not prove route serving or acceptance, intake runtime, materialization execution, rendered output, archive creation, suitability or rebalance/execution authority, Gateway/Workbench behavior, client publication, or a supported feature. | Use it to drive downstream realization slices; do not use it as demo evidence until client publication, suitability/rebalance authority, product-surface, data-product, and supported-feature blockers are cleared by live cross-repo proof. |
| Health and readiness diagnostics | `Implemented` | `/health`, `/health/live`, `/health/ready`, integration tests. | Dependency-aware readiness is service-specific. | Add real dependency checks when integrations exist. |
| Metadata diagnostics | `Implemented` | `/metadata`, e2e smoke test. | Domain metadata is service-specific. | Add service-owned metadata only when implementation needs it. |
| RFC-0002 implementation proof readiness diagnostic | `Partially implemented` | `GET /api/v1/implementation-proof/readiness`, endpoint certification ledger, unit/integration tests, generated readiness artifact proof, AI lineage store proof generation/consumption, actual deterministic-stub Lotus AI runtime receipt consumption, digest-bound Advise, Manage, Report intake, and Report materialization source contracts, outbox broker and consumer evidence, bounded platform-mesh event source-contract proof generation/consumption, and `implementation_proof_readiness_read` operation event. | Operator diagnostic only; it aggregates blockers and source-of-truth refs across source ingestion, advisor queue, AI explanation, data mesh, runtime telemetry, outbox delivery and bounded outbox proof family, Workbench, downstream realization, and supported-feature promotion. Source contracts add provenance but leave their live blockers in place. It does not provide full live implementation proof, live-provider/production AI certification, certified external broker or platform-mesh event publication, full Workbench live proof, route serving or acceptance, suitability/rebalance authority, data-product certification, client-ready publication, or supported-feature promotion. | Use it to drive the next proof slices; do not use it as demo evidence until every reported blocker is cleared by implementation-backed proof. |

High-volatility API proof is now part of the internal opportunity archetype
foundation. `POST /api/v1/idea-signals/high-volatility/evaluate` consumes only
caller-supplied Lotus Risk `RiskMetricsReport:v1` volatility evidence and is
covered by bounded API, endpoint-certification, and operation-event tests. It
does not fetch Risk sources, calculate volatility, approve Risk methodology,
recommend trades, create rebalance actions, prove Workbench behavior, authorize
client publication, certify data mesh, or promote a supported feature.

Separate high-volatility v2 runtime evidence invokes the authoritative source
adapter and evaluation-and-persistence use case. It binds current Risk evidence
to accepted or replayed durable Idea persistence and may clear only the
volatility live-source blocker. This is implementation proof, not a claim of
Workbench realization, deployment, production certification, client
publication, official risk methodology, or supported-feature promotion.

Missing-benchmark review is now an internal bounded foundation under the
opportunity archetype/scenario contract. It has deterministic policy and Core
benchmark-assignment source-port proof plus bounded Performance benchmark-readiness
proof consumption; it does not assign benchmarks, calculate performance or
benchmark returns, certify methodology, prove Workbench behavior, authorize
client publication, or promote a supported feature.

Missing risk-profile review is now an internal bounded foundation under the
opportunity archetype/scenario contract. It creates advisor-review candidates
only from explicit Advise-owned risk-profile diagnostic posture, including the
bounded `POST /api/v1/idea-signals/missing-risk-profile/evaluate` API over
caller-supplied Advise evidence, and does not approve risk profiling,
suitability, policy, proposal, client publication, or external communication.

## Non-Functional Capability Matrix

| Capability | Status | Evidence | Gap | Next step |
| --- | --- | --- | --- | --- |
| Product-safe errors | `Implemented` | `app.errors.ProblemDetails`, generated tests. | Domain-specific denied/degraded errors are not implemented. | Add endpoint-specific errors with tests. |
| Correlation and trace propagation | `Implemented` | `CorrelationIdMiddleware`, integration tests. | Cross-service propagation depends on real downstream clients. | Certify per integration. |
| Architecture boundary enforcement | `Implemented` | `make architecture-boundary-gate` is blocking in `make check`, `make ci`, and GitHub lanes; `make architecture-boundary-report` remains available for ignored on-demand evidence refresh. | Current architecture-boundary scope is enforced by the blocking gate; generated reports are not durable proof by themselves. | Expand boundary rules only when new package ownership creates a real enforcement need. |
| Security authorization model | `Partially implemented` | Caller-context extraction, role/capability policy checks, signal-evaluation advisor-role plus `idea.signal.evaluate` enforcement, generated OpenAPI caller-context security publication, production-like trusted-ingress provenance guard for privileged `X-Caller-*` headers, `make caller-context-contract-gate`, `make signal-api-contract-gate`, `make endpoint-certification-gate`, route-level authorization tests, product-safe denial responses, and bounded read-only Gateway caller-context forwarding for advisor queue and candidate detail. | Trusted-ingress marker is not production identity-provider integration, signed assertion proof, Workbench entitlement-denied panel proof, client-ready authorization certification, or supported product-surface proof. | Certify identity-provider or signed caller assertions plus caller propagation and authorization through Workbench before demo promotion. |
| Mesh certification | `Planned` | Repo-owned proposed producer and consumer declarations, blocked static trust telemetry, and planned SLO/access/evidence policies. | Not certified and not implementation-backed. | Implement runtime products, emit live telemetry, include `lotus-idea` in the platform source manifest, and pass mesh certification. |

# API Certification Baseline

Every endpoint added after scaffold creation must include:

1. domain-correct tag grouping,
2. clear what/when/how description,
3. complete request and response examples,
4. product-safe error examples,
5. attribute descriptions, types, and examples,
6. focused unit or integration tests for success and failure behavior,
7. OpenAPI gate coverage before merge.

The machine-readable source for endpoint certification tracking is:

- docs/operations/endpoint-certification-ledger.json

Run `make endpoint-certification-gate` before promoting any endpoint as supported. The gate now
blocks weak certification by requiring:

1. every public OpenAPI operation to have exactly one ledger entry,
2. required evidence fields for purpose, usage, non-usage boundaries, examples, tests, and OpenAPI,
3. valid JSON request and response examples when an example is JSON-shaped,
4. real `tests/path.py::test_name` references,
5. `baseline_certified` status only for health/metadata baseline endpoints,
6. certified business/operator endpoints to name an `idea.*` capability,
7. certified endpoints to preserve Gateway, Workbench, and supported-feature-promotion boundaries,
8. product-safe 403 behavior and `scripts/openapi_quality_gate.py` evidence,
9. bounded operation-event test evidence for every certified business/operator endpoint,
10. exact bounded read-only `lotus-gateway` route citation before a ledger entry can claim Gateway
    publication, while still preserving Workbench, data-product, client-ready publication, and
    supported-feature boundaries.

## Certified Foundation Endpoints

The current certified foundation inventory is:

| Endpoint | Foundation Scope | Required Capability | Current Boundary |
| --- | --- | --- | --- |
| `POST /api/v1/idea-signals/high-cash/evaluate` | High-cash deterministic evaluation over caller-supplied, source-owned Core evidence. | `idea.signal.evaluate` or advisor role | No live source ingestion, durable state, Gateway, Workbench, mesh certification, or supported-feature promotion. |
| `POST /api/v1/idea-signals/high-cash/evaluate-and-persist` | High-cash evaluation plus internal candidate persistence, idempotency, replay, and audit posture through the active repository provider. | `idea.candidate.persist` plus `Idempotency-Key` | Process-local by default; PostgreSQL-backed only when `LOTUS_IDEA_DATABASE_URL` is configured. Real PostgreSQL persistence/replay, source-ingestion replay/conflict recovery, and migration rollback/reapply recovery proof exists for this path and the first review/conversion/report workflow path, while production storage certification, source-worker certification beyond bounded live proof, mesh certification, Gateway/Workbench proof, and supported-feature promotion remain planned. |
| `POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions` | Internal governed lifecycle transition recording over persisted candidate snapshots. | `idea.candidate.lifecycle.transition` plus `Idempotency-Key` | No downstream authority, suitability, execution, Gateway, Workbench, or supported-feature promotion. |
| `GET /api/v1/idea-candidates/{candidateId}` | Internal source-safe candidate detail projection over persisted candidate snapshots, redacted evidence, workflow summaries, audit summary, and caller entitlement-scope enforcement when scope headers are present. | `idea.candidate.detail.read` or advisor/operator role | Read-only Gateway publication exists through `lotus-gateway` `GET /api/v1/ideas/candidates/{candidate_id}`, including entitlement-scope header forwarding. Bounded read-only Workbench rendering exists for source-safe candidate detail through PR #391. No source-system route disclosure, raw evidence export, full Workbench live proof, data-product certification, downstream authority, client-ready publication, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/evidence-replay` | Internal operator evidence replay posture over persisted candidate evidence hashes and caller-supplied current source refs. | `idea.candidate.evidence.replay` plus operator role | No live Core source export, downstream authority, Gateway/Workbench proof, data-product certification, production recovery certification, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate` | Internal governed AI explanation fallback/verifier evaluation over persisted candidate evidence with source-safe lineage recording. | `idea.ai-explanation.evaluate` | No provider call, `lotus-ai` runtime execution, autonomous advice, downstream authority, Gateway/Workbench surface, client-ready publication, or supported-feature promotion. Use the separate AI lineage store proof artifact for source-safe persistence evidence. |
| `GET /api/v1/ai-explanations/readiness` | Internal operator diagnostic for AI explanation guardrail availability, model-risk operations posture, and certification blockers. | `idea.ai-explanation.readiness.read` plus operator role | Diagnostic only; it may report certified repo-owned model-risk dashboard/alert artifacts, but it is not `lotus-ai` runtime execution, provider-call proof, prompt exposure, Gateway/Workbench proof, data-product certification, client-ready publication, or supported-feature promotion. AI lineage and model-risk operations proofs are consumed by aggregate implementation-proof readiness, not promoted by this endpoint alone. |
| `GET /api/v1/review-queues/advisor` | Internal deterministic advisor queue projection over persisted candidate snapshots, constrained by platform caller-context entitlement headers and optional tenant/book/portfolio/client scope filters. | `idea.review.queue.read` or advisor role | Read-only Gateway publication exists through `lotus-gateway` `GET /api/v1/ideas/review-queues/advisor`, including entitlement-scope header forwarding. Scope-aware filtering is implemented and query scope is rejected when it exceeds caller entitlements. Bounded read-only Workbench queue rendering exists through PR #391. Durable queue store, full Workbench live proof, data-product certification, PM/compliance/operator queue surface, client-ready publication, and supported-feature promotion remain out of scope. |
| `GET /api/v1/review-queues/advisor/readiness` | Internal operator diagnostic for deterministic advisor queue projection readiness, aggregate counts, exclusion counts, durable-storage posture, and certification blockers. | `idea.review.queue.readiness.read` plus operator role | Diagnostic only; no candidate identifier discovery, access-scope inspection, Gateway contract, Workbench proof, data-product certification, PM/compliance queue support, client-ready publication, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/review-actions` | Internal advisor review decision recording with fail-closed scope checks. | `idea.review.record`, advisor role, authorized scope, and `Idempotency-Key` | No suitability, compliance, mandate, execution, client-communication, Gateway, Workbench, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/feedback` | Internal source-provenanced advisor feedback recording. | `idea.feedback.record`, advisor role, authorized scope, and `Idempotency-Key` | No model-training automation, Gateway, Workbench, data-product certification, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/conversion-intents` | Internal review-gated conversion intent recording for Advise, Manage, or Report targets. | `idea.conversion.intent.record` plus `Idempotency-Key` | Intent only; no downstream proposal, manage-review, report authority, suitability, execution, client communication, or supported-feature promotion. |
| `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions` | Internal source-safe submission posture for Advise or Manage conversion intents through configured downstream realization adapters. | `idea.downstream-realization.submit` plus `Idempotency-Key` | Submission posture only; no downstream outcome recording, proposal/action creation proof, suitability, execution, Gateway, Workbench, data-product certification, or supported-feature promotion. |
| `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes` | Internal source-authorized downstream conversion outcome recording. | `idea.conversion.outcome.record` plus `Idempotency-Key` | Outcome tracking only; no downstream workflow execution proof or supported-feature promotion. |
| `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs` | Internal report evidence-pack request recording for reviewed report conversion intents. | `idea.report-evidence-pack.request` plus `Idempotency-Key` | Request only; no `lotus-report` package intake, `lotus-render` output, `lotus-archive` record, client-ready publication, or supported-feature promotion. |
| `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions` | Internal source-safe submission posture for an existing Report evidence-pack request through the configured Report realization adapter. | `idea.downstream-realization.submit` plus `Idempotency-Key` | Submission posture only; no Report package intake proof, Render output, Archive record, downstream outcome recording, Gateway, Workbench, data-product certification, client-ready publication, or supported-feature promotion. |
| `GET /api/v1/downstream-realization/readiness` | Internal operator diagnostic for Advise, Manage, Report, Render, and Archive realization blockers over current `lotus-idea` workflow counts and manifest-backed planned downstream contract readiness. | `idea.downstream-realization.readiness.read` plus operator role | Diagnostic only; planned contract records are validated by `make downstream-realization-contract-gate` but are not downstream route-existence proof; no downstream service calls, proposal creation, manage action creation, report materialization, render output, archive record, client-ready publication, or supported-feature promotion. |
| `GET /api/v1/source-ingestion/readiness` | Internal operator diagnostic for high-cash Core source-ingestion run-once worker configuration, optional live-proof artifact validity, optional scheduled-worker deploy-proof validity, and certification blockers. | `idea.source-ingestion.readiness.read` plus operator role | Diagnostic only; a valid live proof artifact clears only the live-Core blocker, and a valid scheduled-worker proof artifact clears only the scheduled-worker blocker. No data-product certification, platform source-manifest inclusion, Gateway/Workbench support, downstream realization proof, or supported-feature promotion. |
| `POST /api/v1/source-ingestion/run-once` | Internal operator action that runs one bounded high-cash Core source-ingestion pass through the configured manifest, active repository provider, and Core source adapter. | `idea.source-ingestion.run` plus operator role | Aggregate run summary only; fails closed without durable repository, manifest, or Core configuration; no portfolio identifiers, raw Core payloads, raw idempotency keys, candidate identifiers, live Core certification, scheduled-worker proof, Gateway/Workbench support, or supported-feature promotion. |
| `GET /api/v1/outbox-delivery/readiness` | Internal operator diagnostic for aggregate outbox backlog, retry/dead-letter posture, durable repository posture, broker configuration, publisher-adapter presence, and broker/downstream certification blockers. | `idea.outbox-delivery.readiness.read` plus operator role | Diagnostic only; no event identifiers, certified live broker runtime, downstream delivery, platform mesh event certification, Gateway/Workbench support, or supported-feature promotion. |
| `POST /api/v1/outbox-delivery/run-once` | Internal operator action that runs one bounded outbox delivery pass through the active repository and configured publisher adapter. | `idea.outbox-delivery.run` plus operator role | Aggregate run summary only; fails closed without broker configuration; no event identifiers, live broker certification, downstream delivery proof, platform mesh event certification, Gateway/Workbench support, or supported-feature promotion. |
| `GET /api/v1/data-mesh/readiness` | Internal operator diagnostic for repo-authored planned/not-certified data-mesh posture and platform-aligned promotion blockers. | `idea.mesh.readiness.read` plus operator role | Diagnostic only; no data-product certification, platform source-manifest inclusion, platform catalog inclusion, SLO/access/evidence certification, runtime lineage proof, Gateway/Workbench discovery, or supported-feature promotion. |
| `GET /api/v1/data-mesh/trust-telemetry/runtime-preview` | Internal operator diagnostic for source-safe aggregate runtime trust telemetry preview over the active repository provider. | `idea.mesh.trust-telemetry.preview.read` plus operator role | Diagnostic only; no candidate detail, source route export, data-product certification, platform source-manifest inclusion, Gateway/Workbench discovery, or supported-feature promotion. |
| `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot` | Internal operator diagnostic for source-safe contract-shaped runtime trust telemetry snapshot evidence over the active repository provider. | `idea.mesh.trust-telemetry.snapshot.read` plus operator role | Diagnostic only; no candidate detail, source route export, data-product certification, platform source-manifest inclusion, Gateway/Workbench discovery, client-ready publication, or supported-feature promotion. |
| `GET /api/v1/implementation-proof/readiness` | Internal aggregate operator diagnostic for RFC-0002 implementation proof blockers, including outbox-delivery readiness and run-once posture. | `idea.implementation-proof.readiness.read` plus operator role | Diagnostic only; no live implementation proof, certified live broker runtime, downstream delivery, data-product certification, platform source-manifest inclusion, Gateway/Workbench proof, client-ready publication, or supported-feature promotion. |

Baseline health and metadata endpoints are also tracked in the ledger with
`baseline_certified` posture:

1. `GET /health`,
2. `GET /health/live`,
3. `GET /health/ready`,
4. `GET /metadata`.

Use these endpoints only for their current internal foundation, bounded
read-only Gateway publication, or operator diagnostic/action purpose. Do not use them
as live source ingestion proof, Workbench proof, data-product certification,
durable database evidence beyond the explicit PostgreSQL runtime proof,
downstream realization proof, client-ready publication, or supported-feature
promotion. Those remain blocked until later RFC slices add runtime adapters,
downstream contracts, trust telemetry, UI proof, and supported-feature
registration.

Every row above is backed by
`docs/operations/endpoint-certification-ledger.json`; keep this narrative guide
and the ledger synchronized when a certified endpoint is added, removed, or
materially changes boundary.

## Source-Degraded And Reconciliation Endpoints

Endpoints that reconcile expected-versus-realized state or consume another Lotus app as source
authority must also include:

1. explicit source-owner fields in success and degraded responses,
2. source freshness, lineage, and supportability fields where the source owner exposes them,
3. READY, DEGRADED, BLOCKED, and NOT_SUPPORTED examples where those states are applicable,
4. tests for missing, stale, unavailable, partial, malformed, and conflicting upstream evidence,
5. proof that the service does not clone calculations owned by another Lotus app,
6. same-RFC upstream source-contract and downstream consumer realization evidence when contracts
   change,
7. README, wiki, supported-feature, and RFC evidence updates before any product support claim.

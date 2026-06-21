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

Run make endpoint-certification-gate before promoting any endpoint as supported.

## Certified Foundation Endpoints

The current certified foundation inventory is:

| Endpoint | Foundation Scope | Required Capability | Current Boundary |
| --- | --- | --- | --- |
| `POST /api/v1/idea-signals/high-cash/evaluate` | High-cash deterministic evaluation over caller-supplied, source-owned Core evidence. | `idea.signal.evaluate` or advisor role | No live source ingestion, durable state, Gateway, Workbench, mesh certification, or supported-feature promotion. |
| `POST /api/v1/idea-signals/high-cash/evaluate-and-persist` | High-cash evaluation plus internal process-local candidate persistence, idempotency, replay, and audit posture. | `idea.candidate.persist` plus `Idempotency-Key` | `durableStorageBacked=false`; database-backed persistence, migrations, and recovery proof remain planned. |
| `POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions` | Internal governed lifecycle transition recording over persisted candidate snapshots. | `idea.candidate.lifecycle.transition` plus `Idempotency-Key` | No downstream authority, suitability, execution, Gateway, Workbench, or supported-feature promotion. |
| `GET /api/v1/review-queues/advisor` | Internal deterministic advisor queue projection over persisted candidate snapshots. | `idea.review.queue.read` or advisor role | No durable queue store, Gateway/Workbench surface, PM/compliance/operator queue surface, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/review-actions` | Internal advisor review decision recording with fail-closed scope checks. | `idea.review.record`, advisor role, authorized scope, and `Idempotency-Key` | No suitability, compliance, mandate, execution, client-communication, Gateway, Workbench, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/feedback` | Internal source-provenanced advisor feedback recording. | `idea.feedback.record`, advisor role, authorized scope, and `Idempotency-Key` | No model-training automation, Gateway, Workbench, data-product certification, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/conversion-intents` | Internal review-gated conversion intent recording for Advise, Manage, or Report targets. | `idea.conversion.intent.record` plus `Idempotency-Key` | Intent only; no downstream proposal, manage-review, report authority, suitability, execution, client communication, or supported-feature promotion. |
| `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes` | Internal source-authorized downstream conversion outcome recording. | `idea.conversion.outcome.record` plus `Idempotency-Key` | Outcome tracking only; no downstream workflow execution proof or supported-feature promotion. |
| `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs` | Internal report evidence-pack request recording for reviewed report conversion intents. | `idea.report-evidence-pack.request` plus `Idempotency-Key` | Request only; no `lotus-report` package intake, `lotus-render` output, `lotus-archive` record, client-ready publication, or supported-feature promotion. |
| `GET /api/v1/data-mesh/readiness` | Internal operator diagnostic for repo-authored planned/not-certified data-mesh posture. | `idea.mesh.readiness.read` plus operator role | Diagnostic only; no data-product certification, platform source-manifest inclusion, runtime lineage proof, Gateway/Workbench discovery, or supported-feature promotion. |

Baseline health and metadata endpoints are also tracked in the ledger with
`baseline_certified` posture:

1. `GET /health`,
2. `GET /health/live`,
3. `GET /health/ready`,
4. `GET /metadata`.

Use these endpoints only for their current internal foundation or operator
diagnostic purpose. Do not use them as live source ingestion proof, Gateway
proof, Workbench proof, data-product certification, durable database evidence,
downstream realization proof, or supported-feature promotion. Those remain
blocked until later RFC slices add runtime adapters, downstream contracts,
trust telemetry, UI proof, and supported-feature registration.

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

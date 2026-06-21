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

`POST /api/v1/idea-signals/high-cash/evaluate` is the first certified API
foundation for RFC-0002 Slice 10. It evaluates caller-supplied, source-owned
Core evidence and source-reported cash weight for deterministic high-cash signal
posture.

`POST /api/v1/idea-signals/high-cash/evaluate-and-persist` is the certified
internal API foundation that adds candidate persistence through the Slice 06
in-memory idempotency/audit repository contract. It requires
`idea.candidate.persist` and an `Idempotency-Key`, returns replay/conflict
posture for idempotency behavior, and exposes `durableStorageBacked=false`
until database-backed persistence, migrations, and recovery proof exist.

`GET /api/v1/data-mesh/readiness` is a certified internal operator diagnostic
for RFC-0002 Slice 14. It requires `idea.mesh.readiness.read` plus the
`operator` role and reports the current repo-authored `planned` /
`not_certified` data-mesh posture, blockers, source-of-truth contract paths,
and `supportedFeaturePromoted=false`.

Use these endpoints only when the caller already has source-authorized Core
evidence references or internal operator authority for mesh diagnostics. Do not
use them as live source ingestion proof, Gateway proof, Workbench proof,
data-product certification, or supported-feature promotion.
Those remain blocked until later RFC slices add runtime adapters, downstream
contracts, trust telemetry, and supported-feature registration.

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

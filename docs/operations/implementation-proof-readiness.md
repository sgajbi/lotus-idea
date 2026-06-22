# Implementation Proof Readiness

`GET /api/v1/implementation-proof/readiness` is the internal operator
diagnostic for RFC-0002 implementation proof posture.

It aggregates current evidence and blockers across:

1. source-owned high-cash signal ingestion,
2. deterministic advisor review queue,
3. AI-assisted explanation governance,
4. data-mesh producer and consumer certification,
5. Workbench product realization,
6. downstream Advise, Manage, Report, Render, and Archive realization,
7. supported-feature promotion.

The endpoint requires:

1. caller role: `operator`,
2. caller capability: `idea.implementation-proof.readiness.read`,
3. timezone-aware `evaluatedAtUtc` query parameter.

Example:

```powershell
curl -H "X-Caller-Roles: operator" `
  -H "X-Caller-Capabilities: idea.implementation-proof.readiness.read" `
  "http://localhost:8330/api/v1/implementation-proof/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z"
```

## Current Interpretation

Current posture is `blocked` and `not_certified`.

That is expected. The endpoint exists so operators and implementation agents can
see the real proof gap before demo, data-mesh, Workbench, or supported-feature
promotion. It does not turn internal foundations into supported product
capability.

Current blockers include:

1. missing live Core source-ingestion proof,
2. missing scheduled worker deployment proof,
3. missing runtime trust telemetry and platform mesh certification,
4. missing Workbench panel and browser proof,
5. missing downstream Advise, Manage, Report, Render, and Archive realization,
6. missing supported-feature promotion evidence.

## Non-Goals

The endpoint must not be used as:

1. live implementation proof,
2. data-product certification proof,
3. platform source-manifest inclusion proof,
4. Gateway or Workbench product proof,
5. business product discovery,
6. evidence for external client publication,
7. supported-feature promotion.

## Source Safety

The endpoint returns aggregate capability posture only. It does not expose:

1. candidate identifiers,
2. portfolio identifiers,
3. client identifiers,
4. source routes,
5. source payloads,
6. request or response bodies,
7. raw entitlement failures,
8. trace or correlation identifiers.

## Evidence

Implementation-backed evidence:

1. application builder: `src/app/application/implementation_proof_readiness.py`,
2. API route: `src/app/api/implementation_proof_readiness.py`,
3. operation event: `implementation_proof_readiness_read`,
4. endpoint ledger:
   `docs/operations/endpoint-certification-ledger.json`,
5. unit tests:
   `tests/unit/test_implementation_proof_readiness.py`,
6. integration tests:
   `tests/integration/test_implementation_proof_readiness_api.py`.

Run:

```powershell
python -m pytest tests/unit/test_implementation_proof_readiness.py tests/integration/test_implementation_proof_readiness_api.py -q
make endpoint-certification-gate
make openapi-gate
```

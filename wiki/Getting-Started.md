# Getting Started

Current posture: `lotus-idea` is an RFC-0002 foundation implementation. Internal deterministic
signal evaluation, candidate lifecycle, review, proof-readiness, and source-proof automation exist;
no external business feature is supported or promoted yet.

Use the repo-native commands:

```powershell
make install
make check
make ci
make migration-contract-gate
make migration-execution-gate
make canonical-opportunity-source-proofs CANONICAL_OPPORTUNITY_PORTFOLIO_ID=PB_SG_GLOBAL_BAL_001 CANONICAL_OPPORTUNITY_AS_OF_DATE=2026-04-10 CANONICAL_OPPORTUNITY_RISK_BASE_URL=http://risk.dev.lotus CANONICAL_OPPORTUNITY_PERFORMANCE_BASE_URL=http://performance.dev.lotus CANONICAL_OPPORTUNITY_GENERATED_AT_UTC=2026-07-10T00:00:00Z CANONICAL_OPPORTUNITY_EVALUATED_AT_UTC=2026-07-10T00:00:00Z CANONICAL_OPPORTUNITY_CORRELATION_ID=corr-canonical-proof CANONICAL_OPPORTUNITY_TRACE_ID=trace-canonical-proof
uvicorn app.main:app --reload --port 8330
```

The scaffolded runtime exposes health, liveness, readiness, service metadata, metrics, and OpenAPI
baseline endpoints. Product behavior is promoted only after implementation, endpoint certification,
supported-feature registration, CI evidence, and wiki publication.

Primary orientation files:

1. `README.md`
2. `REPOSITORY-ENGINEERING-CONTEXT.md`
3. `docs/rfcs/README.md`
4. `docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/`
5. `supported-features/supported-features.json`
6. `docs/operations/canonical-opportunity-source-proofs.md`

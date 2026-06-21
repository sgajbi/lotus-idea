# Getting Started

Current posture: `lotus-idea` is a governed scaffold and RFC foundation. It does not yet support
business idea generation, review queues, scoring, AI explanation, conversion, or reportable idea
evidence.

Use the repo-native commands:

```powershell
make install
make check
make ci
make migration-contract-gate
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

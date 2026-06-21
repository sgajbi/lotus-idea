# Report Evidence Packs

`lotus-idea` can now record an internal report evidence-pack request for a
reviewed idea that already has a `report_evidence` conversion intent.

This is an RFC-0002 Slice 13 foundation. It is not downstream report, render, or
archive realization.

## Implemented Scope

Certified internal API foundation:

- `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs`

The endpoint:

1. requires `idea.report-evidence-pack.request`,
2. requires `Idempotency-Key`,
3. requires a prior `report_evidence` conversion intent,
4. requires reviewed, approved, ready evidence,
5. records source summaries, evidence hash, retention policy ref, and safe audit
   event,
6. reports `durableStorageBacked` from the active repository provider,
7. returns `supportedFeaturePromoted=false`.

## Boundaries

The endpoint does not:

1. create a `lotus-report` package,
2. create a `lotus-render` output,
3. create a `lotus-archive` record,
4. authorize client-ready publication,
5. grant suitability, compliance, mandate, execution, or client-communication
   authority,
6. certify a data product,
7. promote a supported feature.

## Source Authority

The request preserves authority references:

1. report package intake: `lotus-report`,
2. deterministic rendering: `lotus-render`,
3. archive metadata, retention, legal hold, retrieval, and access audit:
   `lotus-archive`.

`lotus-idea` owns only the reviewed idea evidence request truth until downstream
acceptance contracts and proof exist.

## Validation Evidence

Current proof lives in:

1. `tests/unit/test_report_evidence.py`,
2. `tests/unit/test_idea_persistence.py`,
3. `tests/integration/test_review_workflow_api.py`,
4. `tests/integration/test_postgres_runtime_integration.py`,
5. `tests/unit/test_service_contract.py`,
6. `docs/operations/endpoint-certification-ledger.json`.

Promotion requires deploy and source-ingestion recovery evidence for the PostgreSQL-backed
workflow, downstream acceptance tests, render/archive proof, Gateway/Workbench
proof, data-mesh certification, runtime trust telemetry, supported-feature
registration, and published wiki truth.

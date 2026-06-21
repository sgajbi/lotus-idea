# Conversion Governance

`lotus-idea` owns conversion intent and outcome tracking. It does not own
downstream realization.

Current implemented scope:

1. reviewed and approved ideas can request a governed conversion intent,
2. each intent records target, source evidence, review-approved posture,
   idempotency key, actor, and safe audit event,
3. each target maps to the owning downstream service:
   - `advise_proposal`: `lotus-advise`,
   - `manage_review`: `lotus-manage`,
   - `report_evidence`: `lotus-report`,
4. downstream outcomes must come from the target source authority,
5. outcomes do not grant execution, suitability, compliance, mandate, or
   client-communication authority,
6. certified internal API foundations expose:
   - `POST /api/v1/idea-candidates/{candidateId}/conversion-intents`,
   - `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes`.

The report conversion path now has one additional internal request foundation:

- `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs`

This records source-provenanced report evidence-pack request truth for reviewed
report conversion intents. It does not create `lotus-report`, `lotus-render`, or
`lotus-archive` records.

Current non-supported scope:

1. no downstream adapter is implemented,
2. no proposal, DPM action, downstream report package, rendered document, or
   archive record is created by `lotus-idea`,
3. no conversion data product is certified,
4. no supported feature is promoted,
5. the API foundations report `supportedFeaturePromoted=false`,
6. `durableStorageBacked` is `false` by default and `true` only when
   `LOTUS_IDEA_DATABASE_URL` activates the PostgreSQL repository provider.
   `make postgres-integration-gate` now proves the report conversion
   intent/outcome path against a real PostgreSQL runtime, but this remains
   internal workflow-state proof only.

Implementation source:

- `src/app/domain/conversion_governance.py`
- `src/app/application/conversion_workflow.py`
- `src/app/api/conversion_governance.py`
- `src/app/domain/report_evidence.py`
- `src/app/application/report_evidence.py`
- `src/app/api/report_evidence.py`
- `tests/unit/test_conversion_governance.py`
- `tests/unit/test_idea_persistence.py`
- `tests/integration/test_review_workflow_api.py`
- `docs/operations/endpoint-certification-ledger.json`
- `docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md`

Promotion requirements:

1. deploy and recovery evidence for the PostgreSQL-backed workflow,
2. Gateway/Workbench proof,
3. downstream acceptance tests in `lotus-advise`, `lotus-manage`, and
   `lotus-report` where each service remains source authority for its workflow,
4. data-mesh trust telemetry and platform certification,
5. supported-feature registration and published wiki truth.

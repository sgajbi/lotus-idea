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
   client-communication authority.

Current non-supported scope:

1. no conversion API is exposed,
2. no downstream adapter is implemented,
3. no proposal, DPM action, report package, rendered document, or archive record
   is created by `lotus-idea`,
4. no conversion data product is certified,
5. no supported feature is promoted.

Implementation source:

- `src/app/domain/conversion_governance.py`
- `tests/unit/test_conversion_governance.py`
- `docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md`

Promotion requirements:

1. database-backed persistence and idempotency storage,
2. API/OpenAPI contracts and endpoint certification,
3. Gateway/Workbench proof,
4. downstream acceptance tests in `lotus-advise`, `lotus-manage`, and
   `lotus-report` where each service remains source authority for its workflow,
5. data-mesh trust telemetry and platform certification,
6. supported-feature registration and published wiki truth.

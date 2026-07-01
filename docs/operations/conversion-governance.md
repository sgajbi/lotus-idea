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
6. source-safe downstream application orchestration can submit existing
   Advise/Manage conversion intents and Report evidence-pack requests through
   downstream ports without recording authoritative downstream outcomes,
7. certified internal API foundations expose:
   - `POST /api/v1/idea-candidates/{candidateId}/conversion-intents`,
   - `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes`,
   - `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions`,
   - `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions`.

The report conversion path now has one additional internal request foundation:

- `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs`

This records source-provenanced report evidence-pack request truth for reviewed
report conversion intents. It does not create `lotus-report`, `lotus-render`, or
`lotus-archive` records.

Current non-supported scope:

1. source-safe downstream orchestration, submission APIs, and adapter
   foundations exist, but no live downstream contract is certified,
2. no proposal, DPM action, downstream report package, rendered document, or
   archive record is created by `lotus-idea`,
3. no conversion data product is certified,
4. no supported feature is promoted,
5. the API foundations report `supportedFeaturePromoted=false`,
6. `durableStorageBacked` is `false` only for allowed `local`/`test`
   process-local writes and `true` when `LOTUS_IDEA_DATABASE_URL` activates the
   PostgreSQL repository provider. `demo`, `staging`, and `production` fail
   closed with `durable_repository_not_configured` when durable storage is
   absent.
   `make postgres-integration-gate` now proves the report conversion
   intent/outcome path against a real PostgreSQL runtime, but this remains
   internal workflow-state proof only.

Downstream HTTP runtime posture:

1. Advise, Manage, and Report realization adapters use the shared
   `DownstreamJsonClient` with explicit timeout, connection-pool, keepalive,
   and pool-timeout limits.
2. Runtime-cached realization clients are closed on FastAPI shutdown and by
   the deterministic test reset hook; injected test clients remain owned by the
   caller.
3. Configure defaults with:
   - `LOTUS_IDEA_DOWNSTREAM_REALIZATION_TIMEOUT_SECONDS`,
   - `LOTUS_IDEA_DOWNSTREAM_REALIZATION_MAX_CONNECTIONS`,
   - `LOTUS_IDEA_DOWNSTREAM_REALIZATION_MAX_KEEPALIVE_CONNECTIONS`,
   - `LOTUS_IDEA_DOWNSTREAM_REALIZATION_POOL_TIMEOUT_SECONDS`,
   - `LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_MAX_ATTEMPTS`,
   - `LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_INITIAL_BACKOFF_SECONDS`,
   - `LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_MAX_BACKOFF_SECONDS`.
4. Retry defaults are disabled (`max_attempts=1`). When enabled, retries are
   bounded to timeouts, transport failures, `429`, `502`, `503`, and `504`.
   Advise/Manage/Report `POST` retries require the request `Idempotency-Key`;
   `400`, `401`, `403`, `404`, `409`, malformed upstream responses, and local
   idempotency or business-state failures are not retried. Computed backoff
   delays use the shared client's fixed 20% downward jitter window; valid
   upstream `Retry-After` values remain capped but not jittered.
5. Invalid or internally inconsistent resource settings fail closed before a
   downstream submission is attempted.
6. This lifecycle and resource-control posture is not downstream route
   existence proof, downstream execution certification, suitability authority,
   report materialization proof, client publication authority, or
   supported-feature promotion.

Implementation source:

- `src/app/domain/conversion_governance.py`
- `src/app/application/conversion_workflow.py`
- `src/app/application/downstream_realization.py`
- `src/app/api/downstream_realization.py`
- `src/app/runtime/downstream_realization_state.py`
- `src/app/api/conversion_governance.py`
- `src/app/domain/report_evidence.py`
- `src/app/application/report_evidence.py`
- `src/app/api/report_evidence.py`
- `tests/unit/test_conversion_governance.py`
- `tests/unit/test_idea_persistence.py`
- `tests/unit/test_downstream_realization_application.py`
- `tests/integration/test_downstream_realization_api.py`
- `tests/integration/test_review_workflow_api.py`
- `docs/operations/endpoint-certification-ledger.json`
- `docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md`

Promotion requirements:

1. deploy evidence, certified long-running scheduled source-worker proof, and
   live source-adapter proof for the PostgreSQL-backed workflow,
2. Gateway/Workbench proof,
3. downstream acceptance tests in `lotus-advise`, `lotus-manage`, and
   `lotus-report` where each service remains source authority for its workflow,
4. data-mesh trust telemetry and platform certification,
5. supported-feature registration and published wiki truth.

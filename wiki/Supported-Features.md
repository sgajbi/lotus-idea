# Supported Features

Current posture: no business feature is supported yet.

Internal foundation exists for domain vocabulary, high-cash signal evaluation,
candidate persistence/replay/idempotency/audit, candidate evidence replay,
deterministic scoring with review-queue projection, source-safe candidate detail projection, advisor
review/feedback governance, AI governance redaction/verifier/fallback controls,
and certified internal AI explanation evaluator and readiness APIs, plus the first certified
internal high-cash API foundation.
Internal conversion governance and certified internal
conversion intent/outcome API foundations also exist for review-gated
conversion tracking, source-authority mapping, and no-authority conversion
boundaries. Internal report evidence-pack request governance also exists for
reviewed report conversion intents, with safe source summaries, retention refs,
Report/Render/Archive authority refs, idempotency, audit, and a certified
internal API foundation. Real PostgreSQL runtime proof exists for high-cash
persistence/replay plus the first internal advisor queue, lifecycle, review,
feedback, conversion, report evidence-pack request workflow path, and internal
source-ingestion replay/conflict recovery. A manifest-backed run-once
source-ingestion worker CLI and `make source-ingestion-worker-check` also
exist; the gate validates both manifest shape and source-safe check-only output
shape. A bounded scheduled-worker entrypoint, opt-in Docker Compose worker
profile, and `make source-ingestion-scheduled-worker-check` also exist for
deploy-contract proof. `POST /api/v1/source-ingestion/run-once` adds a certified internal
operator action over the same batch foundation, but it requires durable
repository posture plus configured manifest and Core settings, returns
aggregate decision counts only, and remains `not_certified`. Accepted internal mutations now create source-safe outbox records with
retryable failed status, published status, and dead-letter status through the
repository port. Certified internal outbox delivery readiness and run-once
operator endpoints now report aggregate backlog/status posture and can execute
one bounded configured-publisher pass without exposing event identifiers,
aggregate identifiers, raw idempotency keys, source payloads, broker payloads,
or downstream claims. That is recoverability foundation only; no certified live
broker runtime, downstream consumer, Gateway event, platform mesh event, or
supported event publication exists. `lotus-gateway` now publishes bounded read-only advisor
queue and candidate detail routes, but these foundations are not deployed
scheduler daemon proof, live Core worker certification, Workbench proof, or
supported-feature promotion. The AI explanation readiness diagnostic is an
operator
supportability check only; it does not invoke `lotus-ai`, certify runtime AI
lineage-store proof, prove model-risk dashboards, or promote AI explanation support. The
downstream realization readiness diagnostic is an operator supportability
check only; it reports workflow counts, planned Advise/Manage/Report contract
posture, and Advise/Manage/Report/Render/Archive blockers without calling
downstream services, proving downstream route existence, or creating
downstream records.
The implementation-proof readiness diagnostic is also an operator supportability
check only; it aggregates blockers and evidence refs across source ingestion,
advisor queue, AI explanation, data mesh, runtime trust telemetry
preview/snapshot endpoint and evidence, outbox delivery, Workbench,
downstream realization, and supported-feature promotion. It does not provide live implementation proof, external broker
publication, downstream delivery, Gateway/Workbench proof, data-product
certification, or supported-feature promotion. These are not externally
supported features until live source adapters, certified long-running scheduled
source-worker runtime proof, Workbench proof, downstream acceptance,
data-product certification, and supported-feature evidence are present. The
current scheduled worker deploy-contract proof is a foundation control only.

Planned capabilities:

1. idea lifecycle and review state,
2. source-owned signal ingestion,
3. idea evidence packets,
4. deterministic scoring and ranking,
5. advisor opportunity queues,
6. feedback and suppression,
7. AI-assisted explanation through `lotus-ai`,
8. advisory and manage conversion intents,
9. reportable idea evidence,
10. any demo-ready opportunity journeys before full validation.

Promotion rule: a capability is supported only after implementation, tests,
endpoint certification, supported-feature registration, docs/wiki updates, and
validation evidence exist.
